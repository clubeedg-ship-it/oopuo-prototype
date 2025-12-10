#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Infrastructure Deployment Engine
Migrated from v33 with enhancements
"""
import os
import subprocess
import time
import re
from datetime import datetime
from config import config, LOG_FILE, VAULT_DIR

class InfraEngine:
    """Proxmox VM/CT deployment and management"""
    
    def __init__(self):
        self.progress = 0
        self.status = "Ready"
    
    def log(self, msg):
        """Write to log file"""
        ts = datetime.now().strftime('%H:%M:%S')
        self.status = msg
        with open(LOG_FILE, 'a') as f:
            f.write(f"[INFRA] [{ts}] {msg}\n")
    
    def run_cmd(self, cmd):
        """Execute shell command"""
        try:
            result = subprocess.check_output(
                cmd,
                shell=True,
                stderr=subprocess.STDOUT
            )
            return result.decode().strip()
        except subprocess.CalledProcessError:
            return None
    
    def detect_network(self):
        """Auto-detect network configuration"""
        self.log("Detecting network configuration...")
        
        host_ip = self.run_cmd("hostname -I | awk '{print $1}'")
        gateway = self.run_cmd("ip route | grep default | awk '{print $3}' | head -1")
        prefix = ".".join(host_ip.split('.')[:3])
        
        config.set('network.host_ip', host_ip)
        config.set('network.gateway', gateway)
        config.set('network.brain_ip', f"{prefix}.222")
        config.set('network.guard_ip', f"{prefix}.250")
        
        self.log(f"Network: {prefix}.0/24, Gateway: {gateway}")
    
    def download_assets(self):
        """Download cloud images and templates"""
        self.log("Downloading assets...")
        self.progress = 10
        
        iso_dir = "/var/lib/vz/template/iso"
        os.makedirs(iso_dir, exist_ok=True)
        
        img_path = f"{iso_dir}/ubuntu-24.04-cloud.img"
        if not os.path.exists(img_path):
            cloud_url = config.get('assets.cloud_img_url')
            self.log(f"Downloading Ubuntu cloud image...")
            self.run_cmd(f"wget -q {cloud_url} -O {img_path}")
        
        # Generate SSH key if needed
        key_path = config.get('credentials.key_path')
        os.makedirs(VAULT_DIR, exist_ok=True)
        
        if not os.path.exists(key_path):
            self.log("Generating SSH key pair...")
            self.run_cmd(f"ssh-keygen -t ed25519 -f {key_path} -N '' -q")
        
        self.progress = 30
    
    def deploy_guard(self):
        """Deploy Guard LXC container"""
        self.log("Building Guard (LXC)...")
        self.progress = 35
        
        ctid = config.get('ids.guard_ct')
        template = config.get('assets.lxc_template')
        guard_ip = config.get('network.guard_ip')
        gateway = config.get('network.gateway')
        bridge = config.get('network.bridge')
        password = config.get('credentials.pass')
        
        # Destroy existing container
        self.run_cmd(f"pct destroy {ctid} -purge > /dev/null 2>&1 || true")
        
        # Update available templates
        self.run_cmd("pveam update > /dev/null 2>&1")
        
        # Download template if needed
        template_path = f"/var/lib/vz/template/cache/{template}"
        if not os.path.exists(template_path):
            self.log(f"Downloading LXC template: {template}")
            self.run_cmd(f"pveam download local {template} > /dev/null 2>&1")
        
        # Create container
        cmd = (
            f"pct create {ctid} local:vztmpl/{template} "
            f"--hostname oopuopu-gateway "
            f"--memory 512 --cores 1 "
            f"--net0 name=eth0,bridge={bridge},ip={guard_ip}/24,gw={gateway} "
            f"--storage local-lvm "
            f"--password {password} "
            f"--features nesting=1 "
            f"--unprivileged 1 "
            f"--start 1"
        )
        
        self.run_cmd(cmd)
        self.log(f"Guard created: CT {ctid} at {guard_ip}")
        
        # Install Cloudflared
        self.log("Installing Cloudflare Tunnel agent...")
        setup_script = (
            "apt-get update > /dev/null && "
            "apt-get install -y curl > /dev/null && "
            "curl -L --output cloudflared.deb "
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb "
            "> /dev/null 2>&1 && "
            "dpkg -i cloudflared.deb > /dev/null 2>&1"
        )
        
        self.run_cmd(f"pct exec {ctid} -- bash -c '{setup_script}'")
        config.set('cloudflare.tunnel_installed', True)
        
        self.progress = 50
    
    def deploy_brain(self):
        """Deploy Brain VM"""
        self.log("Building Brain (VM)...")
        self.progress = 55
        
        vmid = config.get('ids.brain_vm')
        brain_ip = config.get('network.brain_ip')
        gateway = config.get('network.gateway')
        bridge = config.get('network.bridge')
        user = config.get('credentials.user')
        password = config.get('credentials.pass')
        key_path = config.get('credentials.key_path')
        
        # Stop and destroy existing VM
        self.run_cmd(f"qm stop {vmid} > /dev/null 2>&1 || true")
        self.run_cmd(f"qm destroy {vmid} > /dev/null 2>&1 || true")
        
        # Read public key
        with open(f"{key_path}.pub", 'r') as f:
            pubkey = f.read().strip()
        
        # Generate password hash
        pwd_hash = self.run_cmd(f"openssl passwd -6 '{password}'")
        
        # Create cloud-init user-data
        yaml = f"""#cloud-config
hostname: oopuopu-cloud
users:
  - name: {user}
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys: ['{pubkey}']
    lock_passwd: false
    passwd: {pwd_hash}
packages: [qemu-guest-agent, curl, wget, git]
runcmd:
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent
"""
        
        os.makedirs("/var/lib/vz/snippets", exist_ok=True)
        with open(f"/var/lib/vz/snippets/user-data-{vmid}.yaml", 'w') as f:
            f.write(yaml)
        
        # Create VM
        self.log("Creating VM...")
        self.run_cmd(
            f"qm create {vmid} --name oopuopu-cloud "
            f"--memory 8192 --cores 4 "
            f"--net0 virtio,bridge={bridge} "
            f"--scsihw virtio-scsi-pci "
            f"--agent enabled=1"
        )
        
        # Import disk
        img_path = "/var/lib/vz/template/iso/ubuntu-24.04-cloud.img"
        self.run_cmd(f"qm importdisk {vmid} {img_path} local-lvm")
        
        # Configure disk
        self.run_cmd(
            f"qm set {vmid} --scsihw virtio-scsi-pci "
            f"--scsi0 local-lvm:vm-{vmid}-disk-0,ssd=1,discard=on"
        )
        
        # Resize disk
        self.run_cmd(f"qm resize {vmid} scsi0 +80G")
        
        # Set boot and cloud-init
        self.run_cmd(
            f"qm set {vmid} --boot c --bootdisk scsi0 "
            f"--ide2 local-lvm:cloudinit "
            f"--cicustom user=local:snippets/user-data-{vmid}.yaml "
            f"--ciuser {user} "
            f"--ipconfig0 ip={brain_ip}/24,gw={gateway}"
        )
        
        # Start VM
        self.log("Starting VM...")
        self.run_cmd(f"qm start {vmid}")
        
        # Wait for network
        self.log("Waiting for network connectivity...")
        for i in range(60):
            if os.system(f"ping -c 1 -W 1 {brain_ip} > /dev/null 2>&1") == 0:
                break
            time.sleep(2)
        
        self.log(f"Brain VM ready at {brain_ip}")
        self.progress = 70
    
    def install_orchestration_stack(self):
        """Install Nomad/Consul/Vault orchestration stack (v9)"""
        self.log("Installing Nomad Orchestration Stack...")
        self.progress = 75
        
        brain_ip = config.get('network.brain_ip')
        user = config.get('credentials.user')
        key_path = config.get('credentials.key_path')
        
        payload = r'''#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
while sudo fuser /var/lib/dpkg/lock-frontend > /dev/null 2>&1; do sleep 2; done

# ===== ORCHESTRATION STACK =====
echo "[1/5] Installing HashiCorp Stack (Nomad/Consul/Vault)..."

# Add HashiCorp GPG key and repository
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update > /dev/null

# Install Nomad, Consul, Vault
sudo apt-get install -y nomad consul vault docker.io > /dev/null

# Configure Nomad
sudo mkdir -p /etc/nomad.d /opt/nomad/data
cat << 'EOF' | sudo tee /etc/nomad.d/nomad.hcl > /dev/null
datacenter = "oopuo-dc1"
data_dir = "/opt/nomad/data"

server {
  enabled = true
  bootstrap_expect = 1
}

client {
  enabled = true
  
  meta {
    "node_type" = "brain"
    "gpu_enabled" = "false"
  }
}

plugin "docker" {
  config {
    allow_privileged = true
    volumes {
      enabled = true
    }
  }
}
EOF

sudo systemctl enable nomad
sudo systemctl start nomad

# Configure Consul
sudo mkdir -p /etc/consul.d /opt/consul/data
cat << 'EOF' | sudo tee /etc/consul.d/consul.hcl > /dev/null
datacenter = "oopuo-dc1"
data_dir = "/opt/consul/data"
server = true
bootstrap_expect = 1
ui_config {
  enabled = true
}
bind_addr = "0.0.0.0"
client_addr = "0.0.0.0"
EOF

sudo systemctl enable consul
sudo systemctl start consul

# Configure Vault
sudo mkdir -p /etc/vault.d /opt/vault/data
cat << 'EOF' | sudo tee /etc/vault.d/vault.hcl > /dev/null
storage "file" {
  path = "/opt/vault/data"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = 1
}

ui = true
disable_mlock = true
EOF

sudo systemctl enable vault
sudo systemctl start vault

# ===== DEEP LEARNING FRAMEWORKS =====
echo "[2/5] Installing Deep Learning Frameworks..."

# Miniconda
mkdir -p ~/miniconda3
if ! [ -f ~/miniconda3/bin/conda ]; then
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
    bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 > /dev/null
    ~/miniconda3/bin/conda init bash > /dev/null
fi

source ~/miniconda3/bin/activate

# PyTorch (CPU for now, GPU after passthrough)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu > /dev/null 2>&1

# TensorFlow
pip install tensorflow > /dev/null 2>&1

# JAX + Flax
pip install jax flax > /dev/null 2>&1

# ===== LLM TOOLS =====
echo "[3/5] Installing LLM Tools..."

# Core LLM frameworks
pip install transformers accelerate bitsandbytes > /dev/null 2>&1
pip install langchain langgraph langsmith langchain-openai langchain-community > /dev/null 2>&1

# Fast inference
pip install vllm > /dev/null 2>&1

# Ollama
curl -fsSL https://ollama.com/install.sh | sh > /dev/null 2>&1

# llama.cpp
cd ~
if ! [ -d llama.cpp ]; then
    git clone https://github.com/ggerganov/llama.cpp > /dev/null 2>&1
    cd llama.cpp
    make > /dev/null 2>&1
fi

# ===== VECTOR DATABASES =====
echo "[4/5] Installing Vector Databases..."

pip install chromadb qdrant-client weaviate-client pymilvus faiss-cpu > /dev/null 2>&1

# ===== DEVELOPMENT TOOLS =====
echo "[5/5] Installing Development & Privacy Tools..."

# Core dev tools
pip install jupyterlab mlflow wandb bentoml ray[serve] > /dev/null 2>&1

# ONNX Runtime
pip install onnxruntime > /dev/null 2>&1

# Privacy tools (Phase 2 ready)
pip install syft opacus tensorflow-privacy flwr > /dev/null 2>&1

# Utilities
sudo apt-get install -y htop nvtop iotop tmux vim git > /dev/null

echo ""
echo "✓ OOPUO v9 Orchestration Stack installed successfully!"
echo ""
echo "Services:"
echo "  - Nomad UI:  http://$(hostname -I | awk '{print $1}'):4646"
echo "  - Consul UI: http://$(hostname -I | awk '{print $1}'):8500"
echo "  - Vault UI:  http://$(hostname -I | awk '{print $1}'):8200"
echo "  - JupyterLab: Run 'jupyter lab --ip=0.0.0.0' manually"
echo ""
'''
        
        # Copy payload
        with open("/tmp/v9_payload.sh", 'w') as f:
            f.write(payload)
        
        self.run_cmd(
            f"scp -i {key_path} -o StrictHostKeyChecking=no "
            f"/tmp/v9_payload.sh {user}@{brain_ip}:/tmp/v9_payload.sh"
        )
        
        # Execute payload
        self.log("Installing stack (this may take 15+ minutes)...")
        self.run_cmd(
            f"ssh -i {key_path} -o StrictHostKeyChecking=no "
            f"{user}@{brain_ip} 'chmod +x /tmp/v9_payload.sh && /tmp/v9_payload.sh'"
        )
        
        self.progress = 95
        self.log("Orchestration stack installation complete")
    
    def setup_gpu_passthrough(self):
        """Configure GPU passthrough for Brain VM"""
        self.log("Setting up GPU passthrough...")
        
        from gpu_manager import GPUManager
        
        gpu_mgr = GPUManager()
        vmid = config.get('ids.brain_vm')
        brain_ip = config.get('network.brain_ip')
        key_path = config.get('credentials.key_path')
        user = config.get('credentials.user')
        
        # Run full GPU setup
        result = gpu_mgr.full_setup(vmid, brain_ip, key_path, user)
        
        for step in result['steps']:
            self.log(step)
        
        if result['next_action'] == 'REBOOT_HOST':
            self.log("⚠ HOST REBOOT REQUIRED - Re-run deployment after reboot")
            return 'REBOOT_REQUIRED'
        elif result['next_action'] == 'SKIP_GPU':
            self.log("No GPU detected - continuing without GPU support")
            return 'NO_GPU'
        elif result['success']:
            self.log("✓ GPU passthrough configured successfully")
            
            # Update Nomad config to enable GPU
            update_nomad_gpu = """
cat << 'EOF' | sudo tee -a /etc/nomad.d/nomad.hcl > /dev/null

# GPU Plugin
plugin "docker" {
  config {
    nvidia_runtime = "nvidia"
  }
}

client {
  meta {
    "gpu_enabled" = "true"
  }
}
EOF

sudo systemctl restart nomad
"""
            
            self.run_cmd(
                f"ssh -i {key_path} -o StrictHostKeyChecking=no "
                f"{user}@{brain_ip} '{update_nomad_gpu}'"
            )
            
            return 'GPU_CONFIGURED'
        else:
            return 'GPU_FAILED'
    
    def deploy_full_stack(self):
        """Full deployment sequence (v9)"""
        try:
            self.detect_network()
            self.download_assets()
            self.deploy_guard()
            self.deploy_brain()
            
            # v9: Install orchestration stack
            self.install_orchestration_stack()
            
            # v9: GPU passthrough (optional)
            gpu_status = self.setup_gpu_passthrough()
            
            if gpu_status == 'REBOOT_REQUIRED':
                self.log("Deployment paused - reboot required for GPU passthrough")
                self.progress = 95
                return 'REBOOT_REQUIRED'
            
            self.progress = 100
            self.log("OOPUO v9 DEPLOYMENT COMPLETE")
            return True
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False

if __name__ == "__main__":
    engine = InfraEngine()
    success = engine.deploy_full_stack()
    
    if success == 'REBOOT_REQUIRED':
        print("⚠ Host reboot required for GPU passthrough")
        print("  Run: sudo reboot")
        print("  Then re-run this script")
    elif success:
        print("OOPUO v9 DEPLOYMENT COMPLETE")
    else:
        print("✗ Deployment failed (see logs)")

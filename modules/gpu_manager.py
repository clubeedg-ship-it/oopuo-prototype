#!/usr/bin/env python3
"""
OOPUO v9 - GPU Manager
Automates GPU passthrough to Brain VM
"""
import os
import subprocess
import re
from config import config, LOG_FILE

class GPUManager:
    """GPU detection, IOMMU setup, and passthrough automation"""
    
    def __init__(self):
        self.gpu_info = None
        self.iommu_enabled = False
    
    def log(self, msg):
        """Write to log"""
        with open(LOG_FILE, 'a') as f:
            f.write(f"[GPU] {msg}\n")
    
    def detect_gpu(self):
        """
        Detect NVIDIA or AMD GPU on Proxmox host
        Returns: dict with vendor, pci_id, name or None
        """
        try:
            result = subprocess.run(
                "lspci | grep -i 'vga\\|3d\\|display'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            for line in result.stdout.split('\n'):
                line_lower = line.lower()
                
                if 'nvidia' in line_lower:
                    pci_id = line.split()[0]
                    self.gpu_info = {
                        'vendor': 'nvidia',
                        'pci': pci_id,
                        'name': line.strip(),
                        'full_pci': self._get_full_pci_id(pci_id)
                    }
                    self.log(f"Detected NVIDIA GPU: {line.strip()}")
                    return self.gpu_info
                
                elif 'amd' in line_lower and ('radeon' in line_lower or 'vega' in line_lower):
                    pci_id = line.split()[0]
                    self.gpu_info = {
                        'vendor': 'amd',
                        'pci': pci_id,
                        'name': line.strip(),
                        'full_pci': self._get_full_pci_id(pci_id)
                    }
                    self.log(f"Detected AMD GPU: {line.strip()}")
                    return self.gpu_info
            
            self.log("No compatible GPU detected")
            return None
        
        except Exception as e:
            self.log(f"GPU detection error: {e}")
            return None
    
    def _get_full_pci_id(self, short_id):
        """Convert 01:00.0 to 0000:01:00.0"""
        if short_id.count(':') == 1:
            return f"0000:{short_id}"
        return short_id
    
    def check_iommu_enabled(self):
        """Check if IOMMU is already enabled"""
        try:
            with open('/proc/cmdline', 'r') as f:
                cmdline = f.read()
            
            if 'intel_iommu=on' in cmdline or 'amd_iommu=on' in cmdline:
                self.iommu_enabled = True
                self.log("IOMMU already enabled")
                return True
            
            self.log("IOMMU not enabled")
            return False
        
        except Exception as e:
            self.log(f"IOMMU check error: {e}")
            return False
    
    def enable_iommu(self):
        """
        Enable IOMMU in GRUB configuration
        Returns: 'ENABLED' or 'REBOOT_REQUIRED'
        """
        if self.check_iommu_enabled():
            return 'ALREADY_ENABLED'
        
        try:
            # Detect CPU vendor
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            if 'Intel' in cpuinfo:
                iommu_param = 'intel_iommu=on'
                self.log("Detected Intel CPU")
            elif 'AMD' in cpuinfo:
                iommu_param = 'amd_iommu=on'
                self.log("Detected AMD CPU")
            else:
                self.log("Unknown CPU vendor")
                return 'ERROR'
            
            # Read GRUB config
            with open('/etc/default/grub', 'r') as f:
                grub_content = f.read()
            
            # Update GRUB_CMDLINE_LINUX_DEFAULT
            if iommu_param not in grub_content:
                # Find the line and update it
                pattern = r'GRUB_CMDLINE_LINUX_DEFAULT="([^"]*)"'
                
                def replacer(match):
                    existing = match.group(1)
                    new_params = f"{existing} {iommu_param} iommu=pt"
                    return f'GRUB_CMDLINE_LINUX_DEFAULT="{new_params}"'
                
                updated_content = re.sub(pattern, replacer, grub_content)
                
                # Write back
                with open('/etc/default/grub', 'w') as f:
                    f.write(updated_content)
                
                # Update GRUB
                subprocess.run(['update-grub'], check=True)
                
                self.log(f"IOMMU enabled with: {iommu_param}")
                return 'REBOOT_REQUIRED'
            
            return 'ALREADY_ENABLED'
        
        except Exception as e:
            self.log(f"IOMMU enable error: {e}")
            return 'ERROR'
    
    def configure_vfio(self):
        """Load VFIO modules and blacklist host GPU drivers"""
        try:
            # Add VFIO modules to /etc/modules
            vfio_modules = ['vfio', 'vfio_iommu_type1', 'vfio_pci', 'vfio_virqfd']
            
            with open('/etc/modules', 'r') as f:
                existing = f.read()
            
            with open('/etc/modules', 'a') as f:
                for module in vfio_modules:
                    if module not in existing:
                        f.write(f"{module}\n")
                        self.log(f"Added module: {module}")
            
            # Blacklist GPU drivers on host
            blacklist_content = """# OOPUO - Blacklist GPU drivers for passthrough
blacklist nouveau
blacklist nvidia
blacklist nvidiafb
blacklist nvidia_drm
blacklist radeon
blacklist amdgpu
"""
            
            with open('/etc/modprobe.d/oopuo-gpu-blacklist.conf', 'w') as f:
                f.write(blacklist_content)
            
            self.log("Created GPU driver blacklist")
            
            # Update initramfs
            subprocess.run(['update-initramfs', '-u', '-k', 'all'], check=True)
            
            self.log("VFIO configuration complete")
            return True
        
        except Exception as e:
            self.log(f"VFIO configuration error: {e}")
            return False
    
    def passthrough_to_vm(self, vmid):
        """
        Configure VM with GPU passthrough
        Args:
            vmid: Proxmox VM ID
        """
        if not self.gpu_info:
            self.log("No GPU detected, cannot passthrough")
            return False
        
        try:
            pci_id = self.gpu_info['full_pci']
            
            # Configure hostpci
            cmd = [
                'qm', 'set', str(vmid),
                '-hostpci0', f'{pci_id},pcie=1,rombar=0'
            ]
            
            subprocess.run(cmd, check=True)
            
            self.log(f"GPU {pci_id} passed through to VM {vmid}")
            
            # Save GPU info to config
            config.set('gpu.enabled', True)
            config.set('gpu.vendor', self.gpu_info['vendor'])
            config.set('gpu.pci_id', pci_id)
            config.save()
            
            return True
        
        except Exception as e:
            self.log(f"GPU passthrough error: {e}")
            return False
    
    def install_vm_drivers(self, brain_ip, key_path, user):
        """
        Install GPU drivers inside the Brain VM
        Args:
            brain_ip: IP address of Brain VM
            key_path: SSH key path
            user: SSH username
        """
        if not self.gpu_info:
            return False
        
        vendor = self.gpu_info['vendor']
        
        try:
            if vendor == 'nvidia':
                script = """#!/bin/bash
set -e

echo "Starting GPU driver installation..."

# Function to wait for apt locks
wait_for_apt() {
    echo "Waiting for package manager to become available..."
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        # Check all lock files
        if ! fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 && \\
           ! fuser /var/lib/apt/lists/lock >/dev/null 2>&1 && \\
           ! fuser /var/cache/apt/archives/lock >/dev/null 2>&1 && \\
           ! fuser /var/lib/dpkg/lock >/dev/null 2>&1; then
            echo "Package manager is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "  Waiting... ($attempt/$max_attempts) - checking for locks"
        sleep 10
    done
    
    # If still locked after max attempts, kill unattended-upgrade
    echo "WARNING: Forcing package manager unlock..."
    sudo killall -9 apt-get apt dpkg unattended-upgrade 2>/dev/null || true
    sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock 2>/dev/null || true
    sudo dpkg --configure -a
    sleep 5
}

# Wait for locks to clear
wait_for_apt

# Disable unattended-upgrades during installation
sudo systemctl stop unattended-upgrades 2>/dev/null || true
sudo systemctl disable unattended-upgrades 2>/dev/null || true

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Install NVIDIA drivers
echo "Installing NVIDIA drivers (this may take several minutes)..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-driver-535 nvidia-utils-535

# Install CUDA Toolkit 12.4
echo "Installing CUDA Toolkit..."
wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y cuda-toolkit-12-4 cuda-drivers-535

# Install NVIDIA Container Toolkit
echo "Installing NVIDIA Container Toolkit..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \\
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \\
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
echo "Configuring Docker for GPU support..."
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify installation
echo "Verifying GPU installation..."
nvidia-smi

echo "✓ GPU installation complete!"
"""

                # Update Nomad config to enable GPU
                sudo tee -a /etc/nomad.d/nomad.hcl > /dev/null <<'EOF'

plugin "docker" {{
  config {{
    allow_privileged = true
    
    extra_labels = ["job_name", "task_group_name", "task_name"]
    
    gc {{
      image = true
    }}
    
    volumes {{
      enabled = true
    }}
  }}
}}

client {{
  meta {{
    "gpu_enabled" = "true"
  }}
}}
EOF

sudo systemctl restart nomad

echo "GPU installation complete!"
"""
            
            elif vendor == 'amd':
                script = """
                # AMD ROCm installation
                sudo apt-get update
                wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/focal/amdgpu-install_*.deb
                sudo apt-get install -y ./amdgpu-install_*.deb
                sudo amdgpu-install --usecase=dkms,rocm
                
                # Verify
                rocm-smi
                """
            
            else:
                self.log(f"Unknown GPU vendor: {vendor}")
                return False
            
            # Write script to temp file
            with open('/tmp/gpu_install.sh', 'w') as f:
                f.write(script)
            
            # Copy to VM
            subprocess.run([
                'scp', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
                '/tmp/gpu_install.sh',
                f'{user}@{brain_ip}:/tmp/gpu_install.sh'
            ], check=True)
            
            # Execute in VM
            self.log("Installing GPU drivers in VM (this may take 10+ minutes)...")
            subprocess.run([
                'ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
                f'{user}@{brain_ip}',
                'chmod +x /tmp/gpu_install.sh && /tmp/gpu_install.sh'
            ], check=True, timeout=1800)  # 30 min timeout
            
            self.log("GPU drivers installed successfully")
            return True
        
        except Exception as e:
            self.log(f"GPU driver installation error: {e}")
            return False
    
    def full_setup(self, vmid, brain_ip=None, key_path=None, user=None):
        """
        Complete GPU passthrough setup workflow
        Returns: dict with status and next_steps
        """
        result = {'success': False, 'steps': [], 'next_action': None}
        
        # Step 1: Detect GPU
        if not self.detect_gpu():
            result['steps'].append('GPU detection: FAILED - No compatible GPU found')
            result['next_action'] = 'SKIP_GPU'
            return result
        
        result['steps'].append(f"GPU detection: OK - {self.gpu_info['name']}")
        
        # Step 2: Enable IOMMU
        iommu_status = self.enable_iommu()
        result['steps'].append(f"IOMMU setup: {iommu_status}")
        
        if iommu_status == 'REBOOT_REQUIRED':
            result['next_action'] = 'REBOOT_HOST'
            result['steps'].append('NEXT: Reboot Proxmox host, then re-run setup')
            return result
        
        # Step 3: Configure VFIO
        if self.configure_vfio():
            result['steps'].append('VFIO configuration: OK')
        else:
            result['steps'].append('VFIO configuration: FAILED')
            return result
        
        # Step 4: Passthrough to VM
        if self.passthrough_to_vm(vmid):
            result['steps'].append(f'GPU passthrough to VM {vmid}: OK')
        else:
            result['steps'].append('GPU passthrough: FAILED')
            return result
        
        # Step 5: Install drivers in VM (if VM is running)
        if brain_ip and key_path and user:
            if self.install_vm_drivers(brain_ip, key_path, user):
                result['steps'].append('VM GPU drivers: OK')
                result['success'] = True
                result['next_action'] = 'COMPLETE'
            else:
                result['steps'].append('VM GPU drivers: FAILED')
                result['next_action'] = 'RETRY_DRIVERS'
        else:
            result['steps'].append('VM GPU drivers: SKIPPED (VM not ready)')
            result['success'] = True
            result['next_action'] = 'INSTALL_DRIVERS_LATER'
        
        return result

if __name__ == "__main__":
    import sys
    
    gpu_mgr = GPUManager()
    
    # Test GPU detection
    gpu = gpu_mgr.detect_gpu()
    if gpu:
        print(f"✓ Found GPU: {gpu['name']}")
        print(f"  Vendor: {gpu['vendor']}")
        print(f"  PCI ID: {gpu['full_pci']}")
    else:
        print("✗ No GPU detected")
        sys.exit(1)
    
    # Check IOMMU
    if gpu_mgr.check_iommu_enabled():
        print("✓ IOMMU is enabled")
    else:
        print("⚠ IOMMU not enabled - run enable_iommu()")

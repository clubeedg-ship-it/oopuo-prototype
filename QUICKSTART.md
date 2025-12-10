# OOPUO v9 - Quick Start Guide

## Installation (3 Steps)

### 1. Upload to Cloud (GitHub)

```bash
# On your local machine
cd /Users/ottogen/oopuo-prototype

# Initialize git repo (if not already)
git init
git add .
git commit -m "OOPUO v9 - AI Infrastructure OS"

# Create GitHub repo and push
# Go to github.com/new → Create repository → name it "oopuo-prototype"
git remote add origin https://github.com/YOUR_USERNAME/oopuo-prototype.git
git branch -M main
git push -u origin main
```

**Alternative: Use raw.githubusercontent.com**

After pushing, your installer will be available at:
```
https://raw.githubusercontent.com/YOUR_USERNAME/oopuo-prototype/main/install.sh
```

### 2. Install on Proxmox (One Command)

```bash
# SSH to your Proxmox server
ssh root@your-proxmox-ip

# Run installer (UPDATE WITH YOUR GITHUB USERNAME)
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/oopuo-prototype/main/install.sh | bash
```

**What happens:**
1. Downloads OOPUO v9 from GitHub
2. Installs modules to `/opt/oopuo`
3. Deploys Guard (LXC) + Brain (VM)
4. Installs Nomad/Consul/Vault
5. Installs AI stack (PyTorch, vLLM, vector DBs)
6. Sets up GPU passthrough (if detected)

**Duration:** 15-20 minutes

### 3. Access Services

After installation:

```
✓ Nomad UI:  http://192.168.x.222:4646
✓ Consul UI: http://192.168.x.222:8500  
✓ Vault UI:  http://192.168.x.222:8200
```

---

## Deploy n8n with GPU

### Option 1: Quick Deploy Script

```bash
# On Proxmox host
bash /root/oopuo-prototype/examples/deploy_n8n.sh
```

### Option 2: Manual Nomad Job

```bash
# SSH to Brain VM
ssh adminuser@192.168.x.222  # Password: Oopuopu123!

# Create job file
cat > n8n.nomad.hcl << 'EOF'
job "n8n" {
  datacenters = ["oopuo-dc1"]
  
  group "n8n-group" {
    network {
      port "http" { static = 5678 }
    }

    task "n8n" {
      driver = "docker"
      
      config {
        image = "n8nio/n8n:latest"
        ports = ["http"]
        volumes = ["/opt/n8n-data:/home/node/.n8n"]
        
        # Enable GPU (if you want GPU-accelerated workflows)
        runtime = "nvidia"
        gpus = "all"
      }

      resources {
        cpu    = 2000   # 2 cores
        memory = 4096   # 4GB
      }
    }
  }
}
EOF

# Deploy
nomad job run n8n.nomad.hcl

# Check status
nomad job status n8n
```

Access n8n: **http://192.168.x.222:5678**

---

## Setup Cloudflare Tunnel

### Step 1: Get Tunnel Running

```bash
# On Proxmox host, start OOPUO TUI
systemctl start oopuo

# Or manually
python3 /opt/oopuo/main.py
```

In TUI:
1. Navigate to **"SETTINGS"**
2. Select **"Cloudflare Tunnel"**
3. Follow 6-step wizard:
   - Install cloudflared ✓
   - Authenticate (open URL in browser)
   - Create tunnel
   - Configure routes
   - Start service

### Step 2: Add n8n Route

```bash
# SSH to Guard LXC
ssh root@192.168.x.250  # Password: Oopuopu123!

# Add n8n route to tunnel config
cloudflared tunnel route dns YOUR_TUNNEL_NAME n8n.yourdomain.com

# Update config
nano /root/.cloudflared/config.yml
```

Add:
```yaml
ingress:
  - hostname: n8n.yourdomain.com
    service: http://192.168.x.222:5678
  - service: http_status:404
```

Restart:
```bash
systemctl restart cloudflared
```

Now access n8n at: **https://n8n.yourdomain.com**

---

## Using Python SDK

Deploy n8n programmatically:

```python
from oopuo_sdk import Brain

brain = Brain.connect("192.168.1.222")

# Deploy n8n
n8n = brain.deploy_agent(
    name="n8n",
    image="n8nio/n8n:latest",
    gpu=False,  # Set True if you want GPU
    cpu=2000,
    memory=4096,
    ports={"http": 5678}
)

print(f"✓ n8n running at http://192.168.1.222:5678")
```

---

## GPU-Accelerated Workflows

If you want to use GPU in n8n workflows (e.g., for AI nodes):

1. **Deploy n8n with GPU:**
   ```bash
   # Add to Nomad job config:
   runtime = "nvidia"
   gpus = "all"
   ```

2. **Install AI libraries inside n8n:**
   ```bash
   docker exec -it $(docker ps | grep n8n | awk '{print $1}') sh
   npm install @n8n/openai-node
   pip install torch torchvision
   ```

3. **Use in workflows:**
   - Add OpenAI/LLM nodes
   - GPU acceleration automatic via PyTorch

---

## Troubleshooting

**Can't access Nomad UI:**
```bash
# Check Brain is running
qm status 200

# Check firewall
iptables -L

# SSH to Brain and check Nomad
ssh adminuser@192.168.x.222
systemctl status nomad
```

**n8n not starting:**
```bash
# Check Nomad job logs
nomad logs -job n8n

# Check data directory permissions
ls -la /opt/n8n-data
```

**Cloudflare tunnel not working:**
```bash
# Check Guard LXC
pct status 100

# Check cloudflared
pct exec 100 -- systemctl status cloudflared
```

---

## Summary: From Zero to n8n

```bash
# 1. ONE-LINE INSTALL (on Proxmox)
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/oopuo-prototype/main/install.sh | bash

# 2. DEPLOY N8N (after install completes)
bash /root/oopuo-prototype/examples/deploy_n8n.sh

# 3. SETUP CLOUDFLARE (in OOPUO TUI)
systemctl start oopuo
# → Navigate to Settings → Cloudflare Tunnel → Follow wizard

# 4. ACCESS
https://n8n.yourdomain.com
```

**Total time:** ~25 minutes (install 20min + n8n 2min + tunnel 3min)

---

## Next Steps

- **Deploy more services:** Use `examples/deploy_*.sh` scripts
- **Build AI workflows:** Use n8n with GPU-accelerated nodes
- **Scale:** Use Python SDK to deploy multiple agents
- **Phase 2:** Enable privacy features (federated learning)

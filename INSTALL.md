# 🚀 OOPUO v9 - Installation Instructions

## Step 1: Upload to GitHub

```bash
cd /Users/ottogen/oopuo-prototype
git init
git add .
git commit -m "OOPUO v9"

# Create repo at github.com/new
git remote add origin https://github.com/YOUR_USERNAME/oopuo-prototype.git
git push -u origin main
```

## Step 2: Install on Proxmox (One Command!)

```bash
# SSH to Proxmox
ssh root@your-proxmox-ip

# Run installer (replace YOUR_USERNAME)
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/oopuo-prototype/main/install.sh | bash
```

Wait 15-20 minutes ⏱️

## Step 3: Deploy n8n

```bash
bash /root/oopuo-prototype/examples/deploy_n8n.sh
```

Access: **http://192.168.x.222:5678**

## Step 4: Connect Cloudflare Domain

```bash
# Start OOPUO TUI
systemctl start oopuo

# In TUI: Settings → Cloudflare Tunnel → Follow wizard
```

Then add your domain:
```bash
# SSH to Guard
ssh root@192.168.x.250

# Configure tunnel
nano /root/.cloudflared/config.yml
```

Add:
```yaml
ingress:
  - hostname: n8n.yourdomain.com
    service: http://192.168.x.222:5678
  - service: http_status:404
```

```bash
systemctl restart cloudflared
```

Done! Access: **https://n8n.yourdomain.com** 🎉

---

## What You Get

✅ Nomad orchestration  
✅ GPU passthrough (if available)  
✅ n8n running in Docker  
✅ Cloudflare tunnel for external access  
✅ Full AI stack (PyTorch, vLLM, vector DBs)  

---

## Troubleshooting

**Can't access services?**
```bash
# Check Brain VM
qm status 200

# Check Nomad
ssh adminuser@192.168.x.222
systemctl status nomad
```

**n8n not starting?**
```bash
nomad job status n8n
nomad logs -job n8n
```

See **QUICKSTART.md** for detailed guide.

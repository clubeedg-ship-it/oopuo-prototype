#!/bin/bash
# OOPUO v9 - One-Line Cloud Installer
# curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/install.sh | bash

set -e

echo -e "\033[38;5;46m╔═══════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[38;5;46m║                                                           ║\033[0m"
echo -e "\033[38;5;46m║      OOPUO v9 - AI Infrastructure OS Installer            ║\033[0m"
echo -e "\033[38;5;46m║                                                           ║\033[0m"
echo -e "\033[38;5;46m╚═══════════════════════════════════════════════════════════╝\033[0m"
echo ""

# Check if running on Proxmox
if ! command -v pveversion &> /dev/null; then
    echo "⚠ WARNING: This doesn't appear to be a Proxmox host"
    read -p "Continue anyway? (y/n): " confirm
    if [ "$confirm" != "y" ]; then exit 1; fi
fi

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "✗ Must run as root"
    exit 1
fi

# --- CHECK FOR EXISTING INSTALLATION ---
echo "Checking for existing OOPUO installation..."

CLEANUP_NEEDED=0

# Check for existing VMs/CTs
if qm status 200 &>/dev/null; then
    echo "  Found existing Brain VM (200)"
    CLEANUP_NEEDED=1
fi

if pct status 100 &>/dev/null; then
    echo "  Found existing Guard CT (100)"
    CLEANUP_NEEDED=1
fi

if [ -d "/opt/oopuo" ]; then
    echo "  Found existing /opt/oopuo directory"
    CLEANUP_NEEDED=1
fi

if [ $CLEANUP_NEEDED -eq 1 ]; then
    echo ""
    echo "⚠  Previous OOPUO installation detected"
    echo ""
    read -p "Remove existing installation and do fresh install? (y/n): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo ""
        echo "Cleaning up previous installation..."
        
        # Stop and remove Brain VM
        if qm status 200 &>/dev/null; then
            echo "  Stopping Brain VM..."
            qm stop 200 &>/dev/null || true
            sleep 2
            echo "  Removing Brain VM..."
            qm destroy 200 --purge &>/dev/null || true
        fi
        
        # Stop and remove Guard CT
        if pct status 100 &>/dev/null; then
            echo "  Stopping Guard CT..."
            pct stop 100 &>/dev/null || true
            sleep 2
            echo "  Removing Guard CT..."
            pct destroy 100 --purge &>/dev/null || true
        fi
        
        # Remove directories
        echo "  Removing directories..."
        rm -rf /opt/oopuo
        rm -rf /etc/oopuo
        rm -rf /var/log/oopuo
        rm -rf /root/oopuo_vault
        
        # Remove systemd service if exists
        if [ -f "/etc/systemd/system/oopuo.service" ]; then
            systemctl stop oopuo &>/dev/null || true
            systemctl disable oopuo &>/dev/null || true
            rm -f /etc/systemd/system/oopuo.service
            systemctl daemon-reload
        fi
        
        # Clean SSH known_hosts
        ssh-keygen -f '/root/.ssh/known_hosts' -R '192.168.0.222' &>/dev/null || true
        ssh-keygen -f '/root/.ssh/known_hosts' -R '192.168.0.250' &>/dev/null || true
        
        echo "  ✓ Cleanup complete"
        echo ""
    else
        echo ""
        echo "Installation aborted. Please remove existing installation manually or choose 'y' to auto-remove."
        exit 1
    fi
fi

echo "[1/4] Downloading OOPUO v9..."

# Create temp directory
TMPDIR=$(mktemp -d)
cd $TMPDIR

# Download from GitHub (no authentication required for public repos)
REPO_URL="https://github.com/clubeedg-ship-it/oopuo-prototype"

# Download as tarball (avoids any git credential prompts)
echo "  Downloading from ${REPO_URL}..."
curl -fsSL ${REPO_URL}/archive/refs/heads/main.tar.gz | tar xz
cd oopuo-prototype-main

echo "[2/4] Installing OOPUO modules..."

# Copy modules to /opt/oopuo
mkdir -p /opt/oopuo
cp -r modules/* /opt/oopuo/

# Create required directories
mkdir -p /var/log/oopuo
mkdir -p /etc/oopuo
mkdir -p /root/oopuo_vault

echo "[3/4] Running infrastructure deployment..."

# Run the deployment
RESULT=$(python3 /opt/oopuo/infra.py 2>&1)
EXIT_CODE=$?

echo "$RESULT"

# Check if it completed or needs reboot
if echo "$RESULT" | grep -q "REBOOT_REQUIRED"; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║         ⚠  INSTALLATION 95% COMPLETE                     ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "✓ Brain VM deployed successfully"
    echo "✓ Nomad/Consul/Vault installed"
    echo ""
    echo "⚠  GPU PASSTHROUGH REQUIRES HOST REBOOT"
    echo ""
    echo "Next steps:"
    echo "  1. Reboot Proxmox host:  sudo reboot"
    echo "  2. After reboot, run installer again to complete GPU setup"
    echo ""
    
    # Get Brain IP
    BRAIN_IP=$(cat /etc/oopuo/config.json 2>/dev/null | grep brain_ip | cut -d'"' -f4)
    
    echo "You can already access (without GPU):"
    echo "  🚀 Nomad UI:  http://${BRAIN_IP}:4646"
    echo "  🔍 Consul UI: http://${BRAIN_IP}:8500"
    echo "  🔐 Vault UI:  http://${BRAIN_IP}:8200"
    echo ""
    echo "  SSH: ssh -i /root/oopuo_vault/oopuo_key adminuser@${BRAIN_IP}"
    echo ""
    
elif [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "\033[38;5;46m╔═══════════════════════════════════════════════════════════╗\033[0m"
    echo -e "\033[38;5;46m║                                                           ║\033[0m"
    echo -e "\033[38;5;46m║              ✓ INSTALLATION COMPLETE!                     ║\033[0m"
    echo -e "\033[38;5;46m║                                                           ║\033[0m"
    echo -e "\033[38;5;46m╚═══════════════════════════════════════════════════════════╝\033[0m"
    echo ""
    
    # Get Brain IP
    BRAIN_IP=$(cat /etc/oopuo/config.json 2>/dev/null | grep brain_ip | cut -d'"' -f4)
    
    echo -e "\033[38;5;51mAccess your OOPUO services:\033[0m"
    echo ""
    echo -e "  🚀 Nomad UI:  \033[38;5;198mhttp://${BRAIN_IP}:4646\033[0m"
    echo -e "  🔍 Consul UI: \033[38;5;198mhttp://${BRAIN_IP}:8500\033[0m"
    echo -e "  🔐 Vault UI:  \033[38;5;198mhttp://${BRAIN_IP}:8200\033[0m"
    echo ""
    echo -e "\033[38;5;51mNext steps:\033[0m"
    echo "  1. Configure Cloudflare Tunnel: Run OOPUO TUI"
    echo "  2. Deploy n8n: See /opt/oopuo/examples/deploy_n8n.sh"
    echo ""
    echo -e "\033[38;5;240m  SSH: ssh adminuser@${BRAIN_IP}\033[0m"
    echo -e "\033[38;5;240m  Password: Oopuopu123!\033[0m"
    echo ""
else
    echo "✗ Installation failed - check logs at /var/log/oopuo/system.log"
    exit 1
fi

# Cleanup
cd /
rm -rf $TMPDIR

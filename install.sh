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
    
    # Check if we can read from terminal (not piped)
    if [ -t 0 ]; then
        # Running interactively - can prompt user
        read -p "Remove existing installation and do fresh install? (y/n): " confirm
        
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            echo ""
            echo "Installation aborted. Run with existing installation or clean up manually."
            exit 1
        fi
    else
        # Running via pipe (curl | bash) - auto-cleanup
        echo "Running via pipe - will auto-cleanup and reinstall"
        echo "To abort, press Ctrl+C in the next 5 seconds..."
        sleep 5
    fi
    
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
echo "  This may take 15-20 minutes..."

# Clear any existing install log
rm -f /var/log/oopuo/install.log

# Run the deployment with timeout to prevent hanging
timeout 1800 python3 -u /opt/oopuo/infra.py 2>&1 | tee /var/log/oopuo/install.log
EXIT_CODE=${PIPESTATUS[0]}

# Check if it timed out
if [ $EXIT_CODE -eq 124 ]; then
    echo ""
    echo "✗ Installation timed out after 30 minutes"
    echo "  Check logs: /var/log/oopuo/system.log"
    echo "  Check install log: /var/log/oopuo/install.log"
    exit 1
fi

# Read the result
RESULT=$(cat /var/log/oopuo/install.log)

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
    
elif echo "$RESULT" | grep -q "DEPLOYMENT COMPLETE"; then
    echo ""
    echo -e "\033[38;5;46m"
    echo "   ╔═══════════════════════════════════════════════════════════╗"
    echo "   ║                                                           ║"
    echo "   ║    ██████╗  ██████╗ ██████╗ ██╗   ██╗ ██████╗             ║"
    echo "   ║   ██╔═══██╗██╔═══██╗██╔══██╗██║   ██║██╔═══██╗            ║"
    echo "   ║   ██║   ██║██║   ██║██████╔╝██║   ██║██║   ██║            ║"
    echo "   ║   ██║   ██║██║   ██║██╔═══╝ ██║   ██║██║   ██║            ║"
    echo "   ║   ╚██████╔╝╚██████╔╝██║     ╚██████╔╝╚██████╔╝            ║"
    echo "   ║    ╚═════╝  ╚═════╝ ╚═╝      ╚═════╝  ╚═════╝             ║"
    echo "   ║                                                           ║"
    echo "   ║         🚀 AI Infrastructure OS - v9 🚀                   ║"
    echo "   ║                                                           ║"
    echo "   ║              ✓ INSTALLATION COMPLETE!                    ║"
    echo "   ║                                                           ║"
    echo "   ╚═══════════════════════════════════════════════════════════╝"
    echo -e "\033[0m"
    echo ""
    
    # Get Brain IP
    BRAIN_IP=$(cat /etc/oopuo/config.json 2>/dev/null | grep brain_ip | cut -d'"' -f4)
    
    echo -e "\033[38;5;51m╭─────────────────────────────────────────────────────────╮\033[0m"
    echo -e "\033[38;5;51m│  Access your OOPUO services:                            │\033[0m"
    echo -e "\033[38;5;51m╰─────────────────────────────────────────────────────────╯\033[0m"
    echo ""
    echo -e "  🚀 Nomad UI:   \033[38;5;198mhttp://${BRAIN_IP}:4646\033[0m"
    echo -e "  🔍 Consul UI:  \033[38;5;198mhttp://${BRAIN_IP}:8500\033[0m"
    echo -e "  🔐 Vault UI:   \033[38;5;198mhttp://${BRAIN_IP}:8200\033[0m"
    echo ""
    
    # Check if GPU failed
    if echo "$RESULT" | grep -q "VM GPU drivers: FAILED"; then
        echo -e "\033[38;5;214m  ⚠  Note: GPU driver installation had errors (optional)\033[0m"
        echo -e "\033[38;5;214m     System is fully functional for CPU workloads\033[0m"
        echo -e "\033[38;5;214m     GPU can be configured manually later if needed\033[0m"
        echo ""
    fi
    
    echo -e "\033[38;5;51m╭─────────────────────────────────────────────────────────╮\033[0m"
    echo -e "\033[38;5;51m│  Next steps:                                            │\033[0m"
    echo -e "\033[38;5;51m╰─────────────────────────────────────────────────────────╯\033[0m"
    echo ""
    echo "  1️⃣  Deploy n8n workflow automation"
    echo "     bash /opt/oopuo/examples/deploy_n8n.sh"
    echo ""
    echo "  2️⃣  Setup Cloudflare Tunnel for external access"
    echo "     pct enter 100 → cloudflared tunnel login"
    echo ""
    echo "  3️⃣  Use Python SDK to deploy AI agents"
    echo "     cd /opt/oopuo/sdk && pip install -e ."
    echo ""
    echo -e "\033[38;5;240m  📡 SSH: ssh -i /root/oopuo_vault/oopuo_key adminuser@${BRAIN_IP}\033[0m"
    echo ""
else
    echo "✗ Installation failed - check logs at /var/log/oopuo/system.log"
    exit 1
fi

# Cleanup
cd /
rm -rf $TMPDIR

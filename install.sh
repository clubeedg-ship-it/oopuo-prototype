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

echo "[1/4] Downloading OOPUO v9..."

# Create temp directory
TMPDIR=$(mktemp -d)
cd $TMPDIR

# Download from cloud (replace with your actual URL)
# For now, we'll package everything into a tarball
REPO_URL="https://github.com/YOUR_USERNAME/oopuo-prototype"  # UPDATE THIS

# Option 1: If you have a GitHub repo
if command -v git &> /dev/null; then
    git clone --depth 1 $REPO_URL oopuo-v9
    cd oopuo-v9
else
    # Option 2: Download as tarball
    curl -fsSL ${REPO_URL}/archive/main.tar.gz | tar xz
    cd oopuo-prototype-main
fi

echo "[2/4] Installing OOPUO modules..."

# Copy modules to /opt/oopuo
mkdir -p /opt/oopuo
cp -r modules/* /opt/oopuo/

echo "[3/4] Running infrastructure deployment..."

# Run the deployment
python3 /opt/oopuo/infra.py

if [ $? -eq 0 ]; then
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

#!/bin/bash
# Deploy n8n on OOPUO v9 via Nomad

BRAIN_IP="192.168.1.222"  # Will be auto-detected

# Get Brain IP from config
if [ -f /etc/oopuo/config.json ]; then
    BRAIN_IP=$(cat /etc/oopuo/config.json | grep brain_ip | cut -d'"' -f4)
fi

echo "Deploying n8n to OOPUO Brain ($BRAIN_IP)..."

# Create Nomad job spec
cat > /tmp/n8n.nomad.hcl << 'EOF'
job "n8n" {
  datacenters = ["oopuo-dc1"]
  type = "service"

  group "n8n-group" {
    count = 1

    network {
      port "http" {
        static = 5678
        to     = 5678
      }
    }

    task "n8n-task" {
      driver = "docker"

      config {
        image = "n8nio/n8n:latest"
        ports = ["http"]
        
        volumes = [
          "/opt/n8n-data:/home/node/.n8n"
        ]
        
        # Enable GPU if needed (uncomment next 2 lines)
        # runtime = "nvidia"
        # gpus = "all"
      }

      env {
        N8N_HOST = "0.0.0.0"
        N8N_PORT = "5678"
        N8N_PROTOCOL = "http"
        WEBHOOK_URL = "http://${BRAIN_IP}:5678/"
        GENERIC_TIMEZONE = "Europe/Berlin"
      }

      resources {
        cpu    = 1000  # 1 core
        memory = 2048  # 2GB RAM
      }

      service {
        name = "n8n"
        port = "http"
        
        tags = [
          "automation",
          "workflow"
        ]

        check {
          type     = "http"
          path     = "/healthz"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }
  }
}
EOF

# Create data directory
ssh -i /root/oopuo_vault/oopuo_key adminuser@$BRAIN_IP "sudo mkdir -p /opt/n8n-data && sudo chown 1000:1000 /opt/n8n-data"

# Copy job spec to Brain
scp -i /root/oopuo_vault/oopuo_key /tmp/n8n.nomad.hcl adminuser@$BRAIN_IP:/tmp/

# Submit job
ssh -i /root/oopuo_vault/oopuo_key adminuser@$BRAIN_IP "nomad job run /tmp/n8n.nomad.hcl"

echo ""
echo "✓ n8n deployed!"
echo ""
echo "  Access: http://${BRAIN_IP}:5678"
echo "  Nomad UI: http://${BRAIN_IP}:4646"
echo ""
echo "To expose via Cloudflare Tunnel:"
echo "  1. Run OOPUO TUI and configure tunnel"
echo "  2. Add route: n8n.yourdomain.com -> http://localhost:5678"
echo ""

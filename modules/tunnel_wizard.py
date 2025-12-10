#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Cloudflare Tunnel Setup Wizard
Step-by-step guide for connecting Guard LXC to Cloudflare
"""
import sys
import os
import subprocess
import shutil
import tty
import termios
import select
from colors import col, box_chars, bold, C_PRIMARY, C_SUCCESS, C_ERROR, C_MUTED, C_TEXT, C_ACCENT
from config import config

class TunnelWizard:
    """Interactive Cloudflare Tunnel setup wizard"""
    
    STEPS = [
        {
            'title': "Step 1: Install Cloudflared",
            'description': "Installing Cloudflare Tunnel client in Guard container...",
            'action': 'install'
        },
        {
            'title': "Step 2: Authenticate",
            'description': "You need to authenticate Cloudflared with your Cloudflare account.\nA URL will be displayed. Open it in your browser and login.",
            'action': 'auth'
        },
        {
            'title': "Step 3: Create Tunnel",
            'description': "Creating a new tunnel named 'oopuo-guard'...",
            'action': 'create_tunnel'
        },
        {
            'title': "Step 4: Configure Routes",
            'description': "Setting up tunnel routes for your services...",
            'action': 'configure'
        },
        {
            'title': "Step 5: Start Tunnel",
            'description': "Starting the tunnel service...",
            'action': 'start'
        },
        {
            'title': "Complete!",
            'description': "Your Guard LXC is now connected to Cloudflare Tunnel.\nYou can access your services via the Cloudflare dashboard.",
            'action': 'done'
        }
    ]
    
    def __init__(self):
        self.current_step = 0
        self.running = True
        self.guard_id = config.get('ids.guard_ct', 100)
        self.width, self.height = shutil.get_terminal_size()
    
    def exec_in_guard(self, command):
        """Execute command in Guard container"""
        try:
            result = subprocess.run(
                f"pct exec {self.guard_id} -- {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def render(self):
        """Render the wizard UI"""
        self.width, self.height = shutil.get_terminal_size()
        
        # Clear screen
        sys.stdout.write("\033[H\033[J")
        
        box = box_chars('rounded')
        
        # Title
        sys.stdout.write("\033[2;2H")
        title = bold(col("╔═══════════════════════════════════════╗", C_PRIMARY))
        sys.stdout.write(title)
        
        sys.stdout.write("\033[3;2H")
        sys.stdout.write(col("║", C_PRIMARY) + "                                       " + col("║", C_PRIMARY))
        
        sys.stdout.write("\033[4;2H")
        wizard_title = "  🔗 CLOUDFLARE TUNNEL SETUP WIZARD  "
        sys.stdout.write(col("║", C_PRIMARY) + bold(col(wizard_title, C_ACCENT)) + col("║", C_PRIMARY))
        
        sys.stdout.write("\033[5;2H")
        sys.stdout.write(col("║", C_PRIMARY) + "                                       " + col("║", C_PRIMARY))
        
        sys.stdout.write("\033[6;2H")
        sys.stdout.write(bold(col("╚═══════════════════════════════════════╝", C_PRIMARY)))
        
        # Progress bar
        progress = int((self.current_step / len(self.STEPS)) * 40)
        bar = "█" * progress + "░" * (40 - progress)
        
        sys.stdout.write("\033[8;2H")
        sys.stdout.write(col(f"Progress: {bar} {self.current_step}/{len(self.STEPS)}", C_SUCCESS))
        
        # Current step
        if self.current_step < len(self.STEPS):
            step = self.STEPS[self.current_step]
            
            sys.stdout.write("\033[10;2H")
            sys.stdout.write(bold(col(step['title'], C_PRIMARY)))
            
            sys.stdout.write("\033[12;2H")
            # Word wrap description
            words = step['description'].split('\n')
            y = 12
            for line in words:
                sys.stdout.write(f"\033[{y};2H")
                sys.stdout.write(col(line, C_TEXT))
                y += 1
        
        # Instructions
        sys.stdout.write(f"\033[{self.height-3};2H")
        if self.current_step < len(self.STEPS) - 1:
            sys.stdout.write(col("Press ENTER to continue  |  Q to quit", C_MUTED))
        else:
            sys.stdout.write(col("Press ENTER to finish  |  Q to quit", C_MUTED))
        
        sys.stdout.flush()
    
    def execute_step(self):
        """Execute the current step's action"""
        if self.current_step >= len(self.STEPS):
            return True
        
        step = self.STEPS[self.current_step]
        action = step['action']
        
        sys.stdout.write(f"\033[{self.height-5};2H")
        sys.stdout.write(col("Working...", C_TEXT) + " " * 30)
        sys.stdout.flush()
        
        if action == 'install':
            success, _, _ = self.exec_in_guard(
                "apt-get update > /dev/null && "
                "apt-get install -y curl > /dev/null && "
                "curl -L --output cloudflared.deb "
                "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && "
                "dpkg -i cloudflared.deb > /dev/null 2>&1"
            )
            
        elif action == 'auth':
            # Show auth URL
            success, stdout, _ = self.exec_in_guard("cloudflared tunnel login 2>&1")
            
            # Extract URL from output
            for line in stdout.split('\n'):
                if 'https://' in line:
                    sys.stdout.write(f"\033[{self.height-6};2H")
                    sys.stdout.write(col(f"Open: {line.strip()}", C_ACCENT) + " " * 20)
                    break
            
            sys.stdout.write(f"\033[{self.height-5};2H")
            sys.stdout.write(col("After logging in, press ENTER", C_TEXT))
            sys.stdout.flush()
            
            return True  # User must manually complete this
        
        elif action == 'create_tunnel':
            success, stdout, _ = self.exec_in_guard("cloudflared tunnel create oopuo-guard 2>&1")
            
            # Extract tunnel ID
            for line in stdout.split('\n'):
                if 'Created tunnel' in line:
                    parts = line.split()
                    if len(parts) > 2:
                        tunnel_id = parts[2]
                        config.set('cloudflare.tunnel_id', tunnel_id)
                        config.set('cloudflare.tunnel_name', 'oopuo-guard')
        
        elif action == 'configure':
            # Create basic config
            cfg = """tunnel: oopuo-guard
credentials-file: /root/.cloudflared/oopuo-guard.json

ingress:
  - hostname: oopuo.example.com
    service: http://localhost:8000
  - service: http_status:404
"""
            self.exec_in_guard(f"mkdir -p /root/.cloudflared && echo '{cfg}' > /root/.cloudflared/config.yml")
            success = True
        
        elif action == 'start':
            success, _, _ = self.exec_in_guard(
                "cloudflared service install && "
                "systemctl enable cloudflared && "
                "systemctl start cloudflared"
            )
            
            if success:
                config.set('cloudflare.tunnel_configured', True)
                config.save()
        
        elif action == 'done':
            success = True
        
        else:
            success = True
        
        # Show result
        sys.stdout.write(f"\033[{self.height-5};2H")
        if success:
            sys.stdout.write(col("✓ Complete!", C_SUCCESS) + " " * 30)
        else:
            sys.stdout.write(col("✗ Failed (see logs)", C_ERROR) + " " * 20)
        sys.stdout.flush()
        
        return success
    
    def handle_input(self, key):
        """Handle keyboard input"""
        if key.lower() == 'q':
            self.running = False
        
        elif key == '\r' or key == '\n':  # Enter
            if self.execute_step():
                self.current_step = min(len(self.STEPS), self.current_step + 1)
            
            if self.current_step >= len(self.STEPS):
                self.running = False
    
    def run(self):
        """Main loop"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            sys.stdout.write("\033[?25l")  # Hide cursor
            
            while self.running and self.current_step < len(self.STEPS):
                self.render()
                
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    self.handle_input(key)
        
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write("\033[?25h")  # Show cursor

if __name__ == "__main__":
    wizard = TunnelWizard()
    wizard.run()

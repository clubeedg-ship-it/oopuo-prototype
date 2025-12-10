#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Controller (Sidebar Menu)
Persistent navigation menu that never closes
"""
import sys
import os
import tty
import termios
import select
import shutil
import subprocess
from colors import col, glitch_text, box_chars, bold, C_PRIMARY, C_ACCENT, C_MUTED, C_TEXT, C_ERROR, C_SUCCESS
from config import config
from ipc import ipc

class Controller:
    """The persistent sidebar menu"""
    
    def __init__(self):
        self.menu_items = [
            "DASHBOARD",
            "CONNECT BRAIN",
            "CONNECT GUARD",
            "LIVE LOGS",
            "TIME MACHINE",
            "SETTINGS",
            "DISCONNECT",
            "EXIT"
        ]
        self.menu_idx = 0
        self.running = True
        self.width, self.height = shutil.get_terminal_size()
        
        # Check Cloudflare tunnel status
        self.tunnel_connected = config.get('cloudflare.tunnel_configured', False)
    
    def check_tunnel_status(self):
        """Check if Cloudflare tunnel is running"""
        try:
            result = subprocess.run(
                f"pct exec {config.get('ids.guard_ct')} -- systemctl is-active cloudflared",
                shell=True,
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.stdout.strip() == "active"
        except:
            return False
    
    def render(self):
        """Render the sidebar menu"""
        self.width, self.height = shutil.get_terminal_size()
        
        # Clear screen
        sys.stdout.write("\033[H\033[J")
        
        # Get box characters
        box = box_chars('double')
        
        # Calculate menu box dimensions
        menu_width = self.width - 4
        menu_start_y = 2
        
        # Draw top border
        sys.stdout.write(f"\033[{menu_start_y};2H")
        sys.stdout.write(col(box['tl'] + box['h'] * (menu_width - 2) + box['tr'], C_PRIMARY))
        
        # Draw menu items
        current_y = menu_start_y + 1
        
        for i, item in enumerate(self.menu_items):
            sys.stdout.write(f"\033[{current_y};2H")
            
            if i == self.menu_idx:
                # Selected item
                prefix = "➜ "
                text = glitch_text(item, 0.02) if item != "DISCONNECT" else item
                line = prefix + bold(col(text, C_ACCENT))
            else:
                # Unselected item
                prefix = "  "
                line = prefix + col(item, C_PRIMARY if item != "DISCONNECT" else C_MUTED)
            
            # Pad to full width
            padding = " " * (menu_width - len(prefix) - len(item) - 4)
            sys.stdout.write(col(box['v'], C_PRIMARY) + " " + line + padding + " " + col(box['v'], C_PRIMARY))
            
            current_y += 1
        
        # Draw separator
        current_y += 1
        sys.stdout.write(f"\033[{current_y};2H")
        sys.stdout.write(col(box['l'] + box['h'] * (menu_width - 2) + box['r'], C_PRIMARY))
        current_y += 1
        
        # Cloudflare Tunnel notification
        if not self.tunnel_connected and not self.check_tunnel_status():
            sys.stdout.write(f"\033[{current_y};2H")
            sys.stdout.write(col(box['v'], C_PRIMARY))
            sys.stdout.write(" " + col("⚠ ", C_ERROR) + col("LXC not connected!", C_TEXT))
            
            current_y += 1
            sys.stdout.write(f"\033[{current_y};2H")
            sys.stdout.write(col(box['v'], C_PRIMARY))
            sys.stdout.write(" " + col("Connect now in SETTINGS", C_MUTED))
            
            current_y += 1
        else:
            sys.stdout.write(f"\033[{current_y};2H")
            sys.stdout.write(col(box['v'], C_PRIMARY))
            sys.stdout.write(" " + col("✓ Tunnel active", C_SUCCESS))
            current_y += 1
        
        # Fill remaining space
        while current_y < self.height - 1:
            sys.stdout.write(f"\033[{current_y};2H")
            sys.stdout.write(col(box['v'] + " " * (menu_width - 2) + box['v'], C_PRIMARY))
            current_y += 1
        
        # Bottom border
        sys.stdout.write(f"\033[{current_y};2H")
        sys.stdout.write(col(box['bl'] + box['h'] * (menu_width - 2) + box['br'], C_PRIMARY))
        
        sys.stdout.flush()
    
    def handle_input(self, key):
        """Handle keyboard input"""
        if key == '\x1b':  # Escape sequence
            # Read next 2 characters for arrow keys
            next_chars = sys.stdin.read(2)
            if next_chars == '[A':  # Up arrow
                self.menu_idx = max(0, self.menu_idx - 1)
            elif next_chars == '[B':  # Down arrow
                self.menu_idx = min(len(self.menu_items) - 1, self.menu_idx + 1)
        
        elif key == '\r' or key == '\n':  # Enter
            self.execute_menu_item()
        
        elif key == '\x03':  # Ctrl+C
            self.running = False
    
    def execute_menu_item(self):
        """Execute selected menu item"""
        selected = self.menu_items[self.menu_idx]
        
        # Send command via IPC to viewport manager
        if selected == "DASHBOARD":
            ipc.send("SHOW_DASHBOARD")
        elif selected == "CONNECT BRAIN":
            ipc.send("CONNECT_BRAIN")
        elif selected == "CONNECT GUARD":
            ipc.send("CONNECT_GUARD")
        elif selected == "LIVE LOGS":
            ipc.send("SHOW_LOGS")
        elif selected == "TIME MACHINE":
            ipc.send("SHOW_TIMEMACHINE")
        elif selected == "SETTINGS":
            ipc.send("SHOW_SETTINGS")
        elif selected == "DISCONNECT":
            ipc.send("DISCONNECT")
        elif selected == "EXIT":
            ipc.send("EXIT")
            self.running = False
    
    def run(self):
        """Main loop"""
        # Setup terminal
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            sys.stdout.write("\033[?25l")  # Hide cursor
            
            while self.running:
                self.render()
                
                # Check for input (timeout 0.1s)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    self.handle_input(key)
        
        except Exception as e:
            with open(config.get('LOG_FILE', '/tmp/oopuo.log'), 'a') as f:
                f.write(f"[CONTROLLER] Error: {e}\n")
        
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write("\033[?25h")  # Show cursor

if __name__ == "__main__":
    controller = Controller()
    controller.run()

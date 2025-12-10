#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Settings Module
Configurable system parameters
"""
import sys
import shutil
import tty
import termios
import select
from colors import col, box_chars, bold, C_PRIMARY, C_SUCCESS, C_ERROR, C_MUTED, C_TEXT, C_ACCENT
from config import config
from tunnel_wizard import TunnelWizard

class Settings:
    """Interactive settings configuration"""
    
    def __init__(self):
        self.menu_items = [
            ("VM Resources", "vm_resources"),
            ("Credentials", "credentials"),
            ("Theme Colors", "theme"),
            ("Snapshot Settings", "snapshots"),
            ("Cloudflare Tunnel", "tunnel"),
            ("Back", "back")
        ]
        self.selected_idx = 0
        self.running = True
        self.width, self.height = shutil.get_terminal_size()
    
    def render(self):
        """Render settings menu"""
        self.width, self.height = shutil.get_terminal_size()
        
        # Clear screen
        sys.stdout.write("\033[H\033[J")
        
        box = box_chars('double')
        
        # Title
        sys.stdout.write("\033[2;2H")
        sys.stdout.write(bold(col("═══ SETTINGS ═══", C_PRIMARY)))
        
        sys.stdout.write("\033[4;2H")
        sys.stdout.write(col("Configure OOPUO Desktop Environment", C_MUTED))
        
        # Menu
        start_y = 6
        for i, (label, key) in enumerate(self.menu_items):
            current_y = start_y + i
            sys.stdout.write(f"\033[{current_y};2H")
            
            if i == self.selected_idx:
                prefix = "➜ "
                text = bold(col(label, C_ACCENT))
            else:
                prefix = "  "
                text = col(label, C_PRIMARY)
            
            sys.stdout.write(prefix + text)
        
        # Instructions
        sys.stdout.write(f"\033[{self.height-3};2H")
        sys.stdout.write(col("↑/↓ Navigate  |  Enter: Select  |  Q: Back", C_TEXT))
        
        sys.stdout.flush()
    
    def show_vm_resources(self):
        """Show VM resource settings"""
        brain_cores = config.get('resources.brain.cores', 4)
        brain_mem = config.get('resources.brain.mem', 8192)
        brain_disk = config.get('resources.brain.disk', 80)
        
        sys.stdout.write("\033[H\033[J")
        sys.stdout.write("\033[2;2H")
        sys.stdout.write(bold(col("VM Resources (Brain)", C_PRIMARY)))
        
        sys.stdout.write("\033[4;2H")
        sys.stdout.write(col(f"CPU Cores: {brain_cores}", C_TEXT))
        
        sys.stdout.write("\033[5;2H")
        sys.stdout.write(col(f"RAM: {brain_mem} MB", C_TEXT))
        
        sys.stdout.write("\033[6;2H")
        sys.stdout.write(col(f"Disk: {brain_disk} GB", C_TEXT))
        
        sys.stdout.write("\033[8;2H")
        sys.stdout.write(col("(Changes require VM rebuild)", C_MUTED))
        
        sys.stdout.write(f"\033[{self.height-2};2H")
        sys.stdout.write(col("Press any key to return", C_TEXT))
        sys.stdout.flush()
        
        sys.stdin.read(1)
    
    def show_tunnel_wizard(self):
        """Launch Cloudflare Tunnel wizard"""
        wizard = TunnelWizard()
        wizard.run()
    
    def handle_input(self, key):
        """Handle keyboard input"""
        if key.lower() == 'q':
            self.running = False
        
        elif key == '\x1b':  # Arrow keys
            next_chars = sys.stdin.read(2)
            if next_chars == '[A':  # Up
                self.selected_idx = max(0, self.selected_idx - 1)
            elif next_chars == '[B':  # Down
                self.selected_idx = min(len(self.menu_items) - 1, self.selected_idx + 1)
        
        elif key == '\r' or key == '\n':  # Enter
            _, action = self.menu_items[self.selected_idx]
            
            if action == "back":
                self.running = False
            elif action == "vm_resources":
                self.show_vm_resources()
            elif action == "tunnel":
                self.show_tunnel_wizard()
    
    def run(self):
        """Main loop"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            sys.stdout.write("\033[?25l")  # Hide cursor
            
            while self.running:
                self.render()
                
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    self.handle_input(key)
        
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write("\033[?25h")  # Show cursor

if __name__ == "__main__":
    settings = Settings()
    settings.run()

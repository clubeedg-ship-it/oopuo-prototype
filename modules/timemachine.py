#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Time Machine
Git-like snapshot system for VM rollback
"""
import sys
import os
import subprocess
import shutil
import tty
import termios
import select
from datetime import datetime
from colors import col, box_chars, bold, C_PRIMARY, C_SUCCESS, C_ERROR, C_MUTED, C_TEXT, C_ACCENT
from config import config

class TimeMachine:
    """Snapshot management interface"""
    
    def __init__(self):
        self.vmid = config.get('ids.brain_vm', 200)
        self.snapshots = []
        self.selected_idx = 0
        self.running = True
        self.width, self.height = shutil.get_terminal_size()
    
    def get_snapshots(self):
        """Get list of snapshots for the VM"""
        try:
            result = subprocess.run(
                f"qm listsnapshot {self.vmid}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return []
            
            # Parse output
            # Format: snapname `-> description
            snapshots = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                if '`->' in line:
                    parts = line.split('`->')
                    name = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Try to parse timestamp from name
                    timestamp = "Unknown"
                    if 'auto-snap-' in name:
                        try:
                            # Format: auto-snap-YYYY-MM-DD_HH:MM
                            date_part = name.replace('auto-snap-', '')
                            timestamp = date_part.replace('_', ' ')
                        except:
                            pass
                    
                    snapshots.append({
                        'name': name,
                        'description': desc,
                        'timestamp': timestamp
                    })
            
            return snapshots
        
        except Exception as e:
            return []
    
    def create_snapshot(self):
        """Create a new snapshot"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H:%M')
        name = f"auto-snap-{timestamp}"
        desc = f"Manual snapshot created at {timestamp}"
        
        try:
            subprocess.run(
                f"qm snapshot {self.vmid} {name} --description '{desc}'",
                shell=True,
                timeout=30
            )
            return True
        except:
            return False
    
    def rollback_snapshot(self, snapshot_name):
        """Rollback to a specific snapshot"""
        try:
            # Stop VM
            subprocess.run(f"qm stop {self.vmid}", shell=True, timeout=30)
            
            # Rollback
            subprocess.run(
                f"qm rollback {self.vmid} {snapshot_name}",
                shell=True,
                timeout=30
            )
            
            # Start VM
            subprocess.run(f"qm start {self.vmid}", shell=True, timeout=30)
            
            return True
        except:
            return False
    
    def render(self):
        """Render the time machine interface"""
        self.width, self.height = shutil.get_terminal_size()
        
        # Clear screen
        sys.stdout.write("\033[H\033[J")
        
        box = box_chars('double')
        
        # Header
        sys.stdout.write("\033[2;2H")
        title = bold(col("═══ TIME MACHINE ═══", C_PRIMARY))
        sys.stdout.write(title)
        
        sys.stdout.write("\033[3;2H")
        subtitle = col(f"VM {self.vmid}: {len(self.snapshots)} snapshots available", C_MUTED)
        sys.stdout.write(subtitle)
        
        # Instructions
        sys.stdout.write("\033[5;2H")
        sys.stdout.write(col("↑/↓ Navigate  |  Enter: Rollback  |  N: New Snapshot  |  Q: Quit", C_TEXT))
        
        # Snapshot list
        list_start_y = 7
        
        if not self.snapshots:
            sys.stdout.write(f"\033[{list_start_y};2H")
            sys.stdout.write(col("No snapshots found. Press 'N' to create one.", C_MUTED))
        else:
            for i, snap in enumerate(self.snapshots):
                current_y = list_start_y + i
                
                if current_y >= self.height - 2:
                    break
                
                sys.stdout.write(f"\033[{current_y};2H")
                
                if i == self.selected_idx:
                    # Selected
                    prefix = "➜ "
                    name_text = bold(col(snap['name'], C_ACCENT))
                else:
                    prefix = "  "
                    name_text = col(snap['name'], C_PRIMARY)
                
                time_text = col(snap['timestamp'], C_SUCCESS)
                desc_text = col(snap['description'][:40], C_MUTED)
                
                line = f"{prefix}{name_text}  {time_text}  {desc_text}"
                sys.stdout.write(line)
        
        sys.stdout.flush()
    
    def handle_input(self, key):
        """Handle keyboard input"""
        if key.lower() == 'q':
            self.running = False
        
        elif key.lower() == 'n':
            # Create new snapshot
            sys.stdout.write(f"\033[{self.height-1};2H")
            sys.stdout.write(col("Creating snapshot...", C_TEXT))
            sys.stdout.flush()
            
            if self.create_snapshot():
                self.snapshots = self.get_snapshots()
                sys.stdout.write(f"\033[{self.height-1};2H")
                sys.stdout.write(col("✓ Snapshot created!  ", C_SUCCESS))
            else:
                sys.stdout.write(f"\033[{self.height-1};2H")
                sys.stdout.write(col("✗ Failed to create   ", C_ERROR))
        
        elif key == '\x1b':  # Escape sequence
            next_chars = sys.stdin.read(2)
            if next_chars == '[A':  # Up
                self.selected_idx = max(0, self.selected_idx - 1)
            elif next_chars == '[B':  # Down
                self.selected_idx = min(len(self.snapshots) - 1, self.selected_idx + 1)
        
        elif key == '\r' or key == '\n':  # Enter
            if self.snapshots and 0 <= self.selected_idx < len(self.snapshots):
                snap = self.snapshots[self.selected_idx]
                
                # Confirm
                sys.stdout.write(f"\033[{self.height-1};2H")
                sys.stdout.write(col(f"Rollback to {snap['name']}? (y/N): ", C_TEXT))
                sys.stdout.flush()
                
                confirm = sys.stdin.read(1)
                if confirm.lower() == 'y':
                    sys.stdout.write(f"\033[{self.height-1};2H")
                    sys.stdout.write(col("Rolling back... (VM will restart)", C_TEXT))
                    sys.stdout.flush()
                    
                    if self.rollback_snapshot(snap['name']):
                        sys.stdout.write(f"\033[{self.height-1};2H")
                        sys.stdout.write(col("✓ Rollback complete!              ", C_SUCCESS))
                    else:
                        sys.stdout.write(f"\033[{self.height-1};2H")
                        sys.stdout.write(col("✗ Rollback failed                 ", C_ERROR))
    
    def run(self):
        """Main loop"""
        # Load snapshots
        self.snapshots = self.get_snapshots()
        
        # Setup terminal
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
    tm = TimeMachine()
    tm.run()

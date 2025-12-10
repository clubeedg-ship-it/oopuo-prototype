#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Tmux Bootstrap Engine
Creates the 3-zone layout on startup
"""
import os
import subprocess
import time
from config import config, LOG_FILE

class TmuxBootstrap:
    """Manages tmux session creation and pane layout"""
    
    SESSION_NAME = "oopuo-desktop"
    
    def __init__(self):
        self.panes = config.get('panes', {})
    
    def log(self, msg):
        """Write to log file"""
        with open(LOG_FILE, 'a') as f:
            f.write(f"[BOOTSTRAP] {msg}\n")
    
    def run_tmux(self, cmd):
        """Execute tmux command"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            self.log(f"Error: {cmd} -> {e}")
            return False
    
    def session_exists(self):
        """Check if OOPUO session already exists"""
        result = subprocess.run(
            f"tmux has-session -t {self.SESSION_NAME} 2>/dev/null",
            shell=True
        )
        return result.returncode == 0
    
    def create_layout(self):
        """
        Create the 3-zone tmux layout:
        
        +-----------------------------------------------------------+
        |  HEADER (10%)                                             |
        +-------------------+---------------------------------------+
        |  SIDEBAR (25%)    |  MAIN (75%)                          |
        |                   |  +---------------------------------+ |
        |                   |  | MAIN (80%)                      | |
        |                   |  +---------------------------------+ |
        |                   |  | MINILOG (20%)                   | |
        +-------------------+---------------------------------------+
        """
        self.log("Creating tmux session layout...")
        
        # 1. Create new session with initial window
        if not self.run_tmux(f"tmux new-session -d -s {self.SESSION_NAME} -n oopuo"):
            self.log("Failed to create session")
            return False
        
        # 2. Split horizontally: top 10% = header, bottom 90% = workspace
        self.run_tmux(f"tmux split-window -v -p 90 -t {self.SESSION_NAME}:0.0")
        
        # 3. Split workspace vertically: left 25% = sidebar, right 75% = main
        self.run_tmux(f"tmux split-window -h -p 75 -t {self.SESSION_NAME}:0.1")
        
        # 4. Split main horizontally: top 80% = main, bottom 20% = minilog
        self.run_tmux(f"tmux split-window -v -p 20 -t {self.SESSION_NAME}:0.2")
        
        # 5. Name panes for easy targeting
        self.run_tmux(f"tmux select-pane -t {self.SESSION_NAME}:0.0 -T header")
        self.run_tmux(f"tmux select-pane -t {self.SESSION_NAME}:0.1 -T sidebar")
        self.run_tmux(f"tmux select-pane -t {self.SESSION_NAME}:0.2 -T main")
        self.run_tmux(f"tmux select-pane -t {self.SESSION_NAME}:0.3 -T minilog")
        
        self.log("Layout created successfully")
        return True
    
    def configure_tmux(self):
        """Apply OOPUO-specific tmux settings"""
        settings = [
            # Disable status bar (we have our own header)
            "set -g status off",
            
            # Disable mouse (keyboard-only interface)
            "set -g mouse off",
            
            # Pane border colors (BTOP-inspired)
            "set -g pane-border-style fg=colour240",
            "set -g pane-active-border-style fg=colour51",
            
            # Allow focus events
            "set -g focus-events on",
            
            # Increase scrollback
            "set -g history-limit 10000",
            
            # No delay for escape key
            "set -sg escape-time 0",
        ]
        
        for setting in settings:
            self.run_tmux(f"tmux {setting} -t {self.SESSION_NAME}")
    
    def setup_keybindings(self):
        """Configure OOPUO hotkeys"""
        bindings = [
            # F10 = Return to sidebar
            f"bind-key -n F10 select-pane -t {self.SESSION_NAME}:0.1",
            
            # Ctrl+Left/Right = Switch between sidebar and main
            f"bind-key -n C-Left select-pane -t {self.SESSION_NAME}:0.1",
            f"bind-key -n C-Right select-pane -t {self.SESSION_NAME}:0.2",
            
            # Disable default prefix key suggestions
            "unbind C-b",
            "set -g prefix C-a",
        ]
        
        for binding in bindings:
            self.run_tmux(f"tmux {binding}")
    
    def launch_modules(self):
        """Start the Python processes in each pane"""
        data_dir = config.get('DATA_DIR', '/opt/oopuo')
        
        # Header: metrics.py
        self.run_tmux(
            f"tmux send-keys -t {self.SESSION_NAME}:0.0 "
            f"'python3 {data_dir}/metrics.py' Enter"
        )
        
        # Sidebar: controller.py
        self.run_tmux(
            f"tmux send-keys -t {self.SESSION_NAME}:0.1 "
            f"'python3 {data_dir}/controller.py' Enter"
        )
        
        # Main: Initial welcome screen
        self.run_tmux(
            f"tmux send-keys -t {self.SESSION_NAME}:0.2 "
            f"'clear && echo \"[ VIEWPORT READY ]\"' Enter"
        )
        
        # MiniLog: System logs
        self.run_tmux(
            f"tmux send-keys -t {self.SESSION_NAME}:0.3 "
            f"'tail -f {LOG_FILE}' Enter"
        )
    
    def bootstrap(self):
        """Full bootstrap sequence"""
        self.log("=== OOPUO BOOTSTRAP START ===")
        
        # Kill existing session if present
        if self.session_exists():
            self.log("Existing session found, killing...")
            self.run_tmux(f"tmux kill-session -t {self.SESSION_NAME}")
            time.sleep(0.5)
        
        # Create layout
        if not self.create_layout():
            self.log("Failed to create layout")
            return False
        
        # Configure tmux
        self.configure_tmux()
        self.setup_keybindings()
        
        # Launch modules
        self.launch_modules()
        
        self.log("=== BOOTSTRAP COMPLETE ===")
        return True

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    bootstrap = TmuxBootstrap()
    success = bootstrap.bootstrap()
    
    if success:
        print("✓ OOPUO Desktop Environment initialized")
        print(f"  Run: tmux attach -t {bootstrap.SESSION_NAME}")
        sys.exit(0)
    else:
        print("✗ Bootstrap failed (see logs)")
        sys.exit(1)

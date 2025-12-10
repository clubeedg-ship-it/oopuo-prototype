#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Viewport Manager
Manages the main pane content via "targeted injection"
"""
import os
import subprocess
import threading
from config import config, LOG_FILE
from ipc import ipc

class ViewportManager:
    """Manages content in the main tmux pane"""
    
    def __init__(self):
        self.session = "oopuo-desktop"
        self.main_pane = config.get('panes.main', 'oopuo-desktop:0.2')
        self.current_view = "READY"
    
    def log(self, msg):
        """Write to log file"""
        with open(LOG_FILE, 'a') as f:
            f.write(f"[VIEWPORT] {msg}\n")
    
    def inject(self, command):
        """Send command to main pane"""
        try:
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.main_pane, command, 'Enter'],
                timeout=2
            )
            return True
        except Exception as e:
            self.log(f"Inject error: {e}")
            return False
    
    def clear_pane(self):
        """Clear the main pane"""
        self.inject('clear')
    
    def show_ready(self):
        """Show ready state"""
        self.clear_pane()
        self.inject('echo "[ VIEWPORT READY ]"')
        self.current_view = "READY"
    
    def show_dashboard(self):
        """Show dashboard in main pane"""
        self.clear_pane()
        self.inject(f'python3 {config.get("DATA_DIR", "/opt/oopuo")}/dashboard.py')
        self.current_view = "DASHBOARD"
    
    def connect_brain(self):
        """Open SSH to Brain VM with exit handler"""
        brain_ip = config.get('network.brain_ip')
        key_path = config.get('credentials.key_path')
        user = config.get('credentials.user')
        
        if not brain_ip:
            self.log("Brain IP not configured")
            self.show_message("ERROR: Brain IP not found. Deploy infrastructure first.")
            return
        
        self.log(f"Connecting to Brain: {user}@{brain_ip}")
        self.current_view = "SSH_BRAIN"
        
        # SSH wrapper that returns to ready state on exit
        wrapper = f"""
ssh -i {key_path} -o StrictHostKeyChecking=no {user}@{brain_ip}
echo "\n[ SSH Session Ended ]"
sleep 2
clear
echo "[ VIEWPORT READY ]"
"""
        # Write wrapper to temp file
        wrapper_path = "/tmp/oopuo_ssh_brain.sh"
        with open(wrapper_path, 'w') as f:
            f.write(wrapper)
        os.chmod(wrapper_path, 0o755)
        
        self.inject(f'bash {wrapper_path}')
    
    def connect_guard(self):
        """Open console to Guard LXC"""
        guard_id = config.get('ids.guard_ct')
        
        self.log(f"Connecting to Guard: CT {guard_id}")
        self.current_view = "GUARD"
        
        wrapper = f"""
pct enter {guard_id}
echo "\n[ Container Session Ended ]"
sleep 2
clear
echo "[ VIEWPORT READY ]"
"""
        wrapper_path = "/tmp/oopuo_guard.sh"
        with open(wrapper_path, 'w') as f:
            f.write(wrapper)
        os.chmod(wrapper_path, 0o755)
        
        self.inject(f'bash {wrapper_path}')
    
    def show_logs(self):
        """Show live logs module"""
        self.clear_pane()
        self.inject(f'python3 {config.get("DATA_DIR", "/opt/oopuo")}/logs.py')
        self.current_view = "LOGS"
    
    def show_timemachine(self):
        """Show time machine interface"""
        self.clear_pane()
        self.inject(f'python3 {config.get("DATA_DIR", "/opt/oopuo")}/timemachine.py')
        self.current_view = "TIMEMACHINE"
    
    def show_settings(self):
        """Show settings interface"""
        self.clear_pane()
        self.inject(f'python3 {config.get("DATA_DIR", "/opt/oopuo")}/settings.py')
        self.current_view = "SETTINGS"
    
    def disconnect(self):
        """Kill current process in main pane and reset"""
        self.log("Disconnecting current view")
        
        # Send Ctrl+C to main pane
        subprocess.run(
            ['tmux', 'send-keys', '-t', self.main_pane, 'C-c'],
            timeout=2
        )
        
        # Wait a bit then show ready
        import time
        time.sleep(0.5)
        self.show_ready()
    
    def show_message(self, msg):
        """Display a message in the main pane"""
        self.clear_pane()
        self.inject(f'echo "{msg}"')
    
    def handle_command(self, command):
        """Handle IPC command"""
        self.log(f"Received command: {command}")
        
        if command == "SHOW_DASHBOARD":
            self.show_dashboard()
        elif command == "CONNECT_BRAIN":
            self.connect_brain()
        elif command == "CONNECT_GUARD":
            self.connect_guard()
        elif command == "SHOW_LOGS":
            self.show_logs()
        elif command == "SHOW_TIMEMACHINE":
            self.show_timemachine()
        elif command == "SHOW_SETTINGS":
            self.show_settings()
        elif command == "DISCONNECT":
            self.disconnect()
        elif command == "EXIT":
            self.log("Exit requested")
            subprocess.run(['tmux', 'kill-session', '-t', self.session])
        else:
            self.log(f"Unknown command: {command}")
    
    def run(self):
        """Start listening for IPC commands"""
        self.log("Viewport manager started")
        self.show_ready()
        
        # Listen for commands
        ipc.listen(self.handle_command)

if __name__ == "__main__":
    manager = ViewportManager()
    manager.run()

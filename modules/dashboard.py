#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Dashboard
Main information display
"""
import sys
import shutil
from colors import col, box_chars, bold, C_PRIMARY, C_SUCCESS, C_ERROR, C_MUTED, C_TEXT
from config import config
import subprocess

def get_vm_status(vmid):
    """Get VM status"""
    try:
        result = subprocess.run(
            f"qm status {vmid}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=2
        )
        if "running" in result.stdout:
            return col("● RUNNING", C_SUCCESS)
        else:
            return col("● STOPPED", C_ERROR)
    except:
        return col("● UNKNOWN", C_MUTED)

def get_ct_status(ctid):
    """Get CT status"""
    try:
        result = subprocess.run(
            f"pct status {ctid}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=2
        )
        if "running" in result.stdout:
            return col("● RUNNING", C_SUCCESS)
        else:
            return col("● STOPPED", C_ERROR)
    except:
        return col("● UNKNOWN", C_MUTED)

def show_dashboard():
    """Display the main dashboard"""
    width, height = shutil.get_terminal_size()
    
    # Clear screen
    sys.stdout.write("\033[H\033[J")
    
    box = box_chars('double')
    
    # Title
    sys.stdout.write("\033[2;2H")
    sys.stdout.write(bold(col("═══ OOPUO DASHBOARD ═══", C_PRIMARY)))
    
    # System Status
    sys.stdout.write("\033[4;2H")
    sys.stdout.write(bold(col("SYSTEM STATUS", C_TEXT)))
    
    brain_vm = config.get('ids.brain_vm', 200)
    guard_ct = config.get('ids.guard_ct', 100)
    
    sys.stdout.write("\033[6;2H")
    vm_status = get_vm_status(brain_vm)
    sys.stdout.write(col(f"Brain (VM {brain_vm}):   ", C_TEXT) + vm_status)
    
    sys.stdout.write("\033[7;2H")
    ct_status = get_ct_status(guard_ct)
    sys.stdout.write(col(f"Guard (CT {guard_ct}):   ", C_TEXT) + ct_status)
    
    # Network Info
    sys.stdout.write("\033[9;2H")
    sys.stdout.write(bold(col("NETWORK", C_TEXT)))
    
    brain_ip = config.get('network.brain_ip', 'Not configured')
    guard_ip = config.get('network.guard_ip', 'Not configured')
    
    sys.stdout.write("\033[11;2H")
    sys.stdout.write(col(f"Brain IP:  {brain_ip}", C_MUTED))
    
    sys.stdout.write("\033[12;2H")
    sys.stdout.write(col(f"Guard IP:  {guard_ip}", C_MUTED))
    
    # Services
    sys.stdout.write("\033[14;2H")
    sys.stdout.write(bold(col("SERVICES", C_TEXT)))
    
    sys.stdout.write("\033[16;2H")
    sys.stdout.write(col(f"Coolify:  http://{brain_ip}:8000", C_PRIMARY))
    
    sys.stdout.write("\033[17;2H")
    sys.stdout.write(col(f"Jupyter:  http://{brain_ip}:8888", C_PRIMARY))
    
    sys.stdout.write("\033[18;2H")
    sys.stdout.write(col(f"SSH:      ssh adminuser@{brain_ip}", C_PRIMARY))
    
    # Instructions
    sys.stdout.write(f"\033[{height-3};2H")
    sys.stdout.write(col("Use the sidebar menu to navigate  |  Press Q to close", C_MUTED))
    
    sys.stdout.flush()
    
    # Wait for Q key
    import tty, termios, select
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        tty.setraw(fd)
        while True:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)
                if key.lower() == 'q':
                    break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    show_dashboard()

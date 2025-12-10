#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Live Logs Module
Aggregated log streaming from multiple sources
"""
import sys
import subprocess
import shutil
from colors import col, box_chars, C_PRIMARY, C_SUCCESS, C_MUTED, C_TEXT
from config import config

def show_logs():
    """Display aggregated logs from host and Brain VM"""
    width, height = shutil.get_terminal_size()
    
    # Clear screen
    sys.stdout.write("\033[H\033[J")
    
    box = box_chars('double')
    
    # Header
    sys.stdout.write("\033[2;2H")
    sys.stdout.write(col("═══ LIVE INTELLIGENCE ═══", C_PRIMARY))
    
    sys.stdout.write("\033[3;2H")
    sys.stdout.write(col("Streaming logs from Host + Brain VM  |  Press Ctrl+C to exit", C_MUTED))
    
    sys.stdout.flush()
    
    # Use tmux split to show two log streams
    main_pane = config.get('panes.main', 'oopuo-desktop:0.2')
    
    # Split main pane horizontally
    subprocess.run([
        'tmux', 'split-window', '-v', '-t', main_pane
    ])
    
    # Top pane: Host syslog
    subprocess.run([
        'tmux', 'send-keys', '-t', f'{main_pane}.0',
        'tail -f /var/log/syslog | grep -i --color=never "oopuo\\|error\\|warn"',
        'Enter'
    ])
    
    # Bottom pane: VBrain logs (if available)
    brain_ip = config.get('network.brain_ip')
    key_path = config.get('credentials.key_path')
    user = config.get('credentials.user')
    
    if brain_ip and key_path:
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{main_pane}.1',
            f'ssh -i {key_path} -o StrictHostKeyChecking=no {user}@{brain_ip} '
            f'"tail -f /var/log/syslog 2>/dev/null || echo \'Brain logs unavailable\'"',
            'Enter'
        ])
    else:
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{main_pane}.1',
            'echo "Brain VM not configured"',
            'Enter'
        ])

if __name__ == "__main__":
    show_logs()

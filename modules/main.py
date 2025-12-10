#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Main Orchestrator
Entry point that coordinates all components
"""
import sys
import os
import threading
import time

# Add modules to path
sys.path.insert(0, '/opt/oopuo')

from config import config, LOG_DIR, FIFO_PATH
from bootstrap import TmuxBootstrap
from viewport import ViewportManager
import subprocess

def setup_directories():
    """Ensure all required directories exist"""
    dirs = [
        LOG_DIR,
        "/etc/oopuo",
        "/root/oopuo_vault"
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def main():
    """Main entry point"""
    setup_directories()
    
    # Write startup log
    with open(f"{LOG_DIR}/system.log", 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"OOPUO Desktop Environment Starting...\n")
        f.write(f"{'='*60}\n")
    
    # Bootstrap tmux session
    bootstrap = TmuxBootstrap()
    
    if not bootstrap.bootstrap():
        print("✗ Failed to create tmux session")
        sys.exit(1)
    
    # Start viewport manager in background thread
    viewport = ViewportManager()
    viewport_thread = threading.Thread(target=viewport.run, daemon=True)
    viewport_thread.start()
    
    # Attach to tmux session (foreground)
    print("✓ OOPUO Desktop Environment initialized")
    print(f"  Attaching to tmux session: {bootstrap.SESSION_NAME}")
    
    os.execvp('tmux', ['tmux', 'attach-session', '-t', bootstrap.SESSION_NAME])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        with open(f"{LOG_DIR}/crash.log", 'w') as f:
            import traceback
            f.write(traceback.format_exc())
        print(f"✗ Fatal error (see crash log): {e}")
        sys.exit(1)

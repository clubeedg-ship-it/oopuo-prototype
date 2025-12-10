#!/usr/bin/env python3
"""
OOPUO Desktop Environment - IPC (Inter-Process Communication)
FIFO-based communication between panes
"""
import os
import time
from pathlib import Path
from config import FIFO_PATH, LOG_FILE

class IPC:
    """FIFO-based inter-process communication"""
    
    def __init__(self):
        self.fifo_path = FIFO_PATH
        self._ensure_fifo()
    
    def _ensure_fifo(self):
        """Create FIFO if it doesn't exist"""
        if os.path.exists(self.fifo_path):
            # Remove if it's not a FIFO
            if not os.path.isfifo(self.fifo_path):
                os.remove(self.fifo_path)
        
        if not os.path.exists(self.fifo_path):
            os.mkfifo(self.fifo_path)
    
    def send(self, command):
        """
        Send command to FIFO (non-blocking)
        
        Args:
            command: String command to send
        """
        try:
            # Open in non-blocking mode
            fd = os.open(self.fifo_path, os.O_WRONLY | os.O_NONBLOCK)
            os.write(fd, (command + "\n").encode())
            os.close(fd)
        except Exception as e:
            with open(LOG_FILE, 'a') as f:
                f.write(f"[IPC] Send error: {e}\n")
    
    def listen(self, callback):
        """
        Listen for commands on FIFO (blocking)
        
        Args:
            callback: Function to call with each received command
        """
        while True:
            try:
                with open(self.fifo_path, 'r') as fifo:
                    for line in fifo:
                        command = line.strip()
                        if command:
                            callback(command)
            except Exception as e:
                with open(LOG_FILE, 'a') as f:
                    f.write(f"[IPC] Listen error: {e}\n")
                time.sleep(1)

# Global instance
ipc = IPC()

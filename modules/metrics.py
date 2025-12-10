#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Header Metrics (BTOP-Inspired)
Displays GPU, CPU, RAM, and uptime with gradient bars
"""
import sys
import os
import time
import shutil
import subprocess
from datetime import datetime, timedelta
from colors import col, gradient_bar, temp_color, C_PRIMARY, C_SUCCESS, C_MUTED, C_TEXT, bold
from config import config

class MetricsRenderer:
    """Renders the top header pane with system metrics"""
    
    def __init__(self):
        self.history_cpu = []
        self.history_gpu = []
        self.max_history = 60  # Keep 60 data points
    
    def get_cpu_usage(self):
        """Get CPU usage percentage"""
        try:
            load = os.getloadavg()[0]
            cpu_count = os.cpu_count() or 1
            return min(100, int((load / cpu_count) * 100))
        except:
            return 0
    
    def get_ram_usage(self):
        """Get RAM usage as (used_gb, total_gb, percentage)"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            
            mem_total = 0
            mem_available = 0
            
            for line in lines:
                if line.startswith('MemTotal:'):
                    mem_total = int(line.split()[1])
                elif line.startswith('MemAvailable:'):
                    mem_available = int(line.split()[1])
            
            used = mem_total - mem_available
            used_gb = used / 1024 / 1024
            total_gb = mem_total / 1024 / 1024
            percent = int((used / mem_total) * 100) if mem_total > 0 else 0
            
            return used_gb, total_gb, percent
        except:
            return 0, 0, 0
    
    def get_gpu_info(self):
        """
        Get GPU usage and temperature
        Returns: (gpu_percent, temp_celsius, gpu_name)
        """
        try:
            # Try nvidia-smi first
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,name', 
                 '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                if len(parts) >= 3:
                    gpu_util = int(parts[0].strip())
                    gpu_temp = int(parts[1].strip())
                    gpu_name = parts[2].strip()
                    return gpu_util, gpu_temp, gpu_name
        except:
            pass
        
        # Try AMD rocm-smi
        try:
            result = subprocess.run(
                ['rocm-smi', '--showuse', '--showtemp'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                # Parse rocm-smi output (format varies)
                lines = result.stdout.split('\n')
                gpu_util = 0
                gpu_temp = 0
                
                for line in lines:
                    if 'GPU use' in line:
                        gpu_util = int(line.split()[-1].replace('%', ''))
                    if 'Temperature' in line:
                        gpu_temp = int(line.split()[-1].replace('°C', ''))
                
                return gpu_util, gpu_temp, "AMD GPU"
        except:
            pass
        
        # No GPU detected
        return 0, 0, "No GPU"
    
    def get_uptime(self):
        """Get system uptime as formatted string"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            
            delta = timedelta(seconds=int(uptime_seconds))
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "unknown"
    
    def render(self):
        """Render the header metrics"""
        width, _ = shutil.get_terminal_size()
        
        # Get metrics
        cpu = self.get_cpu_usage()
        mem_used, mem_total, mem_percent = self.get_ram_usage()
        gpu_util, gpu_temp, gpu_name = self.get_gpu_info()
        uptime = self.get_uptime()
        
        # Update history
        self.history_cpu.append(cpu)
        self.history_gpu.append(gpu_util)
        if len(self.history_cpu) > self.max_history:
            self.history_cpu.pop(0)
        if len(self.history_gpu) > self.max_history:
            self.history_gpu.pop(0)
        
        # Build header layout
        # Format: [ OOPUO OS ] | GPU: [bar] 45% 75°C | CPU: [bar] 23% | RAM: [bar] 4.2/16GB | UP: 12d 4h
        
        logo = bold(col("[ OOPUO OS ]", C_PRIMARY))
        
        # GPU section (most important!)
        gpu_bar = gradient_bar(gpu_util, 100, width=12)
        gpu_temp_col = temp_color(gpu_temp)
        gpu_section = (
            f"{col('GPU:', C_TEXT)} {gpu_bar} "
            f"{col(f'{gpu_util}%', C_SUCCESS)} "
            f"{col(f'{gpu_temp}°C', gpu_temp_col)}"
        )
        
        # CPU section
        cpu_bar = gradient_bar(cpu, 100, width=10)
        cpu_section = f"{col('CPU:', C_TEXT)} {cpu_bar} {col(f'{cpu}%', C_SUCCESS)}"
        
        # RAM section
        ram_bar = gradient_bar(mem_percent, 100, width=10)
        ram_section = (
            f"{col('RAM:', C_TEXT)} {ram_bar} "
            f"{col(f'{mem_used:.1f}/{mem_total:.1f}GB', C_SUCCESS)}"
        )
        
        # Uptime
        uptime_section = f"{col('UP:', C_TEXT)} {col(uptime, C_MUTED)}"
        
        # Combine sections
        sections = [logo, gpu_section, cpu_section, ram_section, uptime_section]
        header = "  ".join(sections)
        
        # Render (clear screen and print)
        sys.stdout.write("\033[H\033[J")  # Clear screen
        sys.stdout.write(header)
        sys.stdout.flush()
    
    def run(self):
        """Main loop: update every 1 second"""
        sys.stdout.write("\033[?25l")  # Hide cursor
        
        try:
            while True:
                self.render()
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[?25h")  # Show cursor

if __name__ == "__main__":
    renderer = MetricsRenderer()
    renderer.run()

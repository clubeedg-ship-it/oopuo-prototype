#!/usr/bin/env python3
"""
OOPUO Desktop Environment - Centralized Configuration
"""
import os
import json
from pathlib import Path

# Directories
CONF_DIR = "/etc/oopuo"
DATA_DIR = "/opt/oopuo"
LOG_DIR = "/var/log/oopuo"
VAULT_DIR = "/root/oopuo_vault"

# Files
CONFIG_FILE = f"{CONF_DIR}/config.json"
LOG_FILE = f"{LOG_DIR}/system.log"
CRASH_FILE = f"{LOG_DIR}/crash.log"
FIFO_PATH = "/tmp/oopuo_cmd"

# Default Configuration
DEFAULT_CONFIG = {
    "ids": {
        "brain_vm": 200,
        "guard_ct": 100
    },
    "network": {
        "bridge": "vmbr0",
        "host_ip": None,
        "gateway": None,
        "brain_ip": None,
        "guard_ip": None
    },
    "resources": {
        "brain": {
            "cores": 4,
            "mem": 8192,
            "disk": 80
        },
        "guard": {
            "cores": 1,
            "mem": 512,
            "disk": 4
        }
    },
    "credentials": {
        "user": "adminuser",
        "pass": "Oopuopu123!",
        "key_path": f"{VAULT_DIR}/oopuo_key"
    },
    "assets": {
        "cloud_img_url": "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img",
        "lxc_template": "ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
    },
    "panes": {
        "header": "oopuo-desktop:0.0",
        "sidebar": "oopuo-desktop:0.1",
        "main": "oopuo-desktop:0.2",
        "minilog": "oopuo-desktop:0.3"
    },
    "theme": {
        "primary": 51,      # Cyan
        "success": 46,      # Green
        "error": 196,       # Red
        "muted": 240,       # Grey
        "accent": 198,      # Pink
        "text": 255,        # White
        "gpu_temp_low": 46,     # Green for < 60°C
        "gpu_temp_mid": 226,    # Yellow for 60-80°C
        "gpu_temp_high": 196    # Red for > 80°C
    },
    "cloudflare": {
        "tunnel_installed": False,
        "tunnel_configured": False,
        "tunnel_name": None,
        "tunnel_id": None
    },
    "snapshot": {
        "auto_enabled": True,
        "interval_hours": 24,
        "retention_days": 30,
        "prefix": "auto-snap"
    }
}

class Config:
    """Configuration manager with persistence"""
    
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        """Load config from file or use defaults"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to add any new keys
                    return self._deep_merge(DEFAULT_CONFIG.copy(), loaded)
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()
    
    def _deep_merge(self, base, updates):
        """Recursively merge dictionaries"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def save(self):
        """Persist config to disk"""
        os.makedirs(CONF_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get(self, path, default=None):
        """Get nested config value using dot notation"""
        keys = path.split('.')
        value = self.data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, path, value):
        """Set nested config value using dot notation"""
        keys = path.split('.')
        target = self.data
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self.save()

# Global instance
config = Config()

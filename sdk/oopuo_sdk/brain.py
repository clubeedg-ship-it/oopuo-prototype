#!/usr/bin/env python3
"""
OOPUO SDK - Brain Connection
Manages connection to OOPUO Brain VM (Nomad/Consul/Vault)
"""
import requests
from typing import Optional, Dict, List

class Brain:
    """Connection to OOPUO Brain VM"""
    
    def __init__(self, host: str, nomad_port: int = 4646, consul_port: int = 8500, vault_port: int = 8200):
        """
        Initialize Brain connection
        
        Args:
            host: IP address or hostname of Brain VM
            nomad_port: Nomad API port (default: 4646)
            consul_port: Consul API port (default: 8500)
            vault_port: Vault API port (default: 8200)
        """
        self.host = host
        self.nomad_url = f"http://{host}:{nomad_port}"
        self.consul_url = f"http://{host}:{consul_port}"
        self.vault_url = f"http://{host}:{vault_port}"
        self._verified = False
    
    @classmethod
    def connect(cls, host: str):
        """
        Quick connection with verification
        
        Args:
            host: IP address or hostname of Brain VM
        
        Returns:
            Brain instance
        
        Raises:
            ConnectionError: If Brain is unreachable
        """
        brain = cls(host)
        brain.verify_connection()
        return brain
    
    def verify_connection(self):
        """
        Verify that Nomad is reachable
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            r = requests.get(f"{self.nomad_url}/v1/status/leader", timeout=5)
            r.raise_for_status()
            self._verified = True
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Brain at {self.host}: {e}")
    
    def deploy_agent(self, name: str, model: str, gpu: bool = False, **kwargs):
        """
        Deploy AI agent as Nomad job
        
        Args:
            name: Agent name (must be unique)
            model: Model name (e.g., 'llama-70b', 'mistral-7b')
            gpu: Whether to require GPU
            **kwargs: Additional parameters (cpu, memory, replicas, etc.)
        
       Returns:
            Agent instance
        """
        from .agent import Agent
        return Agent.deploy(self, name, model, gpu, **kwargs)
    
    def list_jobs(self) -> List[Dict]:
        """
        List all running Nomad jobs
        
        Returns:
            List of job dicts with status info
        """
        try:
            r = requests.get(f"{self.nomad_url}/v1/jobs", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise RuntimeError(f"Failed to list jobs: {e}")
    
    def get_job(self, job_id: str) -> Dict:
        """
        Get details of a specific job
        
        Args:
            job_id: Job ID
        
        Returns:
            Job details dict
        """
        try:
            r = requests.get(f"{self.nomad_url}/v1/job/{job_id}", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get job {job_id}: {e}")
    
    def stop_job(self, job_id: str):
        """
        Stop a running job
        
        Args:
            job_id: Job ID to stop
        """
        try:
            r = requests.delete(f"{self.nomad_url}/v1/job/{job_id}", timeout=5)
            r.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Failed to stop job {job_id}: {e}")
    
    def get_services(self) -> Dict:
        """
        List services from Consul
        
        Returns:
            Dict of service names to tags
        """
        try:
            r = requests.get(f"{self.consul_url}/v1/catalog/services", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise RuntimeError(f"Failed to list services: {e}")
    
    def get_service_nodes(self, service_name: str) -> List[Dict]:
        """
        Get nodes providing a specific service
        
        Args:
            service_name: Service name
        
        Returns:
            List of node dicts with address/port info
        """
        try:
            r = requests.get(
                f"{self.consul_url}/v1/catalog/service/{service_name}",
                timeout=5
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get service nodes for {service_name}: {e}")
    
    def get_node_info(self) -> Dict:
        """
        Get Nomad node (Brain) information
        
        Returns:
            Node info dict with resources, attributes, etc.
        """
        try:
            r = requests.get(f"{self.nomad_url}/v1/nodes", timeout=5)
            r.raise_for_status()
            nodes = r.json()
            
            if nodes:
                # Get detailed info for first node
                node_id = nodes[0]['ID']
                r = requests.get(f"{self.nomad_url}/v1/node/{node_id}", timeout=5)
                r.raise_for_status()
                return r.json()
            
            return {}
        except Exception as e:
            raise RuntimeError(f"Failed to get node info: {e}")
    
    def has_gpu(self) -> bool:
        """
        Check if Brain has GPU available
        
        Returns:
            True if GPU is enabled
        """
        try:
            node = self.get_node_info()
            meta = node.get('Meta', {})
            return meta.get('gpu_enabled') == 'true'
        except:
            return False
    
    def __repr__(self):
        return f"Brain(host={self.host}, verified={self._verified})"

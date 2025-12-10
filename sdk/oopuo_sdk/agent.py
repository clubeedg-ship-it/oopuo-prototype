#!/usr/bin/env python3
"""
OOPUO SDK - AI Agent Deployment
Deploys and manages AI agents as Nomad jobs
"""
import requests
import json
from typing import Optional, Dict

class Agent:
    """AI Agent running on OOPUO"""
    
    def __init__(self, brain, job_id: str):
        """
        Initialize Agent instance
        
        Args:
            brain: Brain instance
            job_id: Nomad job ID
        """
        self.brain = brain
        self.job_id = job_id
        self._service_address = None
    
    @classmethod
    def deploy(cls, brain, name: str, model: str, gpu: bool = False, **kwargs):
        """
        Deploy new AI agent as Nomad job
        
        Args:
            brain: Brain instance
            name: Agent name (job ID)
            model: Model name (e.g., 'llama-70b')
            gpu: Require GPU
            **kwargs: Additional params:
                - cpu: CPU cores (default: 1000 = 1 core)
                - memory: Memory in MB (default: 4096)
                - replicas: Number of instances (default: 1)
                - image: Docker image (default: inferred from model)
        
        Returns:
            Agent instance
        """
        cpu = kwargs.get('cpu', 1000)
        memory = kwargs.get('memory', 4096)
        replicas = kwargs.get('replicas', 1)
        image = kwargs.get('image', f"ollama/ollama")  # Default to Ollama
        
        # Build Nomad job specification
        job_spec = {
            "Job": {
                "ID": name,
                "Name": name,
                "Type": "service",
                "Datacenters": ["oopuo-dc1"],
                "TaskGroups": [{
                    "Name": f"{name}-group",
                    "Count": replicas,
                    "Tasks": [{
                        "Name": f"{name}-task",
                        "Driver": "docker",
                        "Config": {
                            "image": image,
                            "ports": ["http"],
                            "args": ["serve", model] if "ollama" in image else []
                        },
                        "Resources": {
                            "CPU": cpu,
                            "MemoryMB": memory,
                            "Networks": [{
                                "DynamicPorts": [{
                                    "Label": "http",
                                    "To": 11434  # Ollama default port
                                }]
                            }]
                        },
                        "Services": [{
                            "Name": name,
                            "PortLabel": "http",
                            "Tags": [f"model:{model}", "oopuo-agent"]
                        }]
                    }]
                }]
            }
        }
        
        # Add GPU requirement if requested
        if gpu:
            job( spec["Job"]["TaskGroups"][0]["Tasks"][0]["Resources"]["Devices"] = [{
                "Name": "nvidia/gpu",
                "Count": 1
            }]
        
        # Submit job to Nomad
        try:
            r = requests.post(
                f"{brain.nomad_url}/v1/jobs",
                json=job_spec,
                timeout=10
            )
            r.raise_for_status()
            
            return cls(brain, name)
        
        except Exception as e:
            raise RuntimeError(f"Failed to deploy agent: {e}")
    
    def get_status(self) -> Dict:
        """
        Get agent job status
        
        Returns:
            Job status dict
        """
        return self.brain.get_job(self.job_id)
    
    def get_allocations(self) -> list:
        """
        Get job allocations (running instances)
        
        Returns:
            List of allocation dicts
        """
        try:
            r = requests.get(
                f"{self.brain.nomad_url}/v1/job/{self.job_id}/allocations",
                timeout=5
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get allocations: {e}")
    
    def discover_service(self) -> Optional[str]:
        """
        Discover agent service address via Consul
        
        Returns:
            Service address (host:port) or None
        """
        try:
            nodes = self.brain.get_service_nodes(self.job_id)
            
            if nodes:
                node = nodes[0]
                address = node.get('ServiceAddress') or node.get('Address')
                port = node.get('ServicePort')
                
                if address and port:
                    self._service_address = f"{address}:{port}"
                    return self._service_address
            
            return None
        except:
            return None
    
    def infer(self, prompt: str, **kwargs) -> Dict:
        """
        Run inference on the agent
        
        Args:
            prompt: Input prompt
            **kwargs: Model-specific parameters
        
        Returns:
            Inference result dict
        
        Note: This is a simplified example for Ollama.
              Real implementation should handle different model APIs.
        """
        # Discover service if not already done
        if not self._service_address:
            self._service_address = self.discover_service()
        
        if not self._service_address:
            raise RuntimeError("Agent service not found - may still be starting")
        
        # Example Ollama API call
        try:
            payload = {
                "model": self.job_id,  # Assumes job name = model name
                "prompt": prompt,
                "stream": False
            }
            payload.update(kwargs)
            
            r = requests.post(
                f"http://{self._service_address}/api/generate",
                json=payload,
                timeout=120  # Generous timeout for model inference
            )
            r.raise_for_status()
            
            return r.json()
        
        except Exception as e:
            raise RuntimeError(f"Inference failed: {e}")
    
    def stop(self):
        """Stop the agent (delete Nomad job)"""
        self.brain.stop_job(self.job_id)
    
    def scale(self, count: int):
        """
        Scale agent to N replicas
        
        Args:
            count: Number of replicas
        """
        try:
            # Get current job spec
            job = self.brain.get_job(self.job_id)
            
            # Update count
            job["TaskGroups"][0]["Count"] = count
            
            # Re-submit
            r = requests.post(
                f"{self.brain.nomad_url}/v1/job/{self.job_id}",
                json={"Job": job},
                timeout=10
            )
            r.raise_for_status()
        
        except Exception as e:
            raise RuntimeError(f"Failed to scale agent: {e}")
    
    def __repr__(self):
        return f"Agent(job_id={self.job_id}, address={self._service_address})"

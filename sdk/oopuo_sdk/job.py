#!/usr/bin/env python3
"""
OOPUO SDK - Nomad Job Wrapper
Low-level Nomad job management
"""
import requests
from typing import Dict, Optional

class Job:
    """Low-level Nomad job wrapper"""
    
    def __init__(self, brain, job_id: str):
        self.brain = brain
        self.job_id = job_id
    
    @classmethod
    def create(cls, brain, job_spec: Dict):
        """
        Create a Nomad job from specification
        
        Args:
            brain: Brain instance
            job_spec: Nomad job specification dict
        
        Returns:
            Job instance
        """
        try:
            r = requests.post(
                f"{brain.nomad_url}/v1/jobs",
                json=job_spec,
                timeout=10
            )
            r.raise_for_status()
            
            job_id = job_spec["Job"]["ID"]
            return cls(brain, job_id)
        
        except Exception as e:
            raise RuntimeError(f"Failed to create job: {e}")
    
    def get_info(self) -> Dict:
        """Get job information"""
        return self.brain.get_job(self.job_id)
    
    def stop(self):
        """Stop the job"""
        self.brain.stop_job(self.job_id)
    
    def __repr__(self):
        return f"Job(id={self.job_id})"

#!/usr/bin/env python3
"""
OOPUO SDK Example: Deploy LLaMA Model

This example shows how to deploy an AI agent using the OOPUO SDK.
"""
import sys
import time
sys.path.insert(0, '..')

from oopuo_sdk import Brain

def main():
    # Connect to Brain
    print("Connecting to OOPUO Brain...")
    brain = Brain.connect("192.168.1.222")  # Replace with your Brain IP
    
    print(f"✓ Connected to {brain.host}")
    
    # Check GPU availability
    if brain.has_gpu():
        print("✓ GPU available")
        use_gpu = True
    else:
        print("⚠ No GPU detected - deploying without GPU")
        use_gpu = False
    
    # Deploy LLaMA agent
    print("\nDeploying LLaMA-7B agent...")
    agent = brain.deploy_agent(
        name="llama-7b-chat",
        model="llama2:7b",
        gpu=use_gpu,
        cpu=2000,  # 2 cores
        memory=8192  # 8GB RAM
    )
    
    print(f"✓ Agent deployed: {agent.job_id}")
    
    # Wait for agent to start
    print("\nWaiting for agent to start (this may take 1-2 minutes)...")
    for i in range(30):
        try:
            if agent.discover_service():
                print(f"✓ Agent ready at {agent._service_address}")
                break
        except:
            pass
        
        time.sleep(2)
        print(".", end="", flush=True)
    else:
        print("\n⚠ Agent took too long to start")
        sys.exit(1)
    
    # Run inference
    print("\n\nRunning inference...")
    prompt = "Explain quantum computing in simple terms"
    
    result = agent.infer(prompt)
    print(f"\nPrompt: {prompt}")
    print(f"Response: {result.get('response', 'No response')}")
    
    # Keep agent running or stop it
    choice = input("\n\nKeep agent running? (y/n): ")
    
    if choice.lower() != 'y':
        print("\nStopping agent...")
        agent.stop()
        print("✓ Agent stopped")
    else:
        print(f"\n✓ Agent is running")
        print(f"  Job ID: {agent.job_id}")
        print(f"  Service: {agent._service_address}")
        print(f"  Nomad UI: http://{brain.host}:4646")

if __name__ == "__main__":
    main()

# OOPUO SDK

Python SDK for programmatic access to OOPUO AI Infrastructure.

## Installation

```bash
cd sdk
pip install -e .
```

## Quick Start

```python
from oopuo_sdk import Brain

# Connect to your OOPUO Brain
brain = Brain.connect("192.168.1.222")

# Deploy an AI agent
agent = brain.deploy_agent(
    name="llama-7b",
    model="llama2:7b",
    gpu=True,
    memory=816  # 8GB
)

# Run inference
result = agent.infer("Explain AI in simple terms")
print(result['response'])

# Stop when done
agent.stop()
```

## Features

- **Brain Connection**: Connect to Nomad/Consul/Vault APIs
- **Agent Deployment**: Deploy AI models as Nomad jobs
- **Service Discovery**: Automatic service discovery via Consul
- **GPU Support**: Request GPU resources for model inference
- **Job Management**: List, scale, and stop running agents

## API Reference

### Brain

```python
brain = Brain.connect(host="192.168.1.222")

# List all jobs
jobs = brain.list_jobs()

# Get services
services = brain.get_services()

# Check GPU availability
has_gpu = brain.has_gpu()
```

### Agent

```python
# Deploy agent
agent = brain.deploy_agent(
    name="my-agent",
    model="llama2:7b",
    gpu=True,
    cpu=2000,  # 2 cores
    memory=8192,  # 8GB
    replicas=2  # Number of instances
)

# Run inference
result = agent.infer("Your prompt here")

# Scale agent
agent.scale(count=5)

# Stop agent
agent.stop()
```

## Examples

See `examples/` directory:
- `deploy_llama.py`: Deploy and interact with LLaMA model
- More examples coming in Phase 2-4

## Requirements

- Python >= 3.8
- OOPUO v9 infrastructure deployed
- Network access to Brain VM

## License

Internal Use

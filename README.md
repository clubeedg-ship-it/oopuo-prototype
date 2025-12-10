# OOPUO v9 - AI Infrastructure OS

Complete upgrade from v34 to enterprise AI orchestration platform.

## Quick Start

```bash
# On Proxmox host
bash oopuo_v34.sh  # This now installs v9 stack

# Start systemsystemctl start oopuo
```

## What's New in v9

### 🔴 Critical Features

1. **Nomad/Consul/Vault Stack** (Replaces Coolify)
   - Nomad: Distributed job scheduler
   - Consul: Service mesh & discovery
   - Vault: Secrets management
   - Full Docker orchestration

2. **GPU Passthrough Automation**
   - Auto-detect NVIDIA/AMD GPUs
   - IOMMU setup with reboot detection
   - VFIO driver configuration
   - In-VM driver installation (CUDA 12.4)
   - Nomad GPU plugin integration

3. **Comprehensive AI Stack**
   - **Deep Learning**: PyTorch, TensorFlow, JAX
   - **LLM Tools**: vLLM, Ollama, llama.cpp, Transformers
   - **Vector DBs**: ChromaDB, Qdrant, Weaviate, Milvus, FAISS
   - **Dev Tools**: JupyterLab, MLflow, Ray, Weights & Biases
   - **Privacy**: PySyft, Opacus, TensorFlow Privacy (Phase 2 ready)

4. **Python SDK**
   - Programmatic access to OOPUO
   - Deploy agents with one line of code
   - Service discovery via Consul
   - GPU-aware resource allocation

## Services & Ports

After deployment, access:

- **Nomad UI**: http://192.168.x.222:4646
- **Consul UI**: http://192.168.x.222:8500
- **Vault UI**: http://192.168.x.222:8200
- **JupyterLab**: Run manually with `jupyter lab --ip=0.0.0.0`

## Python SDK Usage

```python
from oopuo_sdk import Brain

# Connect
brain = Brain.connect("192.168.1.222")

# Deploy agent
agent = brain.deploy_agent(
    name="llama-70b",
    model="llama2:70b",
    gpu=True,
    memory=40960  # 40GB
)

# Inference
result = agent.infer("Explain quantum computing")
print(result['response'])
```

See `sdk/README.md` for full API documentation.

## GPU Setup

If you have a GPU:

1. Installer auto-detects GPU
2. Enables IOMMU (may require reboot)
3. Configures passthrough to VM
4. Installs CUDA drivers in VM
5. Updates Nomad GPU plugin

**Manual verification:**
```bash
# SSH to Brain
ssh adminuser@192.168.x.222

# Check GPU
nvidia-smi

# Check Nomad sees GPU
curl http://localhost:4646/v1/nodes | jq '.[0].Meta.gpu_enabled'
```

## Architecture

```
Proxmox Host
├─ Guard (LXC 100) - Cloudflare Tunnel
└─ Brain (VM 200) - AI Orchestration
   ├─ Nomad (scheduler)
   ├─ Consul (service mesh)
   ├─ Vault (secrets)
   ├─ Docker (+ GPU support)
   └─ AI Stack (PyTorch, TF, JAX, vLLM, etc.)
```

## Migration from v34

**Breaking Changes:**
- Coolify → Nomad stack (Coolify deployments NOT migrated)
- New ports (4646, 8500, 8200)
- GPU passthrough may require host reboot

**Preserved:**
- SSH keys
- VM/CT IDs (200, 100)
- Network configuration
- Cloudflare tunnel

## File Structure

```
/opt/oopuo/
├── gpu_manager.py    # GPU passthrough automation
├── infra.py          # v9 deployment (Nomad stack)
└── ... (other modules from v34)

/Users/ottogen/oopuo-prototype/
├── modules/          # 15 Python modules
├── sdk/              # Python SDK
│   ├── oopuo_sdk/
│   │   ├── brain.py
│   │   ├── agent.py
│   │   └── job.py
│   ├── examples/
│   │   └── deploy_llama.py
│   └── setup.py
└── oopuo_v34.sh      # Installer (now installs v9)
```

## Troubleshooting

**GPU not detected:**
```bash
lspci | grep -i 'nvidia\|amd'  # Check if host sees GPU
```

**Nomad not starting:**
```bash
systemctl status nomad
journalctl -u nomad -f
```

**SDK connection fails:**
```bash
# Check Nomad is reachable
curl http://192.168.x.222:4646/v1/status/leader
```

## Phases 2-4 (Future)

- **Phase 2**: Privacy primitives (PySyft, federated learning)
- **Phase 3**: Multi-node federation (Consul cluster)
- **Phase 4**: Decentralized marketplace (agent registry, smart contracts)

## Support

- **Logs**: `/var/log/oopuo/system.log`
- **Config**: `/etc/oopuo/config.json`
- **Crash logs**: `/var/log/oopuo/crash.log`

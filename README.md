# MeshCore Agent Framework

**Juliet** — A lightweight, autonomous AI agent native to the [MeshCore](https://meshcore.io) mesh network.

## About

The **MeshCore Agent Framework** makes it easy to deploy intelligent agents directly onto decentralized MeshCore networks.

Agents run on accessible hardware connected via USB serial to a MeshCore node. They listen for `@!` mentions in rooms, respond intelligently, and respect the strict bandwidth and message-length constraints of the mesh.

### Features

- Native MeshCore integration (serial + contact/room support)
- Smart message splitting with numbered parts (`[1/3]`)
- Robust sender name resolution using contact signatures
- Clean async architecture with proper shutdown
- Easy to extend with tools, memory, and local models
- Currently powered by Grok API (with local fallback planned)

### Quick Start

#### Using UV (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd mcagent

# Create virtual environment and install dependencies from pyproject.toml
uv venv
uv sync

# Run the agent
uv run main.py

```

#### The Other Way (for cavemen...)

```bash
# Create a venv
python -m venv venv
# Activate the env
source .venv/bin/activate
# Install Requirements
pip install -r requirements.txt
# Run the agent
python main.py
```

Send any message containing `@!` in the room to interact.

### Goals

- Create a practical **MeshCore Agent Protocol** for decentralized AI
- Support fully offline/local models during network outages
- Enable multi-agent coordination across the mesh
- Make mesh-native AI accessible to community networks

---

**Project Status**: Early development – actively being built

Contributions, ideas, and other mesh communities welcome!

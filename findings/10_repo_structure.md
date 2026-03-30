# Bittensor Subnet Repo Structure & Code Patterns

## Official Template (opentensor/bittensor-subnet-template)

```
bittensor-subnet-template/
├── neurons/
│   ├── miner.py              # Miner entry point
│   └── validator.py          # Validator entry point
├── template/
│   ├── __init__.py
│   ├── protocol.py           # Synapse definition
│   ├── base/
│   │   ├── miner.py          # Base miner class
│   │   └── validator.py      # Base validator class
│   └── forward.py            # Validator forward logic (optional)
│   └── reward.py             # Scoring/reward functions (optional)
├── scripts/                  # Installation and setup scripts
├── docs/
│   ├── running_on_staging.md
│   ├── running_on_testnet.md
│   └── running_on_mainnet.md
├── min_compute.yml           # Minimum hardware requirements
├── requirements.txt
├── setup.py / pyproject.toml
├── README.md
└── CONTRIBUTING.md
```

---

## Real Subnet Examples

### SN1 (macrocosm-os/prompting)
- Validators use LLM to create persona-based prompts
- Miners respond as AI assistants
- Scored by similarity to reference answers
- **Key pattern**: Stream miner architecture (sync forward() with internal async _forward())
- Important docs: `docs/validator.md`, `docs/SN1_validation.md`, `docs/stream_miner_template.md`

### SN9 (macrocosm-os/pretraining → iota)
- Miners upload models to HuggingFace
- Validators download and evaluate against Falcon dataset
- Continuous benchmark for foundation models
- **Key pattern**: External storage (HuggingFace) for large artifacts

### SN82 (SN-Hermes/hermes-subnet)
- Uses `uv` for dependency management (modern alternative to pip)
- Config pattern: `cp validators/config.example.json config.json`
- Run: `python -m neurons.validator` / `python -m neurons.miner`

### SN15 (blockchain-insights/blockchain-data-subnet)
- Separate repos for: ops (Docker Compose), LLM engine, validator API
- Protocol defines data exchange rules for consistent formats

---

## Standard Code Patterns

### protocol.py — Synapse Definition
```python
import bittensor as bt
from typing import Optional, List

class MySynapse(bt.Synapse):
    # Request fields (validator fills before sending)
    task_id: str = ""
    question: str = ""

    # Response fields (miner fills before returning)
    answer: Optional[str] = None
    score: Optional[float] = None
```

### neurons/miner.py — Entry Point
```python
import argparse
import bittensor as bt
from template.protocol import MySynapse

def forward(synapse: MySynapse) -> MySynapse:
    """Process incoming request and return response."""
    synapse.answer = generate_answer(synapse.question)
    return synapse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--netuid", type=int, required=True)
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)

    config = bt.config(parser)
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(netuid=config.netuid)

    axon = bt.axon(wallet=wallet)
    axon.attach(forward_fn=forward)
    axon.serve(netuid=config.netuid, subtensor=subtensor)
    axon.start()

    bt.logging.info("Miner started")
    while True:
        metagraph.sync(subtensor=subtensor)
        time.sleep(12)

if __name__ == "__main__":
    main()
```

### neurons/validator.py — Entry Point
```python
import argparse
import time
import torch
import bittensor as bt
from template.protocol import MySynapse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--netuid", type=int, required=True)
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)

    config = bt.config(parser)
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(netuid=config.netuid)
    dendrite = bt.dendrite(wallet=wallet)

    scores = torch.zeros(metagraph.n)
    alpha = 0.1  # EMA smoothing factor

    while True:
        metagraph.sync(subtensor=subtensor)

        # Build synapse
        synapse = MySynapse(task_id="001", question="...")

        # Query all miners
        responses = dendrite(
            axons=metagraph.axons,
            synapse=synapse,
            timeout=30
        )

        # Score responses
        for i, response in enumerate(responses):
            new_score = compute_score(response)
            scores[i] = alpha * new_score + (1 - alpha) * scores[i]  # EMA

        # Set weights
        weights = scores / scores.sum()
        subtensor.set_weights(
            wallet=wallet,
            netuid=config.netuid,
            uids=list(range(metagraph.n)),
            weights=weights.tolist()
        )

        time.sleep(12)

if __name__ == "__main__":
    main()
```

---

## Configuration Management

### Priority Order
1. Command-line arguments (highest)
2. Environment variables
3. `~/.bittensor/config.yml` (global)
4. Default values (lowest)

### Typical Arguments
```python
parser.add_argument("--netuid", type=int, help="Subnet network ID")
parser.add_argument("--subtensor.network", type=str, default="finney")
parser.add_argument("--subtensor.chain_endpoint", type=str)
parser.add_argument("--axon.port", type=int, default=8091)
bt.wallet.add_args(parser)     # --wallet.name, --wallet.hotkey
bt.subtensor.add_args(parser)  # --subtensor.network, etc.
```

---

## Dependencies (pyproject.toml)
```toml
[project]
requires-python = ">=3.10"
dependencies = [
    "bittensor>=6.6.0",
    "pydantic>=2.0",
    "fastapi>=0.100.0",
    "httpx>=0.24.0",
    "structlog>=23.0.0",
    "tenacity>=8.2.0",
    "numpy>=1.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0",
    "ruff>=0.1.0",
]
```

### QueryAgent-Specific Dependencies
```
bittensor>=6.6.0    # SDK
duckdb>=0.10.0      # SQL execution engine
pyarrow>=15.0.0     # Parquet handling
pandas>=2.0.0       # Data manipulation
hashlib             # SHA-256 (stdlib)
```

---

## Docker Pattern
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT ["python", "-m", "neurons.miner"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  miner:
    build: .
    environment:
      - BITTENSOR_WALLET_NAME=default
    volumes:
      - ~/.bittensor:/root/.bittensor
    ports:
      - "8091:8091"
```

---

## Testing
```
tests/
├── test_protocol.py      # Synapse serialization/deserialization
├── test_miner.py         # Forward function logic
├── test_validator.py     # Scoring logic
├── test_scoring.py       # Score computation
└── integration/
    └── test_loop.py      # End-to-end miner-validator cycle
```

```bash
pytest tests/ -v
pytest tests/test_scoring.py -v
```

---

## README Structure (Standard)
1. Overview — what the subnet does, incentive mechanism
2. Prerequisites — Python version, hardware
3. Installation — clone, install deps
4. Configuration — wallet setup, env vars
5. Running a Miner — with example commands
6. Running a Validator — with example commands
7. Development — local testnet setup
8. Testing — how to run tests
9. Contributing — PR process
10. Resources — docs links

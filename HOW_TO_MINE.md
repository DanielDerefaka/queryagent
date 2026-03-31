# How to Mine on QueryAgent

A step-by-step guide to running QueryAgent miners, validators, and reproducing the full incentive loop on Bittensor testnet.

---

## Table of Contents

1. [What Is QueryAgent?](#what-is-queryagent)
2. [Architecture Overview](#architecture-overview)
3. [Hardware Requirements](#hardware-requirements)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Wallet Setup](#wallet-setup)
7. [Building a Snapshot](#building-a-snapshot)
8. [Generating Tasks and Ground Truth](#generating-tasks-and-ground-truth)
9. [Running a Miner](#running-a-miner)
   - [Template Miner (Recommended for Testnet)](#template-miner)
   - [LLM Miner (GPT-4o)](#llm-miner)
   - [Hybrid Miner (Template + LLM Fallback)](#hybrid-miner)
10. [Running a Validator](#running-a-validator)
11. [Full Local Deployment (10 Miners + 3 Validators)](#full-local-deployment)
12. [Docker Deployment](#docker-deployment)
13. [Understanding the Scoring System](#understanding-the-scoring-system)
14. [How the Incentive Mechanism Works](#how-the-incentive-mechanism-works)
15. [Verifying the Incentive Loop](#verifying-the-incentive-loop)
16. [Running the Test Suite](#running-the-test-suite)
17. [Monitoring and Logs](#monitoring-and-logs)
18. [Anti-Gaming Protections](#anti-gaming-protections)
19. [Troubleshooting](#troubleshooting)

---

## What Is QueryAgent?

QueryAgent is a Bittensor subnet where miners compete to answer blockchain analytics questions using SQL. Validators verify answers by re-executing the SQL on identical frozen data snapshots and comparing SHA-256 hashes. Correct, fast miners earn TAO emissions through Yuma Consensus.

The flow is simple:

```
Validator asks: "What is the total TAO staked across all subnets?"
      ↓
Miner writes SQL: SELECT SUM(stake) AS total_staked FROM stakes
      ↓
Miner executes SQL on frozen Parquet snapshot → computes SHA-256 hash
      ↓
Validator re-executes the same SQL on its own copy of the snapshot
      ↓
Hash matches ground truth? → Score = 0.75 + speed bonuses
Hash doesn't match?       → Score = 0.0 (hard gate, no partial credit)
```

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────┐
│                    VALIDATOR                          │
│                                                       │
│  1. Sample task from pool (public + hidden)           │
│  2. Build QuerySynapse → broadcast to all miners      │
│  3. Collect responses (SQL + result_hash)              │
│  4. Re-execute each miner's SQL on own DuckDB         │
│  5. Compare hash to ground truth                      │
│  6. Score: 75% correct + 15% efficiency + 10% speed   │
│  7. EMA smooth → set_weights() on-chain               │
└───────────────────────┬───────────────────────────────┘
                        │ QuerySynapse via dendrite/axon
                        ▼
┌───────────────────────────────────────────────────────┐
│                      MINER                            │
│                                                       │
│  1. Receive QuerySynapse on axon                      │
│  2. Load frozen Parquet snapshot into DuckDB           │
│  3. Generate SQL (template / LLM / hybrid)            │
│  4. Execute SQL → compute SHA-256 hash                │
│  5. Return Answer Package (sql, hash, explanation)    │
└───────────────────────────────────────────────────────┘
```

### Wire Format (QuerySynapse)

```
Validator → Miner (request):
  task_id        "QB-001"
  snapshot_id    "bt_snapshot_test_v1"
  question       "What is the total TAO staked across all subnets?"
  constraints    {"k": 10, "netuid_filter": 1}

Miner → Validator (response):
  sql            "SELECT SUM(stake) AS total_staked FROM stakes"
  result_hash    "sha256:a1b2c3d4..."
  result_preview {"columns": ["total_staked"], "rows": [[12345.678]]}
  tables_used    ["stakes"]
  explanation    "Sums all stake values from the stakes table."
```

---

## Hardware Requirements

| Component | Miner | Validator |
|-----------|-------|-----------|
| CPU | 4 cores | 4 cores |
| RAM | 8 GB | 16 GB |
| Storage | 5 GB | 10 GB |
| GPU | Not required | Not required |
| Network | Stable (axon server) | Stable (dendrite queries) |

QueryAgent is CPU-only. No GPU needed. The bottleneck is SQL execution speed on DuckDB, which runs in-memory.

---

## Prerequisites

- Python 3.10+
- pip
- Git
- A Bittensor wallet (coldkey + hotkey)
- TAO for registration fees (testnet TAO is free via faucet)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/queryagent/subnet.git
cd subnet
```

### 2. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e .
```

This installs all required packages:

| Package | Version | Purpose |
|---------|---------|---------|
| bittensor | >= 8.0.0 | Subnet framework (axon, dendrite, metagraph, wallets) |
| duckdb | >= 1.0.0 | In-memory SQL engine for query execution |
| pyarrow | >= 15.0.0 | Parquet file I/O for snapshot loading |
| pandas | >= 2.0.0 | DataFrame operations for snapshot building |
| pydantic | >= 2.0 | Data validation |
| numpy | >= 1.24.0 | Numerical operations |
| torch | >= 2.0.0 | Tensor operations for EMA scoring |
| structlog | >= 23.0.0 | Structured logging |

### 4. Verify installation

```bash
PYTHONPATH=. python3 -c "from queryagent.protocol import QuerySynapse; print('OK')"
```

---

## Wallet Setup

### Create a new wallet (if you don't have one)

```bash
# Create coldkey
btcli wallet new_coldkey --wallet.name miner_wallet

# Create hotkey
btcli wallet new_hotkey --wallet.name miner_wallet --wallet.hotkey default
```

### Get testnet TAO (free faucet)

```bash
btcli wallet faucet --wallet.name miner_wallet --subtensor.network test
```

### Register on the subnet

```bash
# Replace <NETUID> with the QueryAgent subnet ID
btcli subnet register \
    --wallet.name miner_wallet \
    --wallet.hotkey default \
    --netuid <NETUID> \
    --subtensor.network test
```

---

## Building a Snapshot

Snapshots are frozen copies of Bittensor chain data stored as Parquet files. Both miners and validators use the same snapshot so that SQL execution produces identical results.

### Build from testnet

```bash
python scripts/build_snapshot.py \
    --network test \
    --output benchmark/snapshots/bt_snapshot_test_v1
```

### Build from mainnet (Finney)

```bash
python scripts/build_snapshot.py \
    --network finney \
    --output benchmark/snapshots/bt_snapshot_2026_03_v1 \
    --max-subnets 50
```

### What gets built

```
benchmark/snapshots/bt_snapshot_test_v1/
├── schema.json          # Table definitions (columns, types)
├── metadata.json        # Block number, build time, checksums
└── tables/
    ├── subnets.parquet    # Subnet hyperparameters
    ├── validators.parquet # Validator neurons (dividends > 0)
    ├── miners.parquet     # Miner neurons
    ├── stakes.parquet     # Neurons with non-zero stake
    ├── emissions.parquet  # Neurons with non-zero emission
    └── metagraph.parquet  # All neurons combined
```

### Snapshot tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `subnets` | Subnet hyperparameters | netuid, tempo, max_n, immunity_period |
| `validators` | Neurons with dividends > 0 or validator_trust > 0 | netuid, uid, hotkey, stake, dividends, validator_trust |
| `miners` | Non-validator neurons | netuid, uid, hotkey, stake, incentive, active |
| `stakes` | Neurons with stake > 0 | netuid, uid, hotkey, stake |
| `emissions` | Neurons with emission > 0 | netuid, uid, hotkey, emission, incentive, dividends |
| `metagraph` | All neurons (validators + miners) | netuid, uid, hotkey, stake, trust, consensus, incentive, emission |

A pre-built testnet snapshot is included at `benchmark/snapshots/bt_snapshot_test_v1/`.

---

## Generating Tasks and Ground Truth

Tasks are the questions validators ask miners. Ground truth hashes are pre-computed by running reference SQL on the snapshot.

```bash
python scripts/generate_tasks.py --snapshot bt_snapshot_test_v1
```

### What gets generated

```
benchmark/
├── tasks/
│   ├── public_tasks.json    # 16 tasks visible to miners
│   └── hidden_tasks.json    # 4 tasks only validators know
└── ground_truth/
    ├── QB-001.json          # Reference SQL + expected hash
    ├── QB-002.json
    └── ... (one per task)
```

### Task difficulty tiers

| Tier | Share | Budget | Example |
|------|-------|--------|---------|
| Easy (30%) | Simple aggregates | 5s | "Total TAO staked?" |
| Medium (50%) | GROUP BY, JOINs | 8s | "Top 10 validators by stake" |
| Hard (20%) | Window functions, CTEs | 15s | "Gini coefficient of stake distribution" |

### Example ground truth file (QB-001.json)

```json
{
  "task_id": "QB-001",
  "snapshot_id": "bt_snapshot_test_v1",
  "reference_sql": "SELECT SUM(stake) AS total_staked FROM stakes",
  "ground_truth_hash": "sha256:a1b2c3d4e5f6...",
  "tier": "easy",
  "budget_ms": 5000
}
```

Miners never see the reference SQL or ground truth hash. They must independently arrive at the correct answer.

---

## Running a Miner

QueryAgent ships with three miner implementations. Pick the one that fits your setup.

### Template Miner

The template miner uses regex pattern matching to map natural language questions to SQL. It's fast, free (no API keys), and deterministic. Good for testnet.

```bash
python -m neurons.miner \
    --netuid <NETUID> \
    --wallet.name miner_wallet \
    --wallet.hotkey default \
    --subtensor.network test \
    --axon.port 8091
```

**How it works:**

The miner has 14 regex patterns that match common questions:

```python
# "total staked" or "total stake" → simple SUM
{"pattern": r"total.*staked|total.*stake",
 "sql": "SELECT SUM(stake) AS total_staked FROM stakes"}

# "top 10 validators by stake" → ORDER BY with LIMIT
{"pattern": r"top (\d+).*validators.*stake",
 "sql": "SELECT netuid, uid, hotkey, stake FROM validators ORDER BY stake DESC LIMIT {k}"}
```

When a validator sends a question, the miner:
1. Tries each regex pattern against the question
2. If a pattern matches, fills in parameters (k, netuid) from constraints
3. Executes the SQL on the frozen DuckDB snapshot
4. Computes SHA-256 hash of the result
5. Returns the Answer Package

**Expected performance:** ~12/20 tasks correct. Templates only cover questions they were written for.

### LLM Miner

The LLM miner sends the question + database schema to GPT-4o, which writes the SQL.

**Requires:** `OPENAI_API_KEY` environment variable.

```bash
export OPENAI_API_KEY="sk-..."

python -m neurons.miner_llm \
    --netuid <NETUID> \
    --wallet.name miner_wallet \
    --wallet.hotkey default \
    --subtensor.network test \
    --axon.port 8091
```

**How it works:**

1. Builds a schema prompt from `schema.json` (table names, column names, types)
2. Includes few-shot examples of correct SQL
3. Sends to GPT-4o with the question + constraints
4. Extracts SQL from the LLM response
5. Executes on DuckDB and computes hash

**Cost:** ~$0.01-0.03 per query (GPT-4o pricing).

### Hybrid Miner

The recommended production strategy. Tries the template miner first (instant, free), falls back to the LLM only for questions templates can't match.

```bash
export OPENAI_API_KEY="sk-..."

python -m neurons.miner_llm \
    --netuid <NETUID> \
    --wallet.name miner_wallet \
    --wallet.hotkey default \
    --subtensor.network test \
    --axon.port 8091
```

The `miner_llm.py` already uses the hybrid strategy by default via `generate_sql_hybrid()`.

---

## Running a Validator

The validator drives the entire incentive loop: it samples tasks, queries miners, re-executes SQL, scores responses, and submits weights on-chain.

```bash
python -m neurons.validator \
    --netuid <NETUID> \
    --wallet.name validator_wallet \
    --wallet.hotkey default \
    --subtensor.network test
```

### What the validator does every round (~2 minutes)

```
1. SAMPLE TASK
   ├── Pick difficulty tier: 30% easy / 50% medium / 20% hard
   ├── 20% chance of selecting a hidden task
   └── Inject random parameters (k, netuid_filter, time_window)

2. QUERY MINERS
   ├── Build QuerySynapse with task_id, snapshot_id, question, constraints
   ├── Broadcast to ALL miners via dendrite
   └── Wait up to 30s for responses

3. RE-EXECUTE & VERIFY
   ├── For each miner response:
   │   ├── Re-execute the miner's SQL on validator's own DuckDB
   │   ├── Time the execution
   │   ├── Compute SHA-256 hash of the result
   │   └── Compare to ground truth hash
   └── Score each miner

4. UPDATE SCORES
   ├── Apply EMA smoothing: EMA[uid] = 0.1 × new + 0.9 × old
   └── Normalize to weights that sum to 1.0

5. SET WEIGHTS (every ~40 minutes / 200 blocks)
   └── Call subtensor.set_weights() on-chain
```

### Validator timing

| Parameter | Value | Description |
|-----------|-------|-------------|
| Validation interval | 120s (2 min) | Time between rounds |
| Metagraph sync | 300s (5 min) | Re-sync neuron list |
| Weights rate limit | 200 blocks (~40 min) | Min blocks between set_weights() |
| Miner timeout | 30s | Max time to wait for a response |

---

## Full Local Deployment

To test the complete subnet locally with multiple miners and validators:

```bash
bash scripts/run_local.sh
```

This script:
- Starts **10 miners** with different skill levels:
  - Miners 1-3: **strong** (handle easy + medium + hard tasks)
  - Miners 4-7: **medium** (handle easy + medium tasks)
  - Miners 8-10: **weak** (handle easy tasks only)
- Starts **3 validators** that independently score miners
- All on a local subtensor chain at `ws://127.0.0.1:9944`

### Monitor the deployment

```bash
# Miner logs
tail -f /tmp/miner_logs/miner_1.log

# Validator logs
tail -f /tmp/validator_logs/validator_1.log
```

### What you'll see in validator logs

```
Round: task=QB-010 tier=medium hidden=False question=Top 10 validators by stake...
Received 10 responses in 2340ms
  UID 0: score=0.9512 hash_match=True
  UID 1: score=0.9488 hash_match=True
  UID 2: score=0.9501 hash_match=True
  UID 3: score=0.9456 hash_match=True
  UID 4: score=0.0000 hash_match=False    ← weak miner, can't do medium tasks
  ...
Scored: 7/10 miners correct, max_score=0.951
Setting weights at block 1234 (7 non-zero weights)
```

---

## Docker Deployment

### Build the image

```bash
docker build -t queryagent .
```

### Run with docker-compose

Create a `.env` file:

```bash
NETUID=<your_subnet_id>
SUBTENSOR_NETWORK=test
BITTENSOR_WALLET_NAME=miner_wallet
BITTENSOR_WALLET_HOTKEY=default
```

Then:

```bash
# Run miner
docker-compose up miner

# Run validator
docker-compose up validator

# Run both
docker-compose up
```

### Manual Docker run

```bash
# Miner
docker run -d \
    -v ~/.bittensor:/root/.bittensor \
    -v $(pwd)/benchmark:/app/benchmark \
    -p 8091:8091 \
    queryagent \
    --netuid <NETUID> \
    --wallet.name miner_wallet \
    --wallet.hotkey default \
    --subtensor.network test

# Validator
docker run -d \
    -v ~/.bittensor:/root/.bittensor \
    -v $(pwd)/benchmark:/app/benchmark \
    queryagent \
    python -m neurons.validator \
    --netuid <NETUID> \
    --wallet.name validator_wallet \
    --wallet.hotkey default \
    --subtensor.network test
```

---

## Understanding the Scoring System

### The Formula

```
IF result_hash != ground_truth_hash:
    score = 0.0                          ← HARD GATE: wrong answer = zero

IF result_hash == ground_truth_hash:
    score = 0.75                         ← 75% for correctness
           + 0.15 × efficiency           ← 15% for SQL execution speed
           + 0.10 × latency              ← 10% for end-to-end response time

Where:
    efficiency = max(0, 1 - exec_ms / budget_ms)
    latency    = max(0, 1 - response_ms / 30000ms)
```

### Scoring examples

| Scenario | Hash Match | Exec Time | Response Time | Score |
|----------|-----------|-----------|---------------|-------|
| Perfect answer, instant | Yes | 10ms / 5000ms | 100ms / 30000ms | 0.75 + 0.147 + 0.097 = **0.994** |
| Correct, moderate speed | Yes | 2000ms / 5000ms | 10000ms / 30000ms | 0.75 + 0.090 + 0.067 = **0.907** |
| Correct but slow | Yes | 4500ms / 5000ms | 28000ms / 30000ms | 0.75 + 0.015 + 0.007 = **0.772** |
| Wrong answer | No | any | any | **0.000** |
| No response | - | - | - | **0.000** |

### EMA Smoothing

Scores are smoothed across rounds using Exponential Moving Average:

```
EMA[uid] = 0.1 × new_score + 0.9 × EMA[uid]
```

- `alpha = 0.1` means it takes ~10 rounds for a new miner to build up a full score
- Prevents single-round gaming (one lucky answer doesn't dominate)
- Penalizes inconsistency (a miner that answers 50% of tasks correctly will have ~half the EMA of a 100% miner)

### Weight Normalization

```
weight[uid] = EMA[uid] / sum(all EMA scores)
```

These normalized weights are submitted on-chain via `set_weights()`. Yuma Consensus uses them to distribute TAO emissions proportionally.

---

## How the Incentive Mechanism Works

### Why correct miners earn more

1. **Hard gate on correctness (75%)**: A wrong hash = 0.0 score. No partial credit. This is the dominant factor. A miner that gets every answer right will always outperform one that doesn't, regardless of speed.

2. **Speed bonuses (25%)**: Among correct miners, the faster ones earn slightly more. This creates competition to write efficient SQL.

3. **EMA smoothing**: Consistent performers accumulate higher EMA scores over time. A miner that cheats on one round and fails the next will have a lower average than a consistently correct miner.

4. **Yuma Consensus**: Multiple validators independently score miners. A miner can't fool one validator without fooling all of them, because they all re-execute the SQL on identical data.

### Why cheating doesn't work

| Attack | Defense |
|--------|---------|
| Memorize answers | Hidden tasks (20%) are never published. Parameter injection randomizes k, netuid, time_window each round. |
| Cache hashes | Snapshots rotate monthly. Old hashes become invalid. |
| SQL injection | DuckDB sandboxing blocks CREATE, DROP, INSERT, UPDATE, DELETE, ALTER, COPY, EXPORT. |
| Copy other miners | Each miner runs independently on its own axon. There's no way to see other miners' responses before submitting. |
| Bribe validators | Hash comparison is deterministic. A validator that submits dishonest scores will diverge from consensus and lose stake. |
| Submit random hashes | SHA-256 collision resistance. Probability of a random hash matching = 1/2^256. |

### TAO emission flow (dTAO)

```
Subnet emissions (set by root network weight)
    ├── 41% → Miners      (proportional to set_weights scores)
    ├── 41% → Validators   (proportional to stake)
    └── 18% → Subnet owner
```

---

## Verifying the Incentive Loop

### Step 1: Run the full test suite

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

This runs 124+ tests across 11 test files:

| Test File | Tests | What It Proves |
|-----------|-------|----------------|
| `test_protocol.py` | 3 | Synapse serialization works correctly |
| `test_hashing.py` | 8 | SHA-256 hashing is deterministic across runs |
| `test_scoring.py` | 12 | 75/15/10 formula computes correct scores, EMA works |
| `test_snapshot.py` | 4 | Parquet loading and SQL sandboxing work |
| `test_tasks.py` | 15 | Task sampling follows 30/50/20 distribution |
| `test_determinism.py` | 11 | Same query 100x = same hash. Concurrent threads = same hash. |
| `test_adversarial.py` | 60 | SQL injection blocked. Edge cases handled. |
| `test_wire.py` | 4 | Real axon-to-dendrite communication works |
| `test_e2e.py` | 5 | Full miner-to-validator loop produces correct scores |
| `test_llm_miner.py` | 2 | LLM and hybrid strategies generate valid SQL |

### Step 2: Verify hash determinism

The entire scoring system depends on deterministic hashing. Prove it:

```python
from queryagent.snapshot import load_snapshot
from queryagent.hashing import hash_result

conn = load_snapshot("bt_snapshot_test_v1")

# Run the same query 100 times
hashes = set()
for _ in range(100):
    h = hash_result(conn, "SELECT SUM(stake) AS total_staked FROM stakes")
    hashes.add(h)

print(f"Unique hashes: {len(hashes)}")  # Must be 1
assert len(hashes) == 1, "HASH DETERMINISM BROKEN"
```

### Step 3: Verify scoring formula

```python
from queryagent.scoring import compute_score

# Correct answer, fast execution
score = compute_score(hash_matches=True, exec_ms=100, budget_ms=5000, response_ms=500, latency_ms=30000)
print(f"Fast correct: {score:.4f}")  # ~0.99

# Correct answer, slow execution
score = compute_score(hash_matches=True, exec_ms=4500, budget_ms=5000, response_ms=28000, latency_ms=30000)
print(f"Slow correct: {score:.4f}")  # ~0.77

# Wrong answer
score = compute_score(hash_matches=False, exec_ms=100, budget_ms=5000, response_ms=500, latency_ms=30000)
print(f"Wrong: {score:.4f}")  # 0.0
```

### Step 4: Verify EMA convergence

```python
import torch
from queryagent.scoring import update_ema

scores = torch.zeros(3)

# Miner 0: always correct (0.95)
# Miner 1: sometimes correct (alternating 0.95 and 0.0)
# Miner 2: always wrong (0.0)
for round_num in range(20):
    new = [0.95, 0.95 if round_num % 2 == 0 else 0.0, 0.0]
    scores = update_ema(scores, new)
    print(f"Round {round_num:2d}: {scores.tolist()}")

# After 20 rounds:
# Miner 0 EMA ≈ 0.83 (consistently high)
# Miner 1 EMA ≈ 0.41 (half the time correct)
# Miner 2 EMA = 0.00 (never correct)
```

This proves that the incentive mechanism rewards consistent correctness.

### Step 5: Run an end-to-end validation round locally

```python
from queryagent.snapshot import load_snapshot
from queryagent.hashing import hash_result, hash_from_rows
from queryagent.snapshot import execute_sql_safe
from queryagent.scoring import compute_score
from queryagent.tasks import TaskPool

# Load everything
conn = load_snapshot("bt_snapshot_test_v1")
pool = TaskPool()
pool.load()

# Simulate: validator samples a task
task = pool.sample_task()
gt = pool.get_ground_truth(task.task_id)

print(f"Task: {task.task_id} ({task.tier})")
print(f"Question: {task.question}")
print(f"Ground truth hash: {gt['ground_truth_hash'][:40]}...")

# Simulate: miner generates SQL (use reference SQL for demo)
miner_sql = gt["reference_sql"]
miner_hash = hash_result(conn, miner_sql)

print(f"Miner hash: {miner_hash[:40]}...")
print(f"Match: {miner_hash == gt['ground_truth_hash']}")

# Simulate: validator re-executes
columns, rows, exec_ms = execute_sql_safe(conn, miner_sql)
validator_hash = hash_from_rows(columns, rows)

score = compute_score(
    hash_matches=(validator_hash == gt["ground_truth_hash"]),
    exec_ms=exec_ms,
    budget_ms=task.budget_ms,
    response_ms=200,
    latency_ms=task.latency_ms,
)
print(f"Score: {score:.4f}")
```

---

## Running the Test Suite

### Run all tests

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

### Run specific test categories

```bash
# Hash determinism (proves verification works)
PYTHONPATH=. python3 -m pytest tests/test_determinism.py -v

# Scoring formula (proves incentives are correct)
PYTHONPATH=. python3 -m pytest tests/test_scoring.py -v

# Anti-gaming (proves SQL injection is blocked)
PYTHONPATH=. python3 -m pytest tests/test_adversarial.py -v

# Full end-to-end loop
PYTHONPATH=. python3 -m pytest tests/test_e2e.py -v

# Real axon↔dendrite wire test
PYTHONPATH=. python3 -m pytest tests/test_wire.py -v
```

### Expected output

```
tests/test_adversarial.py .......... (60 passed)
tests/test_determinism.py .......... (11 passed)
tests/test_e2e.py .....            (5 passed)
tests/test_hashing.py ........     (8 passed)
tests/test_protocol.py ...         (3 passed)
tests/test_scoring.py ............  (12 passed)
tests/test_snapshot.py ....        (4 passed)
tests/test_tasks.py ...............  (15 passed)
tests/test_wire.py ....            (4 passed)

======================== 124 passed ========================
```

---

## Monitoring and Logs

### Miner logs

```
2026-03-31 12:00:01 | INFO | Wallet: miner_wallet/default
2026-03-31 12:00:02 | INFO | Metagraph: 15 neurons on subnet 3
2026-03-31 12:00:02 | INFO | Miner axon started on port 8091
2026-03-31 12:00:14 | INFO | Received task QB-010: Top 10 validators by stake...
2026-03-31 12:00:14 | INFO | Task QB-010 completed in 12ms — hash=sha256:a1b2c3d4...
2026-03-31 12:00:26 | INFO | UID=5 | stake=0.0000 | incentive=0.004521
```

### Validator logs

```
2026-03-31 12:00:01 | INFO | Task pool: 16 public, 4 hidden
2026-03-31 12:00:01 | INFO | Loading snapshot: bt_snapshot_test_v1
2026-03-31 12:00:02 | INFO | Loaded stakes: 245 rows
2026-03-31 12:00:02 | INFO | Validator started. Entering main loop...
2026-03-31 12:02:01 | INFO | Round: task=QB-012 tier=medium hidden=False question=Top 10 miners...
2026-03-31 12:02:04 | INFO | Received 10 responses in 2850ms
2026-03-31 12:02:04 | INFO |   UID 0: score=0.9512 hash_match=True
2026-03-31 12:02:04 | INFO |   UID 1: score=0.9488 hash_match=True
2026-03-31 12:02:04 | INFO |   UID 7: score=0.0000 hash_match=False
2026-03-31 12:02:04 | INFO | Scored: 7/10 miners correct, max_score=0.951
2026-03-31 12:02:04 | INFO | Training data: 7 positive, 3 negative, 0 skipped
```

### Training data output

Validators automatically save scored responses as training data for fine-tuning:

```
benchmark/training_data/training_2026-03-31.jsonl
```

Each line is a labeled example:

```json
{
  "task_id": "QB-010",
  "question": "Top 10 validators by stake across all subnets",
  "sql": "SELECT netuid, uid, hotkey, stake FROM validators ORDER BY stake DESC LIMIT 10",
  "score": 0.9512,
  "label": "positive",
  "miner_uid": 0,
  "exec_ms": 8.42,
  "tier": "medium"
}
```

---

## Anti-Gaming Protections

QueryAgent implements 7 layers of defense against gaming:

| Layer | Protection | How |
|-------|-----------|-----|
| 1 | Hidden tasks | 20% of tasks are never published. Miners can't memorize all answers. |
| 2 | Parameter injection | k, netuid_filter, time_window are randomized each round. Same question, different parameters = different answer. |
| 3 | Snapshot rotation | Snapshots rotate monthly. Cached hashes expire. |
| 4 | DuckDB sandboxing | Only SELECT allowed. CREATE, DROP, INSERT, UPDATE, DELETE, ALTER, COPY, EXPORT are blocked. |
| 5 | Hard gate scoring | Wrong hash = 0.0. No partial credit for "close" answers. |
| 6 | Deregistration | Yuma Consensus removes consistently poor performers from the network. |
| 7 | Deterministic hashing | SHA-256 with canonical form (sorted rows, fixed float precision, NULL sentinel). |

---

## Troubleshooting

### "Snapshot not found"

```bash
# Rebuild the snapshot
python scripts/build_snapshot.py --network test --output benchmark/snapshots/bt_snapshot_test_v1
```

### "No ground truth for task"

```bash
# Regenerate tasks and ground truth
python scripts/generate_tasks.py --snapshot bt_snapshot_test_v1
```

### "Miner hotkey not found in metagraph"

Your hotkey isn't registered on the subnet. Register first:

```bash
btcli subnet register --wallet.name miner_wallet --wallet.hotkey default --netuid <NETUID> --subtensor.network test
```

### "Failed to set weights"

Validators need sufficient stake to set weights. Check your stake:

```bash
btcli wallet overview --wallet.name validator_wallet --subtensor.network test
```

### Hash mismatch between miner and validator

This means the miner's SQL produces different results than the ground truth. Common causes:
- Wrong table name (e.g., using `metagraph` instead of `validators`)
- Missing WHERE clause (e.g., not filtering `active = true`)
- Different column names in SELECT
- Missing ORDER BY or LIMIT

### Import errors

Make sure you're running from the project root with PYTHONPATH set:

```bash
cd /path/to/subnet
PYTHONPATH=. python -m neurons.miner --netuid <NETUID> ...
```

---

## Project Structure Reference

```
queryagent/
├── protocol.py     # QuerySynapse wire format (bt.Synapse subclass)
├── config.py       # All tunable parameters (weights, timeouts, paths)
├── hashing.py      # Deterministic SHA-256 (canonical form, NULL sentinel)
├── scoring.py      # 75/15/10 formula + EMA smoothing + normalization
├── snapshot.py      # Parquet → DuckDB loader (read-only, sandboxed)
├── tasks.py        # Task pool, ground truth, weighted sampling
└── training.py     # Training data pipeline (positive/negative labeling)

neurons/
├── miner.py        # Template-based miner (regex → SQL)
├── miner_llm.py    # LLM miner (GPT-4o) + hybrid strategy
├── miner_local.py  # Local chain miner (skill tiers)
├── validator.py    # Reference validator (testnet)
└── validator_local.py  # Local chain validator

scripts/
├── build_snapshot.py     # Chain data → Parquet snapshot
├── generate_tasks.py     # Tasks + ground truth hashes
├── run_local.sh          # Full local deployment (10 miners + 3 validators)
├── restart_miners.sh     # Restart miner processes
└── restart_validators.sh # Restart validator processes

benchmark/
├── tasks/
│   ├── public_tasks.json    # 16 public tasks
│   └── hidden_tasks.json    # 4 hidden tasks
├── ground_truth/            # Pre-computed SHA-256 hashes
├── snapshots/               # Frozen Parquet data bundles
└── training_data/           # Validator-scored miner responses (JSONL)

tests/                       # 124+ tests across 11 files
```

---

## Quick Start Checklist

```
[ ] 1. Clone repo + install dependencies
[ ] 2. Create Bittensor wallet (coldkey + hotkey)
[ ] 3. Get testnet TAO from faucet
[ ] 4. Register on the subnet
[ ] 5. Verify snapshot exists (or build one)
[ ] 6. Generate tasks and ground truth
[ ] 7. Start miner: python -m neurons.miner --netuid <NETUID> --wallet.name <NAME> --wallet.hotkey default --subtensor.network test
[ ] 8. (Optional) Start validator: python -m neurons.validator --netuid <NETUID> ...
[ ] 9. Monitor logs for scoring results
[ ] 10. Run tests: PYTHONPATH=. pytest tests/ -v
```

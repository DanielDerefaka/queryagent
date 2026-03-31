# Validator Guide

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         validator_local.py main loop                     │
│                                                                          │
│   1. Connect to substrate (local chain or testnet)                       │
│   2. Load task pool (16 public + 4 hidden tasks)                         │
│   3. Load DuckDB snapshot (Parquet → in-memory)                          │
│   4. Query neuron count + hotkeys via substrate                          │
│                                                                          │
│   ┌────────────────── EVERY ~2 MINUTES ───────────────────┐             │
│   │                                                        │             │
│   │  a. Sample task (weighted: 30% easy, 50% med, 20% hard)│             │
│   │  b. Look up ground truth hash                          │             │
│   │  c. Build QuerySynapse                                 │             │
│   │  d. Send to all miners via bt.dendrite                 │             │
│   │  e. For each response:                                 │             │
│   │     - Re-execute miner's SQL on validator's DuckDB     │             │
│   │     - Hash the result                                  │             │
│   │     - Compare to ground truth                          │             │
│   │     - Compute score (0.0 or 0.75+)                     │             │
│   │  f. Update EMA scores                                  │             │
│   │  g. Save training data (scored responses → JSONL)      │             │
│   │                                                        │             │
│   └────────────────────────────────────────────────────────┘             │
│                                                                          │
│   ┌────────────── EVERY 200 BLOCKS (~40 minutes) ─────────┐              │
│   │                                                        │              │
│   │  h. Normalize EMA → weights                           │              │
│   │  i. Submit set_weights() extrinsic on-chain           │              │
│   │                                                        │              │
│   └────────────────────────────────────────────────────────┘              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
python -m neurons.validator_local \
  --netuid 3 \
  --wallet.name validator_1 \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9944
```

## Scoring Pipeline

Each validation round scores all miners independently:

### Step 1: Task Sampling

Tasks are sampled with weighted probability:
- **30% easy** — simple aggregations (budget: 5s)
- **50% medium** — joins, grouping, ranking (budget: 8s)
- **20% hard** — CTEs, window functions, multi-table (budget: 15s)

20% of all sampled tasks come from the **hidden pool** (4 tasks that miners have never seen). This prevents hash memorization.

### Step 2: Query Miners

The validator builds a `QuerySynapse` with the task details and sends it to all registered miners via `bt.dendrite`. Timeout: 30 seconds.

### Step 3: Verify Responses

For each miner response:

1. **Null check** — if no response or missing SQL/hash → score = 0
2. **Re-execution** — run the miner's SQL on the validator's own DuckDB snapshot
3. **Hash comparison** — compare the re-execution hash to the pre-computed ground truth
4. **Score computation:**

```
IF hash mismatch → 0.0
IF hash matches  → 0.75 + 0.15 × efficiency + 0.10 × latency

efficiency = max(0, 1 - exec_ms / budget_ms)
latency    = max(0, 1 - response_ms / 30000)
```

### Step 4: EMA Update

Scores are smoothed via Exponential Moving Average:

```
EMA[uid] = 0.1 × new_score + 0.9 × EMA[uid]
```

This means ~10 correct rounds to go from 0 to near full score, and gradual decay for miners that stop responding.

### Step 5: Set Weights

Every 20 blocks (~4 minutes), the validator normalizes EMA scores to weights and submits on-chain:

```
weight[uid] = EMA[uid] / sum(all EMA scores)
```

The `set_weights` call uses a direct substrate extrinsic (bypasses `bt.subtensor.set_weights()` which checks for CommitRevealWeights, unavailable on local chains).

Weights are encoded as u16 (0-65535 range) before submission.

## Verification Checks

| Check | Description | Result |
|-------|-------------|--------|
| Response received | Miner returned SQL + hash within timeout | Required |
| SQL re-execution | Miner's SQL runs without error on validator DuckDB | Required |
| Hash match | Re-execution hash equals ground truth hash | Score > 0 |
| Efficiency | SQL executes within budget_ms | Bonus (0-15%) |
| Latency | Response arrives within latency_ms | Bonus (0-10%) |

## Training Data Pipeline

After each round, scored responses are saved as labeled training data:

```json
{
  "task_id": "QB-006",
  "question": "What is the average stake per validator?",
  "sql": "SELECT AVG(stake) AS avg_stake FROM validators WHERE stake > 0",
  "result_hash": "sha256:be96fcd326e31...",
  "ground_truth_hash": "sha256:be96fcd326e31...",
  "score": 0.9983,
  "label": "positive",
  "miner_uid": 3,
  "tier": "easy"
}
```

Quality gate:
- Score > 0.80 → `"positive"` (correct SQL, good answer)
- Score < 0.50 → `"negative"` (wrong SQL, bad answer)
- Between → skipped

Data stored in `benchmark/training_data/training_YYYY-MM-DD.jsonl`.

## Expected Log Output

```
=== Validation Round ===
  Task: QB-032 (hard)
  Question: For each subnet, rank validators by emission efficiency and show top 3
  Ground truth: sha256:8631152162157...
  Querying 13 neurons

  UID 3: CORRECT | score=0.9983 | exec=5.1ms | hash=sha256:8631152162157...
  UID 4: CORRECT | score=0.9983 | exec=2.8ms | hash=sha256:8631152162157...
  UID 5: CORRECT | score=0.9983 | exec=3.3ms | hash=sha256:8631152162157...
  UID 6: No response (status=200)    ← medium miner skips hard task
  UID 10: No response (status=200)   ← weak miner skips hard task

EMA scores: [0.0, 0.0, 0.0, 0.981, 0.981, 0.981, 0.463, 0.463, 0.463, 0.463, 0.165, 0.165, 0.165]

>>> SET_WEIGHTS at block 5678 <<<
  Weights set successfully (10 non-zero)
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `WEIGHTS_RATE_LIMIT_BLOCKS` | 200 | Min blocks between set_weights calls (~40 min) |
| `VALIDATION_INTERVAL_S` | 120 | Seconds between validation rounds |
| `DEFAULT_TIMEOUT_S` | 30 | Dendrite query timeout |
| `EMA_ALPHA` | 0.1 | Smoothing factor |
| `HIDDEN_RATIO` | 0.20 | Fraction of hidden tasks sampled |

## Hardware

| Component | Requirement |
|-----------|-------------|
| CPU | 2+ cores |
| RAM | 4 GB |
| Storage | 2 GB |
| GPU | Not required |

# QueryAgent

**Verified on-chain analytics via competitive SQL benchmarking on Bittensor.**

Miners compete to answer blockchain data questions using SQL. Validators re-execute every query on frozen Parquet snapshots and verify results using deterministic SHA-256 hashing. No trust required — the math proves the answer is correct.

## How It Works

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           QueryAgent FLOW                                  │
│                                                                            │
│   VALIDATOR                    BLOCKCHAIN                    MINER         │
│     │                                                          │           │
│     │  1. Sample task from pool                                │           │
│     │     (easy/medium/hard + hidden)                          │           │
│     │                                                          │           │
│     ├──▶ 2. QuerySynapse ──────────────────────────────────▶  │           │
│     │       (task_id, question, snapshot_id)                   │           │
│     │                                                          │           │
│     │                                              3. Generate SQL         │
│     │                                              4. Execute on DuckDB    │
│     │                                              5. SHA-256 hash result  │
│     │                                                          │           │
│     │  ◀──────────────────────── 6. Response ─────────────────┤           │
│     │       (sql, result_hash, tables_used, explanation)       │           │
│     │                                                          │           │
│     │  7. Re-execute miner's SQL                               │           │
│     │  8. Compare hash to ground truth                         │           │
│     │  9. Score: 75% correct + 15% efficiency + 10% latency   │           │
│     │ 10. EMA smoothing (α=0.1)                               │           │
│     │                                                          │           │
│     ├──▶ 11. set_weights() ────▶ Yuma Consensus               │           │
│     │                            (emissions allocated)         │           │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/DanielDerefaka/queryagent.git
cd queryagent
pip install -e .
```

---

## For Miners

See [docs/Miner.md](docs/Miner.md) for full miner documentation.

### Quick Run

```bash
python -m neurons.miner_local \
  --netuid 3 \
  --wallet.name miner_1 \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9944 \
  --axon.port 8091 \
  --skill strong
```

**Skill levels:**
- `strong` — answers all tasks (easy + medium + hard)
- `medium` — answers easy + medium, skips hard
- `weak` — answers easy only

Miners receive a `QuerySynapse` containing a `task_id`, `question`, and `snapshot_id`. They generate SQL, execute it on a DuckDB snapshot, SHA-256 hash the result, and return the package. If the hash matches the validator's ground truth — the miner scores.

---

## For Validators

See [docs/Validator.md](docs/Validator.md) for full validator documentation.

### Quick Run

```bash
python -m neurons.validator_local \
  --netuid 3 \
  --wallet.name validator_1 \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9944
```

Validators sample tasks from the pool (30% easy, 50% medium, 20% hard), send them to all miners via `bt.dendrite`, re-execute the returned SQL on their own DuckDB snapshot, and compare the hash to pre-computed ground truth. Scores are EMA-smoothed and submitted on-chain via `set_weights()`.

---

## Scoring

See [docs/Scoring.md](docs/Scoring.md) for the full mechanism design.

```
IF hash mismatch → score = 0.0  (no partial credit)
IF hash matches  → score = 0.75 + 0.15 × efficiency + 0.10 × latency

efficiency = max(0, 1 - exec_ms / budget_ms)
latency    = max(0, 1 - response_ms / latency_ms)

EMA[uid] = 0.1 × new_score + 0.9 × EMA[uid]
weight[uid] = EMA[uid] / Σ(EMA)
```

| Component | Weight | Description |
|-----------|--------|-------------|
| Correctness | 75% | Binary hash match — ground truth or zero |
| Efficiency | 15% | SQL execution speed on validator's DuckDB |
| Latency | 10% | End-to-end miner response time |

---

## Task Pool

20 benchmark tasks across 3 difficulty tiers:

| Tier | Count | Budget | Example |
|------|-------|--------|---------|
| Easy (30%) | 6 tasks | 5s | `SELECT SUM(stake) AS total_staked FROM stakes` |
| Medium (50%) | 10 tasks | 8s | `SELECT netuid, SUM(emission) FROM emissions GROUP BY netuid ORDER BY ... LIMIT 1` |
| Hard (20%) | 4 tasks | 15s | CTEs, window functions, Gini coefficient, multi-table joins |

**Hidden tasks** (20% of rounds) are never published — miners can't pre-compute answers. Parameter injection randomizes constraints each round.

---

## Anti-Gaming

| Defense | Attack | How It Works |
|---------|--------|-------------|
| Hidden tasks | Hash lookup tables | 20% of tasks are unpublished — can't pre-compute |
| Parameter injection | Memorized answers | Random constraints each round invalidate cached hashes |
| Snapshot rotation | Stale strategies | Monthly snapshot refresh forces adaptation |
| DuckDB sandboxing | SQL injection | Read-only, no filesystem, keyword blocklist |
| Yuma Consensus | Fake validators | Outlier validators get clipped by honest majority |
| Deregistration | Sybil attacks | Low-performing neurons lose their slot |

---

## Project Structure

```
queryagent/
├── queryagent/               # Core SDK module
│   ├── protocol.py           #   QuerySynapse wire format
│   ├── config.py             #   All tunable parameters
│   ├── hashing.py            #   Deterministic SHA-256 hashing
│   ├── scoring.py            #   Score + EMA + weight normalization
│   ├── snapshot.py           #   Parquet → DuckDB loader
│   ├── tasks.py              #   Task pool manager
│   └── training.py           #   Training data pipeline
├── neurons/
│   ├── miner.py              #   Reference miner (testnet)
│   ├── miner_local.py        #   Local chain miner (--skill tiers)
│   ├── miner_llm.py          #   LLM-based miner (GPT-4o)
│   ├── validator.py          #   Reference validator (testnet)
│   └── validator_local.py    #   Local chain validator
├── backend/                  #   FastAPI REST API
├── benchmark/
│   ├── snapshots/            #   Frozen Parquet datasets
│   ├── tasks/                #   Public + hidden task definitions
│   └── ground_truth/         #   Reference SQL + SHA-256 hashes
├── scripts/
│   ├── run_local.sh          #   Full deploy (10 miners + 3 validators)
│   ├── restart_miners.sh     #   Restart miners with skill tiers
│   ├── restart_validators.sh #   Restart validators
│   ├── build_snapshot.py     #   Index bt.subtensor → Parquet
│   └── generate_tasks.py     #   Create tasks + compute ground truth
├── tests/                    #   11 test files (hashing, scoring, e2e, adversarial)
├── docs/
│   ├── Miner.md              #   Miner guide
│   ├── Validator.md          #   Validator guide
│   ├── Scoring.md            #   Full mechanism design
│   └── ...
├── pyproject.toml
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Local Chain Demo

Deploy the full subnet on a local Bittensor chain:

```bash
# 1. Start local subtensor
docker run -d --name subtensor \
  -p 9944:9944 -p 30333:30333 \
  opentensor/subtensor:latest \
  node-subtensor --chain local --rpc-external --ws-external

# 2. Create wallets (10 miners + 3 validators)
for i in 1 2 3; do btcli wallet create --wallet.name validator_$i --no-password; done
for i in $(seq 1 10); do btcli wallet create --wallet.name miner_$i --no-password; done

# 3. Register subnet + neurons on netuid 3
# (fund wallets from Alice faucet first)
btcli subnet create --wallet.name validator_1 --subtensor.network ws://127.0.0.1:9944

# 4. Launch everything
bash scripts/run_local.sh

# 5. Watch it work
tail -f /tmp/validator_logs/validator_1.log
```

---

## Configuration

Key settings in `queryagent/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `CORRECTNESS_WEIGHT` | 0.75 | Base score for correct hash |
| `EFFICIENCY_WEIGHT` | 0.15 | Bonus for fast SQL execution |
| `LATENCY_WEIGHT` | 0.10 | Bonus for fast response |
| `EMA_ALPHA` | 0.1 | Smoothing factor |
| `EASY_SHARE` | 30% | Task sampling weight |
| `MEDIUM_SHARE` | 50% | Task sampling weight |
| `HARD_SHARE` | 20% | Task sampling weight |
| `HIDDEN_RATIO` | 20% | Probability of hidden task |
| `FLOAT_PRECISION` | 6 | Decimal places for canonical hash |
| `WEIGHTS_RATE_LIMIT` | 200 blocks | Min gap between set_weights calls (~40 min) |
| `VALIDATION_INTERVAL_S` | 120 | Seconds between validation rounds |

---

## Hardware Requirements

| Role | CPU | RAM | Storage | GPU |
|------|-----|-----|---------|-----|
| Miner | 2+ cores | 4 GB | 2 GB | Not required |
| Validator | 2+ cores | 4 GB | 2 GB | Not required |

---

## License

MIT

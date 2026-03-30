# QueryAgent

**Ask blockchain questions in plain English. Get verified, provable answers anyone can check.**

QueryAgent is a Bittensor subnet where miners compete to answer on-chain analytics questions using SQL. Validators re-execute every query on frozen data snapshots and verify results using deterministic SHA-256 hashing. No trust required — the math proves the answer is correct.

---

## How It Works

```
                          ┌──────────────┐
                          │   Validator   │
                          │              │
                  ┌───────┤ 1. Sample task│
                  │       │ 2. Send query │
                  │       │              │
                  │       └──────┬───────┘
                  │              │
          ┌───────▼───┐   ┌─────▼─────┐   ┌───────────┐
          │  Miner A  │   │  Miner B  │   │  Miner C  │
          │ (strong)  │   │ (medium)  │   │  (weak)   │
          │           │   │           │   │           │
          │ Generate  │   │ Generate  │   │ Generate  │
          │ SQL →     │   │ SQL →     │   │ SQL →     │
          │ Execute → │   │ Execute → │   │ Execute → │
          │ Hash      │   │ Hash      │   │ Hash      │
          └───────┬───┘   └─────┬─────┘   └─────┬─────┘
                  │             │               │
                  └─────────────┼───────────────┘
                                │
                          ┌─────▼─────────┐
                          │   Validator    │
                          │               │
                          │ 3. Re-execute  │
                          │ 4. Compare hash│
                          │ 5. Score       │
                          │ 6. set_weights │
                          └───────────────┘
```

1. **Validator** samples a task (natural language question + snapshot reference)
2. **Miners** receive the task via `QuerySynapse`, generate SQL, execute on DuckDB, return SQL + result hash
3. **Validator** re-executes miner SQL on the same frozen snapshot, compares hash to ground truth
4. **Scoring**: 75% correctness (hard gate) + 15% efficiency + 10% latency
5. **Weights** set on-chain via `set_weights()` — Yuma Consensus allocates emissions

## Scoring Formula

```
IF hash mismatch → score = 0.0  (no partial credit)
IF hash matches  → score = 0.75 + 0.15 * efficiency + 0.10 * latency

efficiency = max(0, 1 - exec_ms / budget_ms)       # validator-timed SQL execution
latency    = max(0, 1 - response_ms / latency_ms)   # end-to-end response time

EMA[uid] = 0.1 * new_score + 0.9 * EMA[uid]         # smoothed over rounds
weight[uid] = EMA[uid] / sum(all EMA scores)         # normalized to weights
```

---

## Project Structure

```
queryagent/
├── queryagent/               # Core SDK module
│   ├── protocol.py           #   QuerySynapse wire format (bt.Synapse)
│   ├── config.py             #   All tunable parameters
│   ├── hashing.py            #   Deterministic SHA-256 result hashing
│   ├── scoring.py            #   Score computation + EMA + weight normalization
│   ├── snapshot.py           #   Parquet → DuckDB loader (read-only, sandboxed)
│   ├── tasks.py              #   Task pool manager (public + hidden tasks)
│   └── training.py           #   Training data pipeline (scored responses → JSONL)
│
├── neurons/                  # Miner & Validator implementations
│   ├── miner.py              #   Reference miner (template SQL, for testnet)
│   ├── miner_local.py        #   Local chain miner (--skill tiers: strong/medium/weak)
│   ├── miner_llm.py          #   LLM-based miner (OpenAI GPT-4o)
│   ├── validator.py          #   Reference validator (for testnet)
│   └── validator_local.py    #   Local chain validator (direct substrate calls)
│
├── backend/                  # FastAPI REST API
│   ├── main.py               #   App + CORS + route mounting
│   └── routes/               #   /api/query, /api/chat, /api/leaderboard, etc.
│
├── benchmark/                # Data & ground truth
│   ├── snapshots/            #   Frozen Parquet dataset bundles
│   ├── tasks/                #   Public (16) + hidden (4) task definitions
│   └── ground_truth/         #   Pre-computed reference SQL + SHA-256 hashes
│
├── scripts/                  # Deployment & utilities
│   ├── run_local.sh          #   Full deploy: 10 miners + 3 validators
│   ├── restart_miners.sh     #   Restart miners only (with skill tiers)
│   ├── restart_validators.sh #   Restart validators only
│   ├── build_snapshot.py     #   Index bt.subtensor → Parquet snapshot
│   └── generate_tasks.py     #   Create tasks + compute ground truth hashes
│
├── tests/                    # Test suite (11 files)
│   ├── test_hashing.py       #   Deterministic hash verification
│   ├── test_scoring.py       #   Score formula + EMA + weights
│   ├── test_determinism.py   #   100x identical execution, concurrent threading
│   ├── test_adversarial.py   #   SQL injection, fake validators, sybil attacks
│   └── ...
│
├── docs/                     # Documentation
│   └── mechanism_design.md   #   Full mechanism design explanation
│
├── pyproject.toml            # Package metadata + dependencies
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container build
└── docker-compose.yml        # Multi-service orchestration
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Bittensor (`pip install bittensor`)
- DuckDB, PyArrow, Torch, Structlog

### Install

```bash
git clone https://github.com/queryagent/queryagent.git
cd queryagent
pip install -e .
```

### Run Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Local Chain Demo (Competition Setup)

This runs the full subnet on a local Bittensor chain — 10 miners + 3 validators with differentiated scoring.

### 1. Start Local Subtensor Node

```bash
docker run -d --name subtensor \
  -p 9944:9944 -p 30333:30333 \
  opentensor/subtensor:latest \
  node-subtensor --chain local --rpc-external --ws-external
```

### 2. Create Wallets

```bash
# 3 validators
for i in 1 2 3; do
  btcli wallet create --wallet.name validator_$i --wallet.hotkey default --no-password
done

# 10 miners
for i in $(seq 1 10); do
  btcli wallet create --wallet.name miner_$i --wallet.hotkey default --no-password
done
```

### 3. Fund Wallets + Register Subnet

```bash
# Fund from Alice (local chain faucet) — use substrate or btcli
# Create subnet on netuid 3
btcli subnet create --wallet.name validator_1 --subtensor.network ws://127.0.0.1:9944

# Register all 13 neurons
for w in validator_1 validator_2 validator_3 miner_{1..10}; do
  btcli subnet register --wallet.name $w --netuid 3 --subtensor.network ws://127.0.0.1:9944
done
```

### 4. Launch Everything

```bash
bash scripts/run_local.sh
```

This starts:
- **10 miners** on ports 8091-8100 (3 strong, 4 medium, 3 weak)
- **3 validators** querying miners every ~12 seconds

### 5. Verify

```bash
# Watch validator scoring
tail -f /tmp/validator_logs/validator_1.log

# Expected output:
#   UID 3: CORRECT | score=0.9985 | hash=sha256:be96fcd...
#   UID 10: No response (status=200)    ← weak miner skipping hard task
#   >>> SET_WEIGHTS at block 5678 <<<
#   Weights set successfully (10 non-zero)
```

---

## Backend API

```bash
cd queryagent
cp backend/.env.example backend/.env
# Edit backend/.env and add your Gemini API key

pip install fastapi uvicorn python-dotenv httpx
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Endpoints: `/api/health`, `/api/query`, `/api/chat`, `/api/leaderboard`, `/api/schema`, `/api/stats`

---

## Testnet Hotkeys

### Validators (UIDs 0-2)

| UID | Wallet | Hotkey (SS58) |
|-----|--------|---------------|
| 0 | validator_1 | `5HTURs6HDC6E9QVrb9678n8cHFooiZeURnWmewBtqxxBn21f` |
| 1 | validator_2 | `5G1VGqgyhtiGSMMCABtFGimPkdwgipQsES2byoCgAJdLJLMS` |
| 2 | validator_3 | `5DvQzprdYdCjD78FXNtyRWfddJFSno7MubwoTScow97wC43J` |

### Miners (UIDs 3-12)

| UID | Wallet | Skill | Hotkey (SS58) |
|-----|--------|-------|---------------|
| 3 | miner_1 | strong | `5CAtaej3Tcm67f3nuSciT61HCXcFmkyaoSUrSCwWTgwMv8VC` |
| 4 | miner_2 | strong | `5GmzoCEBAhicKfgkNNKnrbSitCWtCZXpiWD3rrG4aEX1EXr6` |
| 5 | miner_3 | strong | `5D359ZASTHpXFXEkrzefgu8ho917xeA3gAdBcsJMgNp7ETcr` |
| 6 | miner_4 | medium | `5FRMhNQdrtzcbpgcDfDLwzucTmBDkZoFgmck74t64zs1C9mN` |
| 7 | miner_5 | medium | `5C7qnYV51BSDXeQKwk5tLHrr3tHCpDpWzNdomDJCKhCcVuNm` |
| 8 | miner_6 | medium | `5CMiY4V1AT2FnRE7iarxKwJbZ2Heyq2uL9LWh4tfixSi53gM` |
| 9 | miner_7 | medium | `5HeT6GfimaSChyReBJYAxKfLFm3LU8NfhdP38FkEAc25nUeW` |
| 10 | miner_8 | weak | `5DU4CZiwrVHo3Ky4YuJYGc2ZSYexx8gYtsmEECjYRfLsM1Me` |
| 11 | miner_9 | weak | `5DyQJdfk15Rgine96dMZJcbpnCsGd6tUccDK3gH1y8wWPAby` |
| 12 | miner_10 | weak | `5G9FyheKogSwrTLdH9iKkhsxQhjb9UoxsmhG7mTG5T2KNjb3` |

---

## Evidence

Running evidence is in the `evidence/` directory (excluded from git — regenerated on each run):

- **Miner logs** — SQL generation, hash computation, response times
- **Validator logs** — task sampling, hash verification, scoring, EMA updates
- **set_weights proof** — on-chain weight submissions with differentiated weights
- **Score differentiation** — strong miners (~0.98) > medium (~0.46) > weak (~0.17)

### Sample Validator Output

```
=== Validation Round ===
  Task: QB-032 (hard)
  Question: For each subnet, rank validators by emission efficiency and show top 3

  UID 3: CORRECT | score=0.9983 | exec=5.1ms | hash=sha256:8631152162157...
  UID 4: CORRECT | score=0.9983 | exec=2.8ms | hash=sha256:8631152162157...
  UID 5: CORRECT | score=0.9983 | exec=3.3ms | hash=sha256:8631152162157...
  UID 6: No response (status=200)    ← medium miner skips hard tasks
  UID 10: No response (status=200)   ← weak miner skips hard tasks

>>> SET_WEIGHTS at block 5678 <<<
  Weights: ['0.0000', '0.0000', '0.0000', '0.1520', '0.1520', '0.1520',
            '0.0720', '0.0720', '0.0720', '0.0720', '0.0260', '0.0260', '0.0260']
  Weights set successfully (10 non-zero)
```

---

## Hardware Requirements

| Role | CPU | RAM | Storage | GPU |
|------|-----|-----|---------|-----|
| Miner | 2+ cores | 4 GB | 2 GB | Not required |
| Validator | 2+ cores | 4 GB | 2 GB | Not required |

---

## Anti-Gaming

- **Hidden tasks** (20%) — miners can't pre-compute answers
- **Parameter injection** — random constraints each round prevent hash caching
- **Monthly snapshot rotation** — invalidates all memorized responses
- **DuckDB sandboxing** — read-only, no filesystem access, SQL keyword blocklist
- **Yuma Consensus clipping** — outlier validators get reduced influence
- **Deregistration pressure** — low-performing miners lose their slot

---

## License

MIT

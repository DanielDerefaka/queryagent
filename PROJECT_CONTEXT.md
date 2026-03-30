# QueryAgent — Full Project Context

> A Bittensor subnet for verified on-chain analytics. Miners compete to answer blockchain questions in plain English with SQL, and validators independently verify every answer using deterministic hashing on frozen data snapshots.

**Status:** Round II (Testnet Phase) — Honorable Mention out of 150+ submissions in the Bittensor Subnet Ideathon (HackQuest × OpenTensor, Feb 2026)

---

## Workspace Layout

```
subnet_dx/
├── queryagent/           # Core library (7 modules)
│   ├── __init__.py
│   ├── protocol.py       # QuerySynapse wire protocol (bt.Synapse subclass)
│   ├── config.py         # All tunable parameters, paths, scoring weights
│   ├── hashing.py        # Deterministic SHA-256 hashing of query results
│   ├── scoring.py        # 75/15/10 scoring formula + EMA + weight normalization
│   ├── snapshot.py       # Parquet → DuckDB loader + SQL safety checks
│   └── tasks.py          # Task pool, sampling, parameter injection, tier distribution
│
├── neurons/              # Miner & validator implementations
│   ├── __init__.py
│   ├── miner.py          # Template-based miner (regex → SQL, 15 patterns)
│   ├── miner_llm.py      # LLM miner (OpenAI GPT-4o) + hybrid strategy
│   └── validator.py      # Validator loop (sample → query → verify → score → set_weights)
│
├── tests/                # 11 test files, 50+ test functions
│   ├── test_protocol.py      # 3 tests — synapse creation and field defaults
│   ├── test_hashing.py       # 8 tests — determinism, NULL handling, float precision
│   ├── test_scoring.py       # 12 tests — score formula, EMA, weight normalization
│   ├── test_snapshot.py      # 4 tests — parquet loading, SQL safety
│   ├── test_tasks.py         # 15 tests — loading, sampling, tier distribution, injection
│   ├── test_determinism.py   # 11 tests — same query 100x, concurrent threads, joins
│   ├── test_adversarial.py   # 60 tests — SQL injection, hash edge cases, scoring edge cases
│   ├── test_wire.py          # 4 tests — real axon↔dendrite on localhost
│   ├── test_e2e.py           # 5 tests — full miner→validator loop
│   └── test_llm_miner.py    # 2 tests — LLM vs template vs hybrid comparison
│
├── scripts/
│   ├── build_snapshot.py     # Indexes Bittensor chain → Parquet tables
│   └── generate_tasks.py     # Generates tasks + ground truth hashes
│
├── benchmark/
│   ├── tasks/
│   │   ├── public_tasks.json   # 16 public tasks
│   │   └── hidden_tasks.json   # 4 hidden tasks (anti-gaming)
│   ├── ground_truth/
│   │   └── QB-001.json ... QB-033.json  # 20 ground truth files
│   └── snapshots/
│       └── bt_snapshot_test_v1/
│           ├── schema.json      # Table/column definitions
│           ├── metadata.json    # Block number, row counts, checksums
│           └── tables/          # 6 Parquet files
│
├── docs/                 # 10 Round I deliverables (html, pdf, docx, pitch deck)
├── findings/             # 13 research files (knowledge base + architecture blueprint)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── min_compute.yml
└── .env.example
```

---

## How It Works

### The Core Loop

```
Validator samples a task ("Which subnet has the highest stake?")
    ↓
Broadcasts QuerySynapse to all miners via bt.Dendrite
    ↓
Miner receives task via bt.Axon:
  1. Loads frozen Parquet snapshot into DuckDB
  2. Generates SQL (template match or LLM fallback)
  3. Executes SQL, hashes result deterministically (SHA-256)
  4. Returns: {sql, result_hash, preview, tables_used, explanation}
    ↓
Validator receives response:
  1. Re-executes miner's SQL on own DuckDB (same snapshot)
  2. Computes hash independently
  3. Compares to ground truth hash
  4. Scores miner: 75% correctness + 15% efficiency + 10% latency
  5. Updates EMA scores (α=0.1)
    ↓
Validator calls set_weights() on-chain
    ↓
Bittensor Yuma Consensus → TAO emission allocation
```

### Why Hash-Based Verification Works

The key insight: if two parties execute the same SQL on the same frozen dataset, they get the same result. We hash that result deterministically (sorted rows, fixed float precision, NULL sentinels) so any honest validator produces the same ground truth hash. This makes verification trivial — just compare hashes.

---

## Module Details

### queryagent/protocol.py — Wire Protocol

```python
class QuerySynapse(bt.Synapse):
    # Request (validator → miner)
    task_id: str                          # e.g. "QB-001"
    snapshot_id: str                      # e.g. "bt_snapshot_test_v1"
    question: str                         # Natural language question
    constraints: Optional[dict] = None    # {k, netuid_filter, time_window}

    # Response (miner → validator)
    sql: Optional[str] = None
    result_hash: Optional[str] = None     # "sha256:<hex>"
    result_preview: Optional[dict] = None # {columns, rows}
    tables_used: Optional[List[str]] = None
    explanation: Optional[str] = None
```

### queryagent/config.py — Configuration

| Parameter | Value | Purpose |
|-----------|-------|---------|
| CORRECTNESS_WEIGHT | 0.75 | Hard gate — hash must match |
| EFFICIENCY_WEIGHT | 0.15 | SQL execution speed bonus |
| LATENCY_WEIGHT | 0.10 | Response time bonus |
| EMA_ALPHA | 0.1 | Smoothing factor |
| EASY_SHARE / MEDIUM / HARD | 0.30 / 0.50 / 0.20 | Task tier distribution |
| HIDDEN_RATIO | 0.20 | Anti-memorization |
| FLOAT_PRECISION | 6 | Decimal places for canonical floats |
| NULL_REPR | `\x00NULL\x00` | Sentinel (prevents NULL/"NULL" collision) |
| DEFAULT_TIMEOUT_S | 30 | Miner response deadline |
| DEFAULT_BUDGET_MS | 5000 | SQL execution budget (easy) |

### queryagent/hashing.py — Deterministic Hashing

```python
def hash_result(conn, sql) -> str:
    """Execute SQL, canonicalize output, return 'sha256:<hex>'."""
    # 1. Execute SQL
    # 2. Canonicalize each value (floats→6dp, NULL→sentinel, bool→lowercase)
    # 3. Sort rows lexicographically
    # 4. Build canonical string: header + sorted rows (pipe-delimited)
    # 5. SHA-256 hash

def hash_from_rows(columns, rows) -> str:
    """Same hashing from pre-fetched data (no DB connection needed)."""

def verify_hash(conn, sql, expected_hash) -> bool:
    """Execute and compare."""
```

**Guarantees:**
- Same SQL + same snapshot = same hash (always)
- Row order independent (sorted before hashing)
- Float precision fixed to 6 decimals
- NULL vs "NULL" distinguished by sentinel
- Thread-safe (read-only operations)

### queryagent/scoring.py — Scoring Engine

```python
def compute_score(correct: bool, exec_ms, budget_ms, response_ms, latency_ms) -> float:
    if not correct:
        return 0.0  # Hard gate
    efficiency = max(0.0, 1 - exec_ms / budget_ms)
    latency = max(0.0, 1 - response_ms / latency_ms)
    return 0.75 + 0.15 * efficiency + 0.10 * latency
    # Range for correct answers: [0.75, 1.0]

def update_ema(scores, new_scores, alpha=0.1):
    return alpha * new_scores + (1 - alpha) * scores

def normalize_weights(scores):
    # Scores → weights that sum to 1.0
```

### queryagent/snapshot.py — Snapshot Loader

```python
def load_snapshot(snapshot_id, use_cache=True) -> DuckDBPyConnection:
    """Load Parquet files into in-memory DuckDB. Caches connections."""

def execute_sql_safe(conn, sql, timeout_ms=None):
    """Execute with safety checks — blocks CREATE/DROP/INSERT/UPDATE/DELETE/ALTER."""
    # Returns: (columns, rows, exec_ms)
```

**Snapshot structure:**
- 6 tables: subnets, validators, miners, stakes, emissions, metagraph
- Built from real Bittensor testnet (block 6655193)
- 10 subnets, 9 validators, 1106 miners, 490 stakes, 24 emissions

### queryagent/tasks.py — Task Pool

```python
class TaskPool:
    def load()           # Loads public + hidden tasks + ground truth
    def sample_task()    # Weighted tier sampling + parameter injection
    def get_ground_truth(task_id)  # Fetch expected hash

# 20 total tasks: 6 easy, 10 medium, 4 hard
# Hidden tasks: QB-030 to QB-033 (never published)
# Parameter injection: k, time_window, netuid_filter randomized
```

---

## Neuron Implementations

### neurons/miner.py — Template Miner

15 regex patterns that match questions to SQL templates. Fast, deterministic, free (no API calls). Gets 12/20 tasks correct but can't handle questions outside its patterns.

```python
TEMPLATES = [
    (r"total.*stak", "SELECT SUM(stake) AS total_staked FROM stakes"),
    (r"how many.*subnets", "SELECT COUNT(DISTINCT netuid) AS subnet_count FROM subnets"),
    (r"top (\d+).*validators.*stake", "SELECT ... ORDER BY stake DESC LIMIT {k}"),
    # ... 12 more patterns
]

def generate_sql(question, constraints) -> Optional[dict]:
    # Match question → template → inject parameters → return {sql, tables, explanation}

def forward(synapse: QuerySynapse) -> QuerySynapse:
    # Load snapshot → generate SQL → execute → hash → fill response
```

### neurons/miner_llm.py — LLM + Hybrid Miner

Sends question + database schema to OpenAI GPT-4o. The hybrid strategy tries templates first (fast, free), falls back to LLM for unmatched questions.

```python
def generate_sql_llm(question, snapshot_id, constraints) -> Optional[dict]:
    # Build prompt with schema + DuckDB rules + few-shot examples
    # Send to GPT-4o
    # Extract SQL from response
    # Return {sql, tables, explanation}

def generate_sql_hybrid(question, snapshot_id, constraints) -> Optional[dict]:
    # Try template first → if no match, fall back to LLM

def forward(synapse):
    # Uses hybrid strategy
```

**Benchmark results (20 tasks):**
| Strategy | Correct | No Match | Wrong | Errors |
|----------|---------|----------|-------|--------|
| Template | 12/20 | 4 | 4 | 0 |
| LLM (GPT-4o) | 9-10/20 | 0 | 10 | 1 |
| Hybrid | 12/20 | 0 | 6 | 2 |

### neurons/validator.py — Validator

```python
def reexecute_miner_sql(conn, sql, budget_ms):
    # Re-execute on validator's DuckDB, time it
    # Return (result_hash, exec_ms) or None

def run_validation_round(dendrite, metagraph, task_pool, conn, scores):
    # 1. Sample task
    # 2. Broadcast to miners via dendrite
    # 3. Re-execute each response
    # 4. Compare hashes to ground truth
    # 5. Score (75/15/10)
    # 6. Update EMA
    # Return updated scores

def main():
    # Main loop: validate every 12 blocks, set_weights every 100 blocks
```

---

## Test Suite

| Test File | Tests | What It Covers |
|-----------|-------|---------------|
| test_protocol.py | 3 | Synapse creation, field defaults, response filling |
| test_hashing.py | 8 | Determinism, NULL handling, float precision, empty results |
| test_scoring.py | 12 | Score formula, EMA smoothing, weight normalization |
| test_snapshot.py | 4 | Parquet loading, SQL safety (blocks writes) |
| test_tasks.py | 15 | Loading, sampling, tier distribution (30/50/20), parameter injection |
| test_determinism.py | 11 | Same query 100x, concurrent threads, cross-connection, joins |
| test_adversarial.py | 60 | SQL injection (17), hash edge cases (12), scoring edge cases (10), miner edge cases (8), snapshot integrity (9), validator re-execution (4) |
| test_wire.py | 4 | Real bt.Axon↔bt.Dendrite on localhost |
| test_e2e.py | 5 | Full miner→validator loop |
| test_llm_miner.py | 2 | LLM vs template vs hybrid comparison |
| **Total** | **~124** | |

---

## Anti-Gaming Measures

1. **Hidden tasks** — 4 tasks (20%) never published, only validators know them
2. **Parameter injection** — k, time_window, netuid_filter randomized per sample
3. **Monthly snapshot rotation** — new frozen dataset prevents memorization
4. **DuckDB sandboxing** — blocks CREATE/DROP/INSERT/UPDATE/DELETE/ALTER/COPY/EXPORT
5. **Hash-based scoring** — no partial credit; wrong hash = 0.0
6. **Deregistration pressure** — poor performers removed by Yuma Consensus
7. **Deterministic hashing** — can't fake results without SHA-256 collision

---

## Key Design Decisions

1. **Frozen Parquet snapshots** — both miner and validator use identical data, making hash comparison possible
2. **DuckDB in-memory** — fast SQL execution, no external database dependency
3. **75% correctness hard gate** — speed doesn't matter if you're wrong
4. **EMA smoothing (α=0.1)** — prevents score manipulation from single good/bad rounds
5. **Template + LLM hybrid** — deterministic templates for known patterns, LLM for everything else
6. **NULL sentinel (`\x00NULL\x00`)** — prevents hash collision between SQL NULL and the string "NULL"

---

## Critical Bugs Found & Fixed

1. **NULL collision** — `_canonicalize_value(None)` and `_canonicalize_value("NULL")` both returned `"NULL"`. Fixed with `\x00NULL\x00` sentinel.
2. **Snapshot monkeypatch** — `from config import SNAPSHOT_DIR` copies the value at import time. Tests couldn't override it. Fixed by importing the module: `from queryagent import config` and using `config.SNAPSHOT_DIR`.
3. **Bittensor v10 API** — `bt.subtensor` → `bt.Subtensor`, `get_subnets()` → `get_all_subnets_netuid()`, `meta.ranks` removed. Updated all references.
4. **Cross-table LEFT JOIN NULLs** — subnets with only miners or only validators produced NULL counts. Fixed with `COALESCE()`.

---

## Emissions Split (dTAO)

- 41% miners
- 41% validators
- 18% subnet owner

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Build snapshot from Bittensor testnet
python scripts/build_snapshot.py --network test --output benchmark/snapshots/bt_snapshot_test_v1

# Generate tasks + ground truth
python scripts/generate_tasks.py --snapshot bt_snapshot_test_v1

# Run tests
PYTHONPATH=. python3.11 -m pytest tests/ -v

# Run template miner
python -m neurons.miner --netuid 1 --wallet.name default --wallet.hotkey default --subtensor.network test

# Run LLM miner (requires OpenAI key)
OPENAI_API_KEY=sk-... python -m neurons.miner_llm --netuid 1 --wallet.name default --wallet.hotkey default --subtensor.network test

# Run validator
python -m neurons.validator --netuid 1 --wallet.name default --wallet.hotkey default --subtensor.network test
```

---

## What's Left for Testnet

1. **Register on Bittensor testnet** — create subnet, register miner + validator, run incentive loop on-chain
2. **Demo video** — validator sends task, miner responds, hash matches, weights update
3. **README** — setup instructions, architecture overview
4. **Docker polish** — optional but cleaner for demo

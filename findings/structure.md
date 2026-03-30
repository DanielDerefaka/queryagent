# QueryAgent — Full Subnet Structure & Build Blueprint

This document maps every file we will create, what it does, how it connects to other files, and the logic inside each one. This is the single source of truth for the testnet build.

---

## Project Root

```
queryagent/
│
├── neurons/
│   ├── __init__.py
│   ├── miner.py                    # Miner entry point — receives tasks, returns Answer Packages
│   └── validator.py                # Validator entry point — sends tasks, scores miners, sets weights
│
├── queryagent/
│   ├── __init__.py
│   ├── protocol.py                 # QuerySynapse definition (bt.Synapse subclass)
│   ├── scoring.py                  # Score computation (hash check, efficiency, latency, EMA)
│   ├── snapshot.py                 # Parquet → DuckDB loader (read-only, sandboxed)
│   ├── tasks.py                    # Task pool manager (sample, filter by tier, track hidden)
│   ├── hashing.py                  # Deterministic SHA-256 hashing of DuckDB query results
│   └── config.py                   # Shared constants and configuration defaults
│
├── benchmark/
│   ├── snapshots/
│   │   └── bt_snapshot_2026_03_v1/
│   │       ├── schema.json         # Table definitions (names, columns, types)
│   │       ├── metadata.json       # Build time, source, row counts, checksums
│   │       └── tables/
│   │           ├── subnets.parquet
│   │           ├── validators.parquet
│   │           ├── miners.parquet
│   │           ├── stakes.parquet
│   │           ├── emissions.parquet
│   │           └── metagraph.parquet
│   ├── tasks/
│   │   ├── public_tasks.json       # 200 public tasks (visible to everyone)
│   │   └── hidden_tasks.json       # 50 hidden tasks (never published, validator-only)
│   └── ground_truth/
│       ├── QB-001.json             # { task_id, reference_sql, expected_hash, tier, budget_ms }
│       ├── QB-002.json
│       └── ...
│
├── scripts/
│   ├── build_snapshot.py           # Index bt.subtensor → Parquet snapshot bundle
│   ├── generate_tasks.py           # Create task pool + compute ground truth hashes
│   └── verify_snapshot.py          # Validate snapshot integrity (checksums, schema match)
│
├── tests/
│   ├── test_protocol.py            # QuerySynapse serialization/deserialization
│   ├── test_scoring.py             # Score computation edge cases
│   ├── test_hashing.py             # Determinism — same query = same hash every time
│   ├── test_snapshot.py            # Parquet loading, DuckDB sandboxing
│   └── integration/
│       └── test_full_loop.py       # Mock miner ↔ validator cycle end-to-end
│
├── docs/
│   ├── running_on_testnet.md       # How to deploy miner + validator on testnet
│   ├── running_on_mainnet.md       # Mainnet deployment guide (future)
│   └── task_authoring.md           # How to write new tasks and ground truth
│
├── pyproject.toml                  # Project metadata, dependencies
├── requirements.txt                # Pinned dependencies for pip
├── min_compute.yml                 # Minimum hardware requirements
├── Dockerfile                      # Container for miner/validator
├── docker-compose.yml              # Multi-service setup
├── .env.example                    # Environment variable template
├── .gitignore
├── LICENSE
└── README.md                       # Overview, setup, run instructions
```

---

## File-by-File Breakdown

---

### `queryagent/protocol.py` — Wire Format

**What it does**: Defines the `QuerySynapse` class that validators send to miners and miners return filled.

**Depends on**: `bittensor`

```python
class QuerySynapse(bt.Synapse):
    # ── Request (validator fills) ──
    task_id: str = ""
    snapshot_id: str = ""
    question: str = ""
    constraints: Optional[dict] = None       # { time_window, max_rows, netuid_filter, k }

    # ── Response (miner fills) ──
    sql: Optional[str] = None
    result_hash: Optional[str] = None        # SHA-256 of deterministic result
    result_preview: Optional[dict] = None    # { columns: [...], rows: [[...], ...] }
    tables_used: Optional[List[str]] = None  # ["subnets", "emissions"]
    explanation: Optional[str] = None        # Short text explaining the SQL
```

**Key rules**:
- All response fields are `Optional[...] = None` — synapse must be valid before miner fills it
- Must be fully JSON serializable (no custom objects in fields)
- Both validator and miner import the exact same class

---

### `queryagent/snapshot.py` — Snapshot Loader

**What it does**: Loads a Parquet snapshot bundle into a DuckDB in-memory database. Used by BOTH miner and validator.

**Depends on**: `duckdb`, `pyarrow`, `json`, `pathlib`

**Core logic**:
```
load_snapshot(snapshot_path: str) → duckdb.Connection
  1. Read schema.json → get table names and column types
  2. Create DuckDB in-memory connection (READ ONLY)
  3. For each table in schema:
     - Load tables/{name}.parquet into DuckDB as a table
  4. Disable any write/network/shell access
  5. Return connection
```

**Key details**:
- Read-only mode — miners cannot write, access filesystem, or make network calls
- In-memory — fast execution, no disk I/O during queries
- Deterministic — same Parquet files = same DuckDB state = same query results
- Snapshot path: `benchmark/snapshots/bt_snapshot_2026_03_v1/`
- Caches loaded snapshots to avoid reloading on every request

---

### `queryagent/hashing.py` — Deterministic Result Hashing

**What it does**: Takes a DuckDB query result and produces a deterministic SHA-256 hash. This is the core of the verification system.

**Depends on**: `hashlib`, `duckdb`

**Core logic**:
```
hash_result(connection: duckdb.Connection, sql: str) → str
  1. Execute SQL on DuckDB connection
  2. Fetch all rows as list of tuples
  3. Sort rows deterministically (by all columns)
  4. Serialize to canonical string format:
     - Column names joined by |
     - Each row: values joined by | with consistent formatting
     - Floats rounded to 6 decimal places
     - NULLs represented as "NULL"
     - Dates as ISO 8601 strings
  5. SHA-256 hash the canonical string
  6. Return "sha256:{hex_digest}"
```

**Why this is critical**: If the canonical format is not 100% deterministic, miners and validators will compute different hashes for the same data. This breaks the entire scoring system. Must handle:
- Float precision (round to fixed decimals)
- NULL ordering
- Row ordering (sort before hashing)
- Date/timestamp formatting
- Empty results

---

### `queryagent/scoring.py` — Score Computation

**What it does**: Computes miner scores from validator re-execution results. Manages EMA smoothing and weight normalization.

**Depends on**: `queryagent/hashing.py`, `torch` or `numpy`

**Core logic**:
```
compute_score(response, ground_truth, exec_ms, budget_ms, response_ms, latency_ms) → float
  1. HARD GATES (any = score 0.0):
     - response.sql is None or empty → 0.0
     - response.result_hash is None → 0.0
     - SQL execution error during validator re-run → 0.0
     - validator_hash ≠ ground_truth_hash → 0.0

  2. SCORE COMPONENTS (if hash matches):
     - correctness = 0.75 (full weight, binary)
     - efficiency = 0.15 × max(0.0, 1 - exec_ms / budget_ms)
     - latency = 0.10 × max(0.0, 1 - response_ms / latency_ms)
     - score = correctness + efficiency + latency
     - Range: [0.75, 1.0] for correct answers

  3. EMA SMOOTHING (across rounds within tempo):
     - EMA[uid] = α × new_score + (1 - α) × EMA[uid]
     - α = 0.1 (smoothing factor)

  4. WEIGHT NORMALIZATION:
     - weight[uid] = EMA[uid] / Σ(EMA)
     - Weights sum to 1.0
     - Submitted via set_weights() on-chain
```

---

### `queryagent/tasks.py` — Task Pool Manager

**What it does**: Manages the pool of tasks, samples by difficulty tier, handles hidden vs public, and injects parameterized variants.

**Depends on**: `json`, `random`, `pathlib`

**Core logic**:
```
TaskPool:
  load(tasks_dir, ground_truth_dir)
    - Load public_tasks.json + hidden_tasks.json
    - Load ground truth for each task
    - Index by tier (easy/medium/hard) and visibility (public/hidden)

  sample_task() → Task
    - Weighted random: 30% easy, 50% medium, 20% hard
    - Mix public and hidden tasks (hidden ≈ 20% of samples)
    - Apply parameter injection:
      - Randomize time_window (7d, 14d, 30d, 90d)
      - Randomize k value (top 5, 10, 20)
      - Randomize netuid filter
    - Return task with ground_truth_hash and budget_ms

Task:
  task_id: str
  snapshot_id: str
  question: str               # Natural language question
  constraints: dict            # { time_window, max_rows, k, netuid }
  reference_sql: str           # Author's SQL (never shown to miners)
  ground_truth_hash: str       # SHA-256 of expected result
  tier: str                    # "easy" | "medium" | "hard"
  budget_ms: int               # Max SQL execution time
  latency_ms: int              # Max end-to-end response time
  is_hidden: bool              # If true, never published
```

---

### `queryagent/config.py` — Shared Constants

**What it does**: Central place for all tunable parameters.

```python
# Scoring weights
CORRECTNESS_WEIGHT = 0.75
EFFICIENCY_WEIGHT = 0.15
LATENCY_WEIGHT = 0.10

# EMA
EMA_ALPHA = 0.1

# Task distribution
EASY_SHARE = 0.30
MEDIUM_SHARE = 0.50
HARD_SHARE = 0.20
HIDDEN_RATIO = 0.20

# Timeouts
DEFAULT_TIMEOUT = 30          # seconds — miner must respond within this
DEFAULT_BUDGET_MS = 5000      # milliseconds — max SQL execution time
DEFAULT_LATENCY_MS = 30000    # milliseconds — max end-to-end time

# Snapshot
SNAPSHOT_DIR = "benchmark/snapshots"
TASKS_DIR = "benchmark/tasks"
GROUND_TRUTH_DIR = "benchmark/ground_truth"

# Hashing
FLOAT_PRECISION = 6           # decimal places for float rounding
NULL_REPR = "NULL"            # canonical NULL representation
```

---

### `neurons/miner.py` — Reference Miner

**What it does**: Receives QuerySynapse via axon, generates SQL, executes on DuckDB, returns Answer Package.

**Depends on**: `queryagent/protocol.py`, `queryagent/snapshot.py`, `queryagent/hashing.py`, `bittensor`

**Flow**:
```
1. STARTUP:
   - Parse args (--netuid, wallet, subtensor config)
   - Connect to subtensor, sync metagraph
   - Load snapshot into DuckDB (cached)
   - Create axon, attach forward function, serve + start

2. FORWARD (called per request):
   forward(synapse: QuerySynapse) → QuerySynapse:
     a. Load snapshot for synapse.snapshot_id (from cache or disk)
     b. Generate SQL from synapse.question:
        - Template matching first (pattern library of ~50 common queries)
        - Optional: LLM fallback if no template matches
     c. Execute SQL on DuckDB connection
     d. Compute SHA-256 hash of result (via hashing.py)
     e. Build result_preview (first 10 rows, column names)
     f. Set synapse.sql, synapse.result_hash, synapse.result_preview,
        synapse.tables_used, synapse.explanation
     g. Return synapse

3. MAIN LOOP:
   - Sync metagraph every 12 seconds
   - Log status (registered, UID, stake, rank)
   - Handle graceful shutdown (SIGTERM/SIGINT)
```

**SQL Generation Strategy (v1 — template-based)**:
```
Templates = dictionary of {pattern → SQL template}

Examples:
  "total * staked"     → "SELECT SUM(stake) FROM stakes"
  "top {k} * by *"     → "SELECT ... ORDER BY {col} DESC LIMIT {k}"
  "* growth * {n} days" → "SELECT ... WHERE date >= snapshot_date - INTERVAL '{n} days'"

Match: regex patterns against synapse.question
Inject: constraints (k, time_window, netuid) into SQL template
Execute: run on DuckDB, hash result, return
```

---

### `neurons/validator.py` — Validator

**What it does**: Samples tasks, broadcasts to miners, re-executes SQL, scores, sets weights on-chain.

**Depends on**: `queryagent/protocol.py`, `queryagent/scoring.py`, `queryagent/snapshot.py`, `queryagent/tasks.py`, `queryagent/hashing.py`, `bittensor`

**Flow**:
```
1. STARTUP:
   - Parse args (--netuid, wallet, subtensor config)
   - Connect to subtensor, sync metagraph
   - Create dendrite client
   - Load task pool (public + hidden tasks + ground truth)
   - Load snapshot into DuckDB
   - Initialize EMA scores array: zeros(256)

2. MAIN LOOP (runs continuously):

   a. SYNC metagraph (every ~10-20 blocks)

   b. SAMPLE task from pool
      - Weighted by difficulty tier (30/50/20)
      - Mix hidden tasks (~20% of rounds)
      - Inject randomized parameters

   c. BUILD QuerySynapse
      synapse = QuerySynapse(
          task_id=task.task_id,
          snapshot_id=task.snapshot_id,
          question=task.question,
          constraints=task.constraints
      )

   d. BROADCAST to all miners via dendrite
      responses = dendrite(
          axons=metagraph.axons,
          synapse=synapse,
          timeout=30  # seconds
      )

   e. SCORE each response
      For each (uid, response) in enumerate(responses):
        - If response.sql is None → score = 0.0
        - Else:
          1. Re-execute response.sql on validator's DuckDB (timed)
          2. Compute hash of validator's result
          3. Compare to task.ground_truth_hash
          4. If mismatch → score = 0.0
          5. If match → compute efficiency + latency scores
          6. combined = 0.75 + 0.15 × efficiency + 0.10 × latency
        - EMA update: scores[uid] = 0.1 × new + 0.9 × scores[uid]

   f. SET WEIGHTS (respecting rate limit)
      - Normalize: weights = scores / scores.sum()
      - Submit: subtensor.set_weights(wallet, netuid, uids, weights)
      - Rate limit: at most once per weights_rate_limit blocks (~100 blocks = ~20 min)

   g. LOG round results (task_id, scores, top miners, execution times)

   h. SLEEP until next block (12 seconds)
```

**Safety measures during re-execution**:
- Hard timeout: `budget_ms` per SQL execution — kill query if exceeded
- DuckDB read-only mode — no writes, no filesystem access
- SQL plan analysis (future): reject unbounded scans before execution
- Catch all exceptions — never crash validator on bad miner SQL

---

### `scripts/build_snapshot.py` — Indexer

**What it does**: Connects to `bt.subtensor`, pulls chain data, exports to Parquet snapshot.

**Depends on**: `bittensor`, `pyarrow`, `pandas`, `json`

**Tables to index**:

| Table | Source | Key Columns |
|-------|--------|-------------|
| `subnets` | subtensor.get_all_subnets() | netuid, name, owner, tempo, emission, created_at |
| `validators` | metagraph per subnet | uid, hotkey, stake, vtrust, dividends, active, netuid |
| `miners` | metagraph per subnet | uid, hotkey, stake, rank, trust, incentive, emission, active, netuid |
| `stakes` | subtensor.get_stake_info() | hotkey, coldkey, stake_amount, netuid, timestamp |
| `emissions` | subtensor.get_emission_values() | netuid, uid, emission, block, timestamp |
| `metagraph` | full metagraph dump | netuid, uid, hotkey, stake, rank, trust, consensus, incentive, emission, dividends, active |

**Output structure**:
```
benchmark/snapshots/bt_snapshot_2026_03_v1/
├── schema.json          # { tables: [{ name, columns: [{ name, type }] }] }
├── metadata.json        # { snapshot_id, build_time, block_number, row_counts, checksums }
└── tables/
    ├── subnets.parquet
    ├── validators.parquet
    ├── miners.parquet
    ├── stakes.parquet
    ├── emissions.parquet
    └── metagraph.parquet
```

**Versioning**: `bt_snapshot_YYYY_MM_v{N}` — one per month, N increments if rebuilt.

---

### `scripts/generate_tasks.py` — Task + Ground Truth Generator

**What it does**: Creates the task pool and computes ground truth hashes.

**Depends on**: `queryagent/snapshot.py`, `queryagent/hashing.py`, `duckdb`, `json`

**Process**:
```
1. Load snapshot into DuckDB
2. For each task definition:
   a. Fill in the reference SQL with parameters
   b. Execute reference SQL on DuckDB
   c. Compute SHA-256 hash of result (via hashing.py)
   d. Store: { task_id, snapshot_id, question, constraints, reference_sql,
               ground_truth_hash, tier, budget_ms, latency_ms, is_hidden }
3. Write public_tasks.json (without reference_sql or ground_truth_hash)
4. Write hidden_tasks.json (validator-only, same format)
5. Write individual ground_truth/QB-XXX.json files
```

**Task examples by tier**:

| Tier | Example Question | SQL Complexity |
|------|-----------------|----------------|
| Easy | "Total TAO staked across all subnets" | Single table SUM |
| Easy | "How many active miners on subnet 1?" | Single table COUNT + WHERE |
| Medium | "Top 10 validators by stake growth in last 30 days" | JOIN + time delta + ORDER BY LIMIT |
| Medium | "Subnet with highest emission efficiency" | JOIN + computed metric + ranking |
| Hard | "Subnets where validator trust improved but emissions fell" | Multi-join + two temporal comparisons + conditional |
| Hard | "Correlation between stake concentration and miner churn by subnet" | Complex aggregation + window functions |

---

### `scripts/verify_snapshot.py` — Snapshot Integrity Check

**What it does**: Validates that a snapshot is complete, consistent, and produces deterministic results.

**Checks**:
1. All tables listed in schema.json exist as Parquet files
2. Column types match schema definition
3. Row counts match metadata.json
4. Checksums match (SHA-256 of each Parquet file)
5. DuckDB can load all tables without error
6. A sample of ground truth tasks produce expected hashes

---

### `benchmark/` — Data Layer

```
benchmark/
├── snapshots/
│   └── bt_snapshot_2026_03_v1/
│       ├── schema.json
│       │   {
│       │     "snapshot_id": "bt_snapshot_2026_03_v1",
│       │     "tables": [
│       │       {
│       │         "name": "subnets",
│       │         "columns": [
│       │           { "name": "netuid", "type": "INTEGER" },
│       │           { "name": "name", "type": "VARCHAR" },
│       │           { "name": "owner", "type": "VARCHAR" },
│       │           { "name": "emission", "type": "DOUBLE" },
│       │           { "name": "tempo", "type": "INTEGER" },
│       │           { "name": "created_at", "type": "TIMESTAMP" }
│       │         ]
│       │       },
│       │       ...
│       │     ]
│       │   }
│       │
│       ├── metadata.json
│       │   {
│       │     "snapshot_id": "bt_snapshot_2026_03_v1",
│       │     "build_time": "2026-03-01T00:00:00Z",
│       │     "block_number": 4500000,
│       │     "network": "finney",
│       │     "row_counts": { "subnets": 128, "validators": 8192, ... },
│       │     "checksums": { "subnets.parquet": "sha256:...", ... }
│       │   }
│       │
│       └── tables/
│           ├── subnets.parquet
│           ├── validators.parquet
│           ├── miners.parquet
│           ├── stakes.parquet
│           ├── emissions.parquet
│           └── metagraph.parquet
│
├── tasks/
│   ├── public_tasks.json
│   │   [
│   │     {
│   │       "task_id": "QB-001",
│   │       "snapshot_id": "bt_snapshot_2026_03_v1",
│   │       "question": "Total TAO staked across all subnets",
│   │       "constraints": {},
│   │       "tier": "easy",
│   │       "budget_ms": 5000,
│   │       "latency_ms": 30000
│   │     },
│   │     ...
│   │   ]
│   │
│   └── hidden_tasks.json    # Same format, never published
│
└── ground_truth/
    ├── QB-001.json
    │   {
    │     "task_id": "QB-001",
    │     "reference_sql": "SELECT SUM(stake) as total FROM stakes",
    │     "ground_truth_hash": "sha256:a1b2c3...",
    │     "tier": "easy",
    │     "budget_ms": 5000
    │   }
    └── ...
```

---

### `tests/` — Test Suite

| Test File | What It Tests |
|-----------|---------------|
| `test_protocol.py` | QuerySynapse creates, serializes, deserializes correctly |
| `test_hashing.py` | Same SQL + same data = same hash (determinism). Float precision. NULL handling. Empty results. |
| `test_scoring.py` | Score = 0 on wrong hash. Score in [0.75, 1.0] on correct hash. EMA convergence. Edge cases. |
| `test_snapshot.py` | Parquet loads into DuckDB. Read-only enforced. Schema matches. All tables queryable. |
| `integration/test_full_loop.py` | Mock: validator sends task → miner generates SQL → validator re-executes → scores → weights update |

---

### Root Files

**`pyproject.toml`**:
```toml
[project]
name = "queryagent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "bittensor>=8.0.0",
    "duckdb>=1.0.0",
    "pyarrow>=15.0.0",
    "pandas>=2.0.0",
    "pydantic>=2.0",
    "numpy>=1.24.0",
    "structlog>=23.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
]
```

**`min_compute.yml`**:
```yaml
miner:
  cpu: 4 cores
  ram: 8 GB
  storage: 5 GB
  gpu: not required
  network: stable

validator:
  cpu: 4 cores
  ram: 16 GB
  storage: 10 GB
  gpu: not required
  network: stable
```

**`.env.example`**:
```
BITTENSOR_WALLET_NAME=default
BITTENSOR_WALLET_HOTKEY=default
NETUID=
SUBTENSOR_NETWORK=test
SNAPSHOT_PATH=benchmark/snapshots/bt_snapshot_2026_03_v1
```

---

## Data Flow (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│                        EVERY TEMPO (~72 min)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    QuerySynapse     ┌──────────┐                │
│  │          │ ──────────────────→ │          │                │
│  │VALIDATOR │    (task_id,        │  MINER   │                │
│  │          │     snapshot_id,    │          │                │
│  │          │     question)       │          │                │
│  │          │                     │          │                │
│  │          │    QuerySynapse     │          │                │
│  │          │ ←────────────────── │          │                │
│  │          │    (sql,            │          │                │
│  │          │     result_hash,    │          │                │
│  │          │     tables_used,    │          │                │
│  │          │     explanation)    │          │                │
│  └────┬─────┘                     └──────────┘                │
│       │                                                        │
│       │  1. Re-execute miner's SQL on own DuckDB               │
│       │  2. Hash own result                                    │
│       │  3. Compare to ground_truth_hash                       │
│       │  4. wrong → score = 0.0                                │
│       │  5. correct → 0.75 + 0.15×eff + 0.10×lat              │
│       │  6. EMA smooth                                         │
│       │  7. set_weights() on-chain                             │
│       │                                                        │
│       ▼                                                        │
│  ┌──────────┐                                                  │
│  │ YUMA     │  Aggregates all validator weights                │
│  │CONSENSUS │  → TAO emissions to miners (41%)                 │
│  │          │  → TAO emissions to validators (41%)             │
│  │          │  → TAO to subnet owner (18%)                     │
│  └──────────┘                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Build Order

| Step | File(s) | Why First |
|------|---------|-----------|
| 1 | `queryagent/protocol.py` | Everything imports QuerySynapse |
| 2 | `queryagent/config.py` | Constants used everywhere |
| 3 | `queryagent/hashing.py` | Core of verification — must be deterministic |
| 4 | `queryagent/snapshot.py` | Data foundation — miner + validator both need it |
| 5 | `scripts/build_snapshot.py` | Creates the actual data to work with |
| 6 | `queryagent/tasks.py` | Task pool — validator needs it |
| 7 | `scripts/generate_tasks.py` | Creates tasks + ground truth from snapshot |
| 8 | `queryagent/scoring.py` | Evaluation logic — validator uses it |
| 9 | `neurons/miner.py` | Responds to tasks with Answer Packages |
| 10 | `neurons/validator.py` | Sends tasks, scores miners, sets weights |
| 11 | `tests/*` | Verify everything works before deployment |
| 12 | Testnet deployment | Register subnet + miner + validator on Bittensor testnet |
| 13 | Demo video | Record working incentive loop for judges |

---

## Key Design Decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Communication | bt.axon / bt.dendrite | Standard Bittensor pattern. NOT Docker HTTP. |
| SQL engine | DuckDB (in-memory, read-only) | Fast, portable, no server needed, sandboxed |
| Data format | Parquet | Columnar, fast, portable, deterministic |
| Hashing | SHA-256 of canonical result string | Deterministic, well-understood, collision-resistant |
| Scoring | 75/15/10 with hard correctness gate | Correctness dominates. Speed differentiates correct miners. |
| EMA α | 0.1 | Smooth — rewards consistency over single-round luck |
| Task mix | 30% easy / 50% medium / 20% hard | Floor for templates, ceiling requires intelligence |
| Hidden tasks | 20% of pool (50 tasks) | Prevents memorization without making it impossible to score |
| Miner SQL gen | Template-based (v1) | Simple, reliable baseline. LLM fallback in v2. |
| Config | argparse + bt.config | Standard Bittensor pattern |

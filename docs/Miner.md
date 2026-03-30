# Miner Guide

## Overview

QueryAgent miners receive natural language blockchain questions, generate SQL, execute it against a frozen DuckDB snapshot, and return the result hash to validators for verification.

```
Validator ──QuerySynapse──▶ Miner
                              │
                              ├── 1. Receive task_id + question
                              ├── 2. Generate SQL (template or LLM)
                              ├── 3. Execute SQL on DuckDB snapshot
                              ├── 4. SHA-256 hash the result
                              │
Validator ◀──Response──────── └── 5. Return: sql, result_hash, tables_used, explanation
```

## QuerySynapse Protocol

The wire format for all validator-miner communication:

**Request fields (validator → miner):**

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Unique task identifier (e.g. `QB-001`) |
| `snapshot_id` | `str` | Which frozen dataset to query (e.g. `bt_snapshot_test_v1`) |
| `question` | `str` | Natural language analytics question |
| `constraints` | `dict` | Optional parameters (time_window, k, netuid_filter) |

**Response fields (miner → validator):**

| Field | Type | Description |
|-------|------|-------------|
| `sql` | `str` | The SQL query the miner generated |
| `result_hash` | `str` | SHA-256 hash of the deterministic query result |
| `result_preview` | `dict` | First N rows of the result (columns + rows) |
| `tables_used` | `list[str]` | Which tables the SQL references |
| `explanation` | `str` | Short text explaining the query logic |

## Miner Types

### Template Miner (`miner_local.py`)

Maps `task_id` directly to pre-built SQL. Fast, deterministic, guaranteed hash match for known tasks.

```bash
python -m neurons.miner_local \
  --netuid 3 \
  --wallet.name miner_1 \
  --wallet.hotkey default \
  --subtensor.network ws://127.0.0.1:9944 \
  --axon.port 8091 \
  --skill strong
```

**Skill levels** control which task tiers the miner attempts:

| Skill | Easy | Medium | Hard | Best For |
|-------|------|--------|------|----------|
| `strong` | Yes | Yes | Yes | Maximum score, handles all tasks |
| `medium` | Yes | Yes | No | Skips hard CTEs/window functions |
| `weak` | Yes | No | No | Only simple aggregations |

If a miner receives a task outside its skill level, it returns no response (score = 0 for that round). This is by design — it's better to skip than to return a wrong hash.

### LLM Miner (`miner_llm.py`)

Uses OpenAI GPT-4o to generate SQL from natural language. Handles novel questions but costs per query and may produce non-matching SQL.

```bash
export OPENAI_API_KEY=sk-...
python -m neurons.miner_llm \
  --netuid 3 \
  --wallet.name miner_1 \
  --wallet.hotkey default \
  --subtensor.network test
```

### Reference Miner (`miner.py`)

Template-based miner for Bittensor testnet. Uses regex pattern matching against question text.

## Data Snapshot

Miners execute SQL against frozen Parquet snapshots loaded into DuckDB. The snapshot is read-only and sandboxed — no filesystem access, no writes.

**Available tables:**

| Table | Description | Rows (test snapshot) |
|-------|-------------|---------------------|
| `subnets` | Subnet configuration | 10 |
| `validators` | Validator metadata + stakes | 9 |
| `miners` | Miner metadata + incentives | 1,106 |
| `stakes` | Staking records | 490 |
| `emissions` | Emission records per subnet | 24 |
| `metagraph` | Merged view (all neurons) | 1,115 |

## Hash Determinism

The entire system depends on identical SQL producing identical hashes. DuckDB handles this via:

1. **Frozen data** — same Parquet files loaded into memory
2. **Canonical form** — floats rounded to 6 decimal places, NULLs as sentinel, booleans lowercase
3. **Row sorting** — all rows sorted lexicographically before hashing (ORDER BY in SQL isn't enough for ties)
4. **SHA-256** — `sha256:<hex_digest>` format

A miner that produces different SQL than the ground truth reference will get score = 0, even if the SQL is semantically correct, because the row ordering or column aliases may differ.

## Tips

1. **Start with the template miner** — guaranteed hash matches for all 20 known tasks
2. **Test locally first** — run `pytest tests/test_hashing.py` to verify determinism
3. **Check your SQL aliases** — `SUM(stake) AS total_staked` must match exactly
4. **Don't round unless the reference does** — extra `ROUND()` calls change the hash
5. **The axon port must be accessible** — validators connect via `bt.dendrite`

## Hardware

| Component | Requirement |
|-----------|-------------|
| CPU | 2+ cores |
| RAM | 4 GB |
| Storage | 2 GB |
| GPU | Not required |
| Network | Port accessible for axon |

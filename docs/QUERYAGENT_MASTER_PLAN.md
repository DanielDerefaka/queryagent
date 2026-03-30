# QueryAgent Subnet — Master Plan (Benchmark‑First)

**Last updated:** 2026-02-19  
**Status:** Planning → Ideathon submission + benchmark v0.1 build

---

## 1) TL;DR

**QueryAgent** is a Bittensor subnet where **miners compete to answer analytics questions** by submitting an **Answer Package**:

- Executable **SQL**
- **Result** (table preview + result hash)
- **Explanation** (plain English)
- **Provenance** (tables used + snapshot ID)

**Validators score miners by re-running the miner SQL on a canonical dataset snapshot** and comparing outputs to **ground truth** (stored as reference results/hashes). Miners earn rewards based on objective performance: **correctness first**, then **efficiency and latency**.

The benchmark (**QueryBench**) is the product.

---

## 2) Subnet Identity

### Name
**QueryAgent**

### One-liner
**“Verified agentic analytics: miners answer questions with executable SQL + reproducible results; validators verify by re-running queries on frozen snapshots.”**

### Short description
Blockchain data is hard to understand without analytics, and even “AI analytics” is hard to trust. QueryAgent turns analytics into a measurable market: miners produce verifiable answers, validators reproduce and score them.

---

## 3) What problem are we solving?

### The pain (what users experience today)
- Blockchain data is massive and messy: explorers show raw events, not insight.
- Analytics platforms help, but users still need:
  1) SQL skill  
  2) schema knowledge  
  3) time to debug queries  
  4) trust that dashboards/AI outputs are correct  
- Reproducibility is hard because data refreshes and table semantics evolve.

### What’s missing in the ecosystem
There is no open, benchmark-driven marketplace that objectively measures:
- **Which analytics agent is actually correct**
- **Which agent is robust under schema changes**
- **Which agent is fast/efficient enough for real use**

---

## 4) What product does the subnet give?

### The subnet’s product (the commodity)
**Verified analytics answers** in a standard, machine-readable format (**Answer Package**).

### Who can use it
- Dashboards and analytics apps (front-ends)
- Research bots and reporting tools
- Subnet teams and validators (subnet health, emissions, activity)
- Other subnets (as an analytics oracle)

### What we are NOT depending on (for Ideathon)
- We do **not** need a website.
- We do **not** need revenue.
- We do **not** need mainnet deployment.
We need a **strong benchmark + clear evaluation + miner/validator reference implementation**.

---

## 5) Core concept: Benchmark-first (Const’s framework)

A good subnet starts with:
1) **Benchmark** (what good means)
2) **Submission format** (what miners submit)
3) **Evaluation** (how validators score)
4) **Miner + Validator reference scripts**
5) Then: incentive curve tuning, UX, revenue, etc.

QueryAgent follows this exactly.

---

## 6) QueryBench — the Benchmark

### QueryBench components
**QueryBench = Dataset Snapshots + Tasks + Ground Truth**

#### A) Dataset snapshots
A snapshot is a **frozen version** of the dataset used for scoring.
- Example snapshot IDs: `bt_snapshot_2026_02_01_v1`, `bt_snapshot_2026_03_01_v1`
- Snapshots must be reproducible and loadable by validators deterministically.

**Recommended snapshot format:** Parquet (columnar, fast, portable)
- Stored as a bundle with:
  - `schema.json` (tables + columns + types)
  - `tables/*.parquet`
  - `metadata.json` (build time, source, row counts, checksums)

#### B) Tasks
Each task is:
- `task_id`
- `snapshot_id`
- `question` (plain English)
- `constraints` (time window, max rows, allowed tables)
- `ground_truth_hash` (and optionally expected table)

Task types for v0.1:
- Aggregations (sum, count, avg)
- Top‑k ranking
- Time window metrics (7d/30d deltas)
- Group-by breakdown (by day, by subnet)
- Joins (events + subnet metadata)

#### C) Ground truth
For each task:
- Reference SQL (maintainer-authored)
- Expected result hash (and optionally expected result table)
- Tolerances for float fields (if needed)

**Important:** We score **results**, not SQL strings.

---

## 7) Submission Format (Miner I/O)

### v1 submission type (recommended for simplicity and fairness)
**Miners run a Dockerized HTTP/RPC endpoint**.

**Why this format**
- Works with any language/framework inside Docker
- Easy for validators to query at scale
- Simple to evaluate and standardize

### Request schema (validator → miner)
```json
{
  "task_id": "QB-001",
  "snapshot_id": "bt_snapshot_2026_02_01_v1",
  "question": "Top 10 subnets by swap volume in the last 7 days",
  "constraints": {
    "max_rows": 50,
    "time_start": "2026-01-25",
    "time_end": "2026-02-01"
  }
}
```

### Response schema (miner → validator) — Answer Package
```json
{
  "task_id": "QB-001",
  "snapshot_id": "bt_snapshot_2026_02_01_v1",
  "sql": "SELECT ...",
  "result_preview": {
    "columns": ["netuid", "volume_tao"],
    "rows": [[18, 12345.67], [1, 9876.54]]
  },
  "tables_used": ["dex_swaps", "subnets"],
  "explanation": "Subnet 18 and 1 had the highest swap volume over the last 7 days.",
  "result_hash": "sha256:..."
}
```

**Rules**
- If miner cannot answer, it must return a structured error:
  - `error_code`, `message`, optional `clarifying_question` (Phase 2+)

---

## 8) Miner Design (what miners do)

### What miners optimize for
1) **Correctness** (must match ground truth)
2) **Efficiency** (run within query budgets)
3) **Latency** (respond quickly)

### Reference miner (baseline)
A baseline miner can be:
- Template-first SQL generator (a library of common query patterns)
- Optional LLM fallback when templates don’t match
- Optional “self-check” step: run SQL locally on snapshot to avoid obvious failures

### Required skills/hardware (v1)
- Skills: SQL, basic API server, Docker
- Hardware: modest CPU; memory depends on snapshot size (validator side matters more)

---

## 9) Validator Design (evaluation and scoring)

### Validator evaluation pipeline
1) Sample tasks from QueryBench
2) Send task to miner endpoint
3) Validate response schema
4) Run miner SQL on the snapshot locally (DuckDB/Postgres)
5) Compute result hash from execution output
6) Compare to ground truth hash
7) Compute score (correctness + efficiency + latency)
8) Convert scores to weights and submit weights

### Budgets (to prevent abuse)
- SQL execution timeout (e.g., 2–10 seconds per task for v1)
- Max rows returned
- Optional: reject queries that scan too much / exceed budget

---

## 10) Scoring + Calculations (clear and strict)

### A) Correctness (hard gate in Phase 1)
- Validator executes miner SQL → `result_hash_miner`
- Compare to `ground_truth_hash`

**Correctness:**
- `Correctness = 1` if match  
- `Correctness = 0` otherwise  
(Phase 1: no partial credit)

### B) Efficiency score (example)
- `Efficiency = max(0, 1 - runtime_ms / budget_ms)`

### C) Latency score (example)
- `Latency = max(0, 1 - response_ms / latency_budget_ms)`

### D) Overall score (Phase 1 baseline)
- If invalid JSON/SQL/schema mismatch → `Score = 0`
- Else:
  - If `Correctness = 0` → `Score = 0`
  - If `Correctness = 1`:
    - `Score = 0.75*Correctness + 0.15*Efficiency + 0.10*Latency`

> Correctness dominates. Efficiency and latency differentiate correct miners.

---

## 11) How scores become weights (incentive mechanism)

### Weight assignment (simple)
Let `score_i` be miner i score for the epoch:

- Proportional:
  - `weight_i = score_i / Σ(score)`

- More competitive (optional):
  - `weight_i = (score_i^p) / Σ(score^p)`
  - `p=2` rewards top miners more than p=1

**Why this is aligned**
Miners are rewarded for:
- reproducible correctness
- efficient queries (no waste)
- fast responses

---

## 12) Anti-gaming design (how we prevent cheating)

### Common attacks and defenses
1) **Memorization**
   - Hidden tasks (private eval set)
   - Parameterized tasks (random time windows, top‑k sizes)
2) **Bluffing results**
   - Validators re-run SQL; results are computed, not trusted
3) **DoS via expensive SQL**
   - Strict timeouts and budgets
   - Penalize cost/latency
   - Reject overly expensive plans
4) **Overfitting to one dataset**
   - Multiple snapshots over time
   - Periodic benchmark refreshes

---

## 13) Roadmap (4 phases)

### Phase 1 — Verified Text→SQL on canonical snapshots (MVP)
**Goal:** Prove the benchmark + evaluation loop.
- Build QueryBench v0.1 (snapshot + 200–500 tasks + ground truth)
- Reference miner + validator scripts
- Leaderboard emerges from correctness

### Phase 2 — Agentic repair + robustness
**Goal:** Make it truly agentic.
- Tasks with broken SQL / missing columns / ambiguous terms
- Miner must recover (fix + retry) or ask one clarifying question
- Add partial credit scoring for “almost correct” repairs

### Phase 3 — Multi-step analytics pipelines
**Goal:** Beyond one query.
- Output can include multi-step SQL plan + intermediate outputs
- Optional chart spec output
- Validators verify intermediate + final results

### Phase 4 — Interfaces + adoption (not required for Ideathon)
**Goal:** Make it easy to integrate.
- SDK + API gateway (optional)
- “Query packs” (prebuilt metrics)
- Dashboards/alerts built on verified answers

---

## 14) Deliverables (what we are planning to ship first)

### Ideathon deliverables (Round I)
- Clear benchmark definition (QueryBench)
- Submission format + schema
- Evaluation logic + scoring formula
- Miner/validator reference implementation plan
- 7-slide deck + roadmap (already created)
- Written “whitepaper-style” overview for judges

### Testnet deliverables (Round II readiness)
- Minimal working miner + validator on a test snapshot
- Deterministic evaluation harness
- Demonstration of weights updating from scores

---

## 15) Proposed repo structure (reference implementation)

```
queryagent/
  benchmark/
    snapshots/
      bt_snapshot_.../
        schema.json
        metadata.json
        tables/*.parquet
    tasks/
      tasks_v0_1.json
      ground_truth/
        QB-001.json (expected hash + ref SQL)
  validator/
    validator.py
    scoring.py
    snapshot_loader.py
    task_sampler.py
  miner/
    miner.py
    templates.py
    llm_adapter.py (optional)
    docker/Dockerfile
  docs/
    README.md
    SPEC.md
    CONTRIBUTING.md
```

---

## 16) Adoption plan (how people start using it)

### Day 1 integration targets
- A simple CLI tool that asks questions and prints verified results
- A Telegram/Discord bot for “subnet stats queries”
- Dashboard front-end that calls the top miners

### Why people will care
- Reproducible answers → less misinformation
- Lower barrier to analytics (no SQL required)
- Competition improves quality over time

---

## 17) Risks and mitigations

### Risk: dataset snapshot pipeline is hard
Mitigation:
- Start small (one snapshot, limited schema)
- Expand snapshot coverage after evaluation pipeline works

### Risk: expensive queries
Mitigation:
- strict budgets and timeouts
- penalize cost

### Risk: benchmark memorization
Mitigation:
- hidden tasks + parameterization + rotating snapshots

---

## 18) Glossary (simple)
- **Snapshot:** Frozen dataset version used for scoring.
- **Task:** A question + constraints tied to a snapshot.
- **Ground truth:** Expected result for a task on a snapshot.
- **Answer Package:** Miner’s output (SQL + result + explanation + provenance).
- **Validator:** Runs SQL and scores miners.
- **Weight:** How validators allocate rewards based on performance.

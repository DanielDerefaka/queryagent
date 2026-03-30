# QueryAgent — Full Product & Subnet Architecture

> The verified Bittensor intelligence platform. Ask any Bittensor question in plain English. Get a verified AI answer with cryptographic proof.

**Version:** 2.0 — Post-Investor Feedback  
**Date:** March 2026  
**Team:** @danielderedev · @_KaWisLeo · @KarisOkey  
**Status:** Bittensor Subnet Ideathon — Round II (Testnet Phase)

---

## Table of Contents

1. [What Is QueryAgent](#1-what-is-queryagent)
2. [The Product — What We Are Building](#2-the-product)
3. [The Subnet Architecture](#3-the-subnet-architecture)
4. [Lessons From Top Subnets](#4-lessons-from-top-subnets)
5. [Development Phases](#5-development-phases)
6. [Technology Stack](#6-technology-stack)
7. [Competitive Positioning](#7-competitive-positioning)
8. [Anti-Gaming Measures](#8-anti-gaming-measures)
9. [The Investor Story](#9-the-investor-story)
10. [Team](#10-team)

---

## 1. What Is QueryAgent

**One sentence:** QueryAgent is the verified Bittensor intelligence platform — a place where anyone can ask questions about the Bittensor ecosystem in plain English, get AI-powered answers with cryptographic proof, and explore live dashboards without writing a single line of SQL.

### The Problem We Are Solving

When you first join Bittensor you are immediately overwhelmed. Which subnet should I stake to? Which miners are actually earning? What is happening on-chain right now? There is no simple, trustworthy place to find those answers.

- Taostats is a technical dashboard, not an intelligence tool
- Bittensor docs are written for developers
- Discord gives you 20 different opinions and no proof any of them are correct
- Nobody has built the tool that a newcomer actually needs

QueryAgent is that tool. It is the intelligence layer for the Bittensor ecosystem — built on top of Bittensor itself.

### Who We Are Building For

**Primary user:** A newcomer to Bittensor. Someone who just bought TAO, wants to understand the ecosystem, and is completely lost. They cannot read raw chain data. They do not know SQL. They just want straight answers.

**Secondary users:**
- Miners and validators checking their own performance
- Investors tracking subnet economics
- Developers who want a clean API for on-chain Bittensor data

### What We Learned From Investors

After our first investor meeting we received honest feedback that sharpened the product:

- The idea was not presented as scalable — we need a clear path to a large user base
- Too many third-party API dependencies — we need to own our stack
- The miner/validator logic was not the exciting part — the product needs to be the exciting part
- We could not answer our burn rate — we now know: **$10/month ($5 VPS + $5 OpenAI API)**

These were fair. They pushed us to get much clearer on what the product actually is, who it is for, and how the subnet powers it rather than being the product itself.

---

## 2. The Product

QueryAgent has four product surfaces, all powered by the same underlying data and AI layer.

### 2.1 AI Chat

The flagship feature. Users type any Bittensor question in plain English and receive an immediate, accurate, AI-generated answer. No SQL. No technical knowledge required.

**Example questions users ask:**
- Which subnet has the most active miners right now?
- What is the best validator to stake to for maximum returns?
- How much TAO did subnet 64 earn in emissions this week?
- Which hotkey holds the most alpha tokens?
- What is my validator's current vtrust score?

The AI gives a direct answer with a chart or table if needed, plus a **verification badge** showing the data source and proof hash. Every answer is grounded in real on-chain data, not hallucinated.

### 2.2 Auto-Generated Dashboards

Users can save any query result as a dashboard widget. Multiple widgets combine into a personal dashboard. The dashboard updates automatically on a schedule.

How it works: you ask the chat a question, it gives you a table, you click **Save to Dashboard**. Over time you build a live view of everything you care about in Bittensor — your miner performance, your subnet's emissions, the validators you are staked to.

No dashboard builder needed. No drag and drop. The AI generates it from natural language. This is the key differentiator from Dune Analytics, where you need SQL to build anything.

### 2.3 SQL Query Editor

For power users — developers, researchers, analysts — who want to write their own queries against live Bittensor chain data. Full SQL editor with syntax highlighting, autocomplete, and result visualization.

This is the Dune Analytics layer for Bittensor experts. Power users can write their own query, fork it, and share it with the community.

### 2.4 Scheduled Reports and Alerts

Users can schedule any query or chat question to run daily, weekly, or on a custom schedule. Results are delivered in-app, via email, or via webhook.

**Examples:**
- Daily: What is my validator's current vtrust score?
- Weekly: Which subnets gained the most emissions share this week?
- Alert: Notify me when subnet 64 drops below 10% emissions share

This is the feature that turns QueryAgent from a tool you visit once into a service you depend on.

---

## 3. The Subnet Architecture

This is the most important conceptual upgrade from our original design. We learned from studying the best Bittensor subnets — Chutes, Ridges AI, Macrocosmos, BitMind, Zeus — that **the subnet is not the product. The subnet is the engine that powers the product.**

### 3.1 The Core Insight

> Miners and validators compete to produce high-quality Bittensor analytics answers. Their competition generates a growing dataset of verified question-answer pairs. That dataset trains the AI agent that powers the consumer product. The product gets smarter every day because miners keep competing.

This is the same architecture Macrocosmos uses across SN1, SN9, SN13, and SN37 — where each subnet's miner outputs become training data for the next layer. It is live and operational in the Bittensor ecosystem today.

### 3.2 The Three Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — SUBNET (Incentive Layer)                             │
│  Miners compete to answer Bittensor analytics questions         │
│  Validators verify answers via SHA-256 hash comparison          │
│  Yuma Consensus distributes TAO emissions to winning miners     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ Verified Q&A pairs flow down
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — DATA PIPELINE (Training Layer)                       │
│  All scored miner responses accumulate into training dataset    │
│  High-quality answers (score > 0.80) labelled as positives      │
│  Real user questions fed back up to miners as organic tasks     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ Fine-tuned AI model deployed
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — PRODUCT (Consumer Layer)                             │
│  AI Chat · Auto-Dashboards · SQL Editor · Scheduled Reports     │
│  Users never touch Bittensor — they use a polished SaaS tool   │
│  Product revenue flows back into alpha token buybacks           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 How Miners Work

**Input:** A natural language Bittensor analytics question, optionally with a chain filter and time window.

**Task:** Generate valid SQL for the Bittensor snapshot schema, execute it in DuckDB, return result + hash + explanation.

| Miner Type | Description | Benchmark Score |
|---|---|---|
| Template Miner | 15 regex → SQL patterns. Fast, free, deterministic. | 12/20 tasks |
| LLM Miner | GPT-4o with Bittensor schema context and few-shot examples. | 9-10/20 tasks |
| Hybrid Miner | Template first, LLM fallback. Best of both worlds. | 12/20 (0 unmatched) |

**Output fields:**
```python
class QuerySynapse(bt.Synapse):
    # Request (validator → miner)
    task_id: str                          # e.g. "QB-001"
    snapshot_id: str                      # e.g. "bt_snapshot_test_v1"
    question: str                         # Natural language question
    constraints: Optional[dict] = None   # {k, netuid_filter, time_window}

    # Response (miner → validator)
    sql: Optional[str] = None
    result_hash: Optional[str] = None    # "sha256:<hex>"
    result_preview: Optional[dict] = None
    tables_used: Optional[List[str]] = None
    explanation: Optional[str] = None
```

### 3.4 How Validators Work

| Step | What Happens |
|---|---|
| 1. Sample task | Pick from task pool — 30% easy, 50% medium, 20% hard |
| 2. Broadcast | Send QuerySynapse to all miners via bt.Dendrite, 30s timeout |
| 3. Re-execute | Run each miner's SQL on validator's own DuckDB instance |
| 4. Hash comparison | Compute SHA-256, compare to ground truth. Match = correct. |
| 5. Score | 0.75 × correctness + 0.15 × efficiency + 0.10 × latency |
| 6. EMA smoothing | Update scores with alpha=0.1 to prevent single-round manipulation |
| 7. Set weights | Call subtensor.set_weights() on-chain every ~100 blocks |
| 8. Log training data | Save high-quality responses to training dataset |

### 3.5 Scoring Formula

```python
def compute_score(correct: bool, exec_ms, budget_ms, response_ms, latency_ms) -> float:
    if not correct:
        return 0.0  # Hard gate — wrong hash = zero, no exceptions
    efficiency = max(0.0, 1 - exec_ms / budget_ms)
    latency = max(0.0, 1 - response_ms / latency_ms)
    return 0.75 + 0.15 * efficiency + 0.10 * latency
    # Range for correct answers: [0.75, 1.0]
```

**EMA smoothing:**
```python
scores = alpha * new_scores + (1 - alpha) * scores  # alpha = 0.1
```

### 3.6 Why Hash-Based Verification Is The Right Choice

Most subnets use model-based scoring — comparing miner outputs against a reference model. This is expensive, subjective, and gameable. Our approach is fundamentally different:

- Two nodes executing identical SQL on identical frozen data always produce identical bytes
- SHA-256 of that output is deterministic — no subjectivity, no approximation
- Wrong hash = exactly 0.0. No partial credit. You cannot fake correctness.
- Validators are computationally cheap to run — DuckDB executes in milliseconds
- No trust required between miner and validator — the math proves it

### 3.7 The Snapshot System

**Current snapshot:** `bt_snapshot_test_v1`  
**Source:** Bittensor testnet (block 6655193)  
**Format:** Apache Parquet → loaded into in-memory DuckDB  
**Tables:** 6 total

| Table | Rows | Description |
|---|---|---|
| subnets | 10 | Subnet metadata, hyperparameters |
| validators | 9 | Validator UIDs, stake, vtrust, dividends |
| miners | 1,106 | Miner UIDs, incentive, stake |
| stakes | 490 | Stake relationships |
| emissions | 24 | Emission amounts per neuron |
| metagraph | — | Full metagraph snapshot |

**Rotation plan:** Every 4-6 hours for recent data. Daily/weekly for historical archives. Each snapshot tagged with block height cutoff and SHA-256 checksum in a manifest file.

### 3.8 Deterministic Hashing — The Technical Details

```python
def hash_result(conn, sql) -> str:
    # 1. Execute SQL in DuckDB
    # 2. Canonicalize each value:
    #    - Floats → 6 decimal places
    #    - None → "\x00NULL\x00"  (prevents NULL/"NULL" collision)
    #    - Bool → lowercase string
    # 3. Sort rows lexicographically (order-independent)
    # 4. Build canonical string: header + sorted rows (pipe-delimited)
    # 5. SHA-256 hash → return "sha256:<hex>"
```

**Guarantees:**
- Same SQL + same snapshot = same hash, always
- Row order independent
- Float precision fixed to 6 decimals
- NULL vs "NULL" distinguished by sentinel `\x00NULL\x00`
- Thread-safe (read-only operations)

### 3.9 The Training Data Pipeline

Every scored miner interaction produces a training example:

```json
{
  "question": "Which subnet has the highest total stake?",
  "sql": "SELECT netuid, SUM(stake) as total FROM stakes GROUP BY netuid ORDER BY total DESC LIMIT 1",
  "answer": {"netuid": 64, "total": 128453.21},
  "score": 0.998,
  "miner_uid": 2,
  "block": 6816,
  "snapshot_id": "bt_snapshot_test_v1",
  "label": "positive"
}
```

**Quality threshold:** Responses scoring above 0.80 are labelled positive. Below 0.50 are labelled negative. Between 0.50 and 0.80 are filtered out (ambiguous quality).

**Feedback loop:** Questions asked by real users on the product are injected back into the miner task pool as organic queries, ensuring training data matches real demand.

### 3.10 On-Chain Results (Testnet Proof)

```
UID 0 (subnet owner):  stake=3,776 β  | incentive=0.000 | dividends=0.000
UID 1 (validator):     stake=1,144 β  | incentive=0.000 | dividends=1.000 | vtrust=1.000
UID 2 (miner):         stake=103+  β  | incentive=1.000 | dividends=0.000
```

**Miner stake growth during live run:**
```
03:51:35 | UID=2 | stake=0.0000  | incentive=0.000
04:01:10 | UID=2 | stake=67.650  | incentive=1.000
04:01:31 | UID=2 | stake=76.670  | incentive=1.000
04:02:20 | UID=2 | stake=103.730 | incentive=1.000
```

---

## 4. Lessons From Top Subnets

Before redesigning QueryAgent we studied eight of the top Bittensor subnets. Here is what we learned.

### 4.1 Chutes (SN64) — Validator IS The Product

Chutes processes 3 trillion tokens/month. It holds 14% of all Bittensor emissions. It has 400,000+ API users, most of whom do not know they are using Bittensor.

**The key insight:** The Chutes validator and chutes.ai product are the same system. Every real user API call is simultaneously a miner scoring event. Miners cannot game synthetic benchmarks separately from production because benchmarks ARE production.

**Lesson for QueryAgent:** Eventually, real user questions on our product should flow back to miners as organic tasks. The more real users we have, the richer and more diverse the training data becomes.

### 4.2 Ridges AI (SN62) — Miners As R&D, Product As Deployment

Ridges miners submit Python agent files. Validators score them on SWE-bench coding benchmarks. The winning agents are deployed into a separate VS Code extension product. Users pay $12/month and never touch Bittensor.

Ridges achieved **96.3% on Python coding benchmarks** — beating centralised systems — because decentralised competition drives quality faster than any single team can.

**Lesson for QueryAgent:** Our miners competing on Bittensor analytics questions will produce better SQL and better answers over time, exactly like Ridges agents improved on coding tasks. The training data they generate becomes our moat.

### 4.3 Macrocosmos Pipeline (SN1/SN9/SN13/SN37) — Miner Outputs As Training Data

Macrocosmos runs four interconnected subnets where each subnet's output becomes training input for the next:

```
SN13 scrapes 55B rows of social data
    → SN9 pre-trains models on that data
    → SN37 fine-tunes using SN1's agentic outputs
    → SN1 serves users with fine-tuned models
    → SN1's outputs become new training data for SN37
    → cycle repeats, quality floor rises every iteration
```

**Lesson for QueryAgent:** This is our exact architecture. Miner competition generates training data. Training data improves the AI. Better AI serves users better. More users generate more organic training data.

### 4.4 BitMind (SN34) — Adversarial Competition Drives Quality

BitMind has two types of miners: detectors (classify images as real or fake) and generators (create adversarial fakes to fool the detectors). They compete against each other. Chrome extension does 150,000+ weekly detections. App is live. Enterprise API earns real revenue.

**Lesson for QueryAgent:** As miners improve at answering questions, we should escalate difficulty — harder queries, less common data patterns, more complex joins. Continuous difficulty escalation prevents stagnation.

### 4.5 Zeus (SN18) — Score On Difficulty, Not Just Correctness

Zeus weather forecasting miners get higher scores for forecasting difficult regions (mountains, volatile weather) than easy regions (stable ocean). This prevents miners from gaming easy tasks.

**Lesson for QueryAgent:** Hard tier queries (20% of tasks) should carry disproportionately higher reward. Simple aggregations earn less than complex multi-join window function queries.

### 4.6 Architecture Pattern Summary

| Pattern | Source | Applied To QueryAgent |
|---|---|---|
| Validator IS the API gateway | Chutes, Nineteen | Validators serve as bridge between subnet and product layer |
| Miner outputs → training data | Macrocosmos | Scored Q&A pairs fine-tune the product AI continuously |
| R&D competition → product deployment | Ridges AI | Best miner answers power the chat/dashboard product |
| Adversarial difficulty escalation | BitMind | Hard tasks escalate as miners improve |
| Difficulty-adjusted scoring | Zeus | Hard queries earn more emissions than easy ones |
| Score on real utility | Chutes | Eventually, real user queries become miner tasks |

---

## 5. Development Phases

### Phase 1 — Hackathon Submission (Now → March 31)

Focus: Prove the subnet works on-chain. Win the ideathon.

- [ ] Local chain running with miner and validator neurons registered
- [ ] Full incentive loop: miner earns TAO, validator sets weights, Yuma Consensus distributes emissions
- [ ] Template miner scoring 12/20, LLM miner handling the remaining 8
- [ ] Demo video: plain English question → SQL → verified result → TAO earned
- [ ] README documenting the full subnet setup
- [ ] Update pitch to lead with the product story, not the subnet mechanics

### Phase 2 — Product MVP (April → June)

Focus: Build the consumer product. Get 10 real users.

- [ ] AI Chat interface — users type Bittensor questions, get instant AI answers
- [ ] Auto-dashboard builder — save any chat result as a dashboard widget
- [ ] Live Bittensor data pipeline — snapshot rotation every 4-6 hours
- [ ] Training data pipeline — all validator-scored miner responses feed into dataset
- [ ] Initial AI agent fine-tuned on first 1,000 verified Q&A pairs from subnet
- [ ] Beta launch with 10 Bittensor newcomers from Discord/Telegram
- [ ] Public API key system for developers

### Phase 3 — Revenue and Scale (July → September)

Focus: Generate real external revenue. Create the flywheel.

- [ ] SQL Query Editor for power users
- [ ] Scheduled reports and alert system
- [ ] Public API for developers (pay-per-query pricing)
- [ ] Revenue from API fees flows into subnet alpha token buybacks
- [ ] Organic user questions fed back into subnet as miner tasks
- [ ] Multi-chain expansion beyond Bittensor

---

## 6. Technology Stack

### Subnet Layer

| Component | Technology |
|---|---|
| Blockchain | Bittensor (Subtensor v10 API — bt.Subtensor, bt.Dendrite, bt.Axon, bt.Metagraph) |
| Wire protocol | QuerySynapse — custom bt.Synapse subclass |
| Data storage | Apache Parquet → in-memory DuckDB (no external DB) |
| Snapshot source | Bittensor chain — 6 tables (subnets, validators, miners, stakes, emissions, metagraph) |
| Hashing | SHA-256, sorted rows, 6dp float precision, NULL sentinel |
| Scoring | 75% correctness + 15% efficiency + 10% latency, EMA alpha=0.1 |
| Template miner | 15 regex → SQL patterns, Python 3.11 |
| LLM miner | GPT-4o with schema context and few-shot examples, hybrid strategy |
| Language | Python 3.11 |
| Tests | 124+ tests across 11 files (unit, adversarial ×60, determinism, wire, e2e) |

### Product Layer

| Component | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Database / realtime | Convex (reactive queries, optimistic UI) |
| Styling | Tailwind CSS — dark-mode first, Inter font, cyan-blue brand accent (#06B6D4) |
| AI agent | Fine-tuned model served via FastAPI, trained on subnet miner dataset |
| SQL editor | Monaco Editor (lazy-loaded on /query route only) |
| Charts | Recharts / Tremor for standard, Apache ECharts for heavy visualizations |
| Data tables | TanStack Table v8 (sort, filter, pagination, column resize) |
| Animations | Framer Motion v12 |
| Auth | Clerk |
| API backend | FastAPI — connects product to subnet data pipeline |

### Workspace Layout

```
subnet_dx/
├── queryagent/           # Core library
│   ├── protocol.py       # QuerySynapse wire protocol
│   ├── config.py         # All tunable parameters
│   ├── hashing.py        # Deterministic SHA-256 hashing
│   ├── scoring.py        # 75/15/10 scoring + EMA + normalization
│   ├── snapshot.py       # Parquet → DuckDB loader + SQL safety
│   └── tasks.py          # Task pool, sampling, parameter injection
│
├── neurons/
│   ├── miner.py          # Template miner (15 regex patterns)
│   ├── miner_llm.py      # LLM miner (GPT-4o) + hybrid strategy
│   └── validator.py      # Full verify-score-set_weights loop
│
├── tests/                # 124+ tests across 11 files
├── scripts/
│   ├── build_snapshot.py # Chain → Parquet tables
│   └── generate_tasks.py # Tasks + ground truth hashes
│
├── benchmark/
│   ├── tasks/
│   │   ├── public_tasks.json   # 16 public tasks
│   │   └── hidden_tasks.json   # 4 hidden tasks (anti-gaming)
│   └── snapshots/bt_snapshot_test_v1/
│       ├── schema.json
│       ├── metadata.json
│       └── tables/             # 6 Parquet files
│
└── [product — to be built in Phase 2]
    ├── app/              # Next.js 15 App Router
    ├── convex/           # Database schema and queries
    ├── components/       # UI components
    └── api/              # FastAPI backend
```

### Burn Rate

**Current:** $10/month total ($5 VPS + $5 OpenAI API)  
The main product is not yet live. No third-party API costs at scale yet.

---

## 7. Competitive Positioning

The blockchain analytics market is proven and funded. Dune Analytics raised $69M and has 1M+ users. Nansen charges $99–$999/month. Flipside Crypto just abandoned SQL entirely for AI chat. None of them are built for Bittensor specifically, and none of them can prove their data is unmodified.

| Feature | QueryAgent | Dune Analytics | Nansen | Flipside |
|---|---|---|---|---|
| Plain English queries | ✅ Core feature | ❌ Requires SQL | ❌ Pre-built only | ✅ But centralised |
| Cryptographic proof | ✅ SHA-256 with every answer | ❌ None | ❌ None | ❌ None |
| Bittensor-specific | ✅ Built for Bittensor | ❌ Generic multi-chain | ❌ Afterthought | ❌ Afterthought |
| Decentralised | ✅ Miner network | ❌ Single company | ❌ Single company | ❌ Single company |
| Self-improving AI | ✅ Miners train the model | ❌ Static | ❌ Static | ❌ Static |
| Free tier | ✅ Planned | Limited | ❌ $99/month min | ❌ Credits |
| SQL editor | ✅ Power users | ✅ Primary interface | ❌ Not available | ❌ Retired |
| Auto-dashboards | ✅ From chat | ❌ Manual build | ❌ Pre-built only | ❌ None |
| Scheduled reports | ✅ Built-in | 💰 Paid only | 💰 Paid only | ❌ None |

---

## 8. Anti-Gaming Measures

A subnet is only as good as its resistance to exploitation. QueryAgent has seven layers:

1. **Hidden tasks** — 4 of 20 benchmark tasks (20%) never published. Only validators know them. Miners who memorize public tasks still fail on hidden ones.

2. **Parameter injection** — `k`, `time_window`, and `netuid_filter` are randomized per query. Even if a miner memorizes a query template, the specific parameters change every time.

3. **Monthly snapshot rotation** — new frozen dataset every month prevents lookup-table attacks on historical data.

4. **DuckDB sandboxing** — `CREATE`, `DROP`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `COPY`, `EXPORT` all blocked. Miners cannot modify the database.

5. **Hard gate scoring** — wrong hash = exactly `0.0`. No partial credit for speed or confidence. You cannot game your way to a passing score.

6. **Deregistration pressure** — Yuma Consensus removes consistently poor performers. Bad miners lose their registration slot.

7. **Deterministic hashing** — SHA-256 collision resistance means you cannot fake a correct hash without actually computing the right answer.

---

## 9. The Investor Story

### The Pitch in Three Sentences

I built QueryAgent because I was that confused newcomer. When I joined Bittensor, I had no idea what was happening on-chain. There was no simple, trustworthy tool for normal people — so I built one, and I made it run on Bittensor itself so the answers are cryptographically verified.

### The Problem

- 100,000+ wallets on Bittensor. Most owners have no idea how to evaluate subnets, validators, or miners.
- Existing tools like Taostats are technical dashboards, not intelligence platforms.
- No tool answers plain English questions with verified data.

### The Solution

- QueryAgent: ask any Bittensor question in plain English, get a verified AI answer with cryptographic proof.
- Four products: AI Chat, Auto-Dashboards, SQL Editor, Scheduled Reports.
- Powered by a Bittensor subnet where miners compete to produce correct analytics — and their competition continuously trains the product AI.

### The Traction

- Honorable mention out of 150+ submissions — Bittensor Subnet Ideathon Round II
- Fully running on-chain: miner stake grew from 0 to 103+ TAO in minutes
- 124+ tests all passing: unit, adversarial, determinism, wire, end-to-end
- $10/month burn rate

### The Market

- Dune Analytics: $69M raised, 1M+ users, proven demand for blockchain analytics
- Bittensor: 100K+ wallets, growing 50% in subnets per year, no dedicated analytics product
- Category-defining opportunity: the intelligence layer for decentralised AI

### The Flywheel

```
More users ask questions
    → more organic tasks for miners
    → richer training data
    → smarter AI
    → better answers
    → more users

Better miner quality
    → more TAO emissions
    → more miners competing
    → more training data
    → better AI

Product revenue
    → alpha token buybacks
    → higher subnet emissions
    → more attractive to miners
```

---

## 10. Team

| Name | Role |
|---|---|
| Daniel Derefaka (@danielderedev) | Lead — blockchain security researcher, bug bounty hunter (Immunefi, Code4rena, Sherlock), Bittensor miner, Computer Science final year (Rivers State University) |
| @_KaWisLeo | Co-founder |
| @KarisOkey | Co-founder |

### Open Positions

QueryAgent is actively looking for contributors who share the vision:

- Bittensor subnet developer (Python, DuckDB, Bittensor SDK v10)
- Frontend developer (Next.js 16, Tailwind, Convex)
- ML engineer (fine-tuning, RLHF, dataset curation)

Reach out to @danielderedev on X.

---

## Key Config Reference

```python
# queryagent/config.py
CORRECTNESS_WEIGHT = 0.75
EFFICIENCY_WEIGHT  = 0.15
LATENCY_WEIGHT     = 0.10
EMA_ALPHA          = 0.1
EASY_SHARE         = 0.30
MEDIUM_SHARE       = 0.50
HARD_SHARE         = 0.20
HIDDEN_RATIO       = 0.20
FLOAT_PRECISION    = 6
NULL_REPR          = "\x00NULL\x00"
DEFAULT_TIMEOUT_S  = 30
DEFAULT_BUDGET_MS  = 5000
```

## Quick Start (Subnet)

```bash
# Install
pip install -r requirements.txt

# Build snapshot from Bittensor chain
python scripts/build_snapshot.py --network test --output benchmark/snapshots/bt_snapshot_test_v1

# Generate tasks + ground truth hashes
python scripts/generate_tasks.py --snapshot bt_snapshot_test_v1

# Run all tests
PYTHONPATH=. python3.11 -m pytest tests/ -v

# Run template miner
python -m neurons.miner \
  --wallet.name qa-miner \
  --wallet.hotkey default \
  --netuid 2 \
  --axon.port 8901 \
  --subtensor.network local

# Run LLM miner (requires OPENAI_API_KEY)
OPENAI_API_KEY=sk-... python -m neurons.miner_llm \
  --wallet.name qa-miner \
  --wallet.hotkey default \
  --netuid 2 \
  --subtensor.network local

# Run validator
python -m neurons.validator \
  --wallet.name qa-validator \
  --wallet.hotkey default \
  --netuid 2 \
  --subtensor.network local

# Check emissions
btcli subnet show --netuid 2 --network ws://127.0.0.1:9944
```

## Local Chain Setup (Full Command Sequence)

```bash
# 1. Pull and run local chain
docker pull ghcr.io/opentensor/subtensor-localnet:devnet-ready
docker run --rm --name local_chain -p 9944:9944 -p 9945:9945 -d \
  ghcr.io/opentensor/subtensor-localnet:devnet-ready

# 2. Create wallets
btcli wallet create --wallet.name alice --hotkey default --uri alice --no-use-password
btcli wallet create --wallet.name qa-owner --hotkey default --no-use-password
btcli wallet create --wallet.name qa-validator --hotkey default --no-use-password
btcli wallet create --wallet.name qa-miner --hotkey default --no-use-password

# 3. Fund from Alice
btcli wallet transfer --wallet.name alice --destination <QA_OWNER_ADDR> --amount 1100 --network ws://127.0.0.1:9944
btcli wallet transfer --wallet.name alice --destination <QA_VALIDATOR_ADDR> --amount 200 --network ws://127.0.0.1:9944
btcli wallet transfer --wallet.name alice --destination <QA_MINER_ADDR> --amount 10 --network ws://127.0.0.1:9944

# 4. Create and start subnet
btcli subnet create --subnet-name queryagent --wallet.name qa-owner \
  --wallet.hotkey default --network ws://127.0.0.1:9944 --no-mev-protection
btcli subnet start --netuid 2 --wallet.name qa-owner --network ws://127.0.0.1:9944

# 5. Register neurons
btcli subnets register --netuid 2 --wallet-name qa-validator --hotkey default --network ws://127.0.0.1:9944
btcli subnets register --netuid 2 --wallet-name qa-miner --hotkey default --network ws://127.0.0.1:9944

# 6. Stake for validator permit
btcli stake add --netuid 2 --wallet-name qa-validator --hotkey default \
  --amount 100 --network ws://127.0.0.1:9944 --no-mev-protection --tolerance 1.0 --partial

# 7. Disable commit-reveal (required for direct set_weights)
btcli sudo set --param commit_reveal_weights_enabled --value False \
  --netuid 2 --wallet.name qa-owner --network ws://127.0.0.1:9944

# 8. Run miner (Terminal 1)
PYTHONPATH=. python3.11 neurons/miner.py \
  --wallet.name qa-miner --wallet.hotkey default \
  --netuid 2 --axon.port 8901 --subtensor.network local

# 9. Run validator (Terminal 2)
PYTHONPATH=. python3.11 neurons/validator.py \
  --wallet.name qa-validator --wallet.hotkey default \
  --netuid 2 --subtensor.network local

# 10. Verify emissions
btcli subnet show --netuid 2 --network ws://127.0.0.1:9944
```

---

*QueryAgent — The verified Bittensor intelligence platform*  
*github.com/queryagent · @danielderedev · Bittensor Subnet Ideathon Round II*
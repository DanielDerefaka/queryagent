# QueryAgent — Investor Breakdown

*A simple, no-BS explanation of what we're building, how it works, and why it matters.*

---

## What is QueryAgent?

**QueryAgent lets anyone ask blockchain questions in plain English and get verified, provable answers.**

Think of it like Google for blockchain data — but instead of one company running the search engine, a decentralized network of computers competes to give you the best answer. Every answer is mathematically verified so you know it's correct.

**Example:**
- You ask: *"Which Bittensor subnet had the highest emissions last week?"*
- Behind the scenes, dozens of machines race to translate your question into a database query, run it, and return the answer
- A separate set of machines independently verify the answer is correct
- You get: **"SN64 (Chutes) — 518.4 TAO"** with a proof anyone can check

No SQL knowledge needed. No trusting a single company. Provably correct answers.

---

## The Market Problem

Blockchain data is public, but accessing it is hard:

| Platform | Problem |
|----------|---------|
| **Dune Analytics** | Requires SQL knowledge. 95% of crypto users can't write SQL. Free tier queries time out constantly. |
| **Nansen** | Pre-built dashboards only. $99-$999/month. No custom queries. |
| **Flipside Crypto** | Shut down their SQL studio in 2025. Pivoted to AI but lost power users. |
| **Etherscan / Block explorers** | One transaction at a time. No analytics. No aggregation. |

**The gap:** There's no tool that lets a normal person ask a blockchain question in plain English and get a verified, correct answer. Dune has 1,500+ paying customers and processes 3+ petabytes of data — but it only serves people who can write SQL.

---

## How It Works (The Simple Version)

QueryAgent runs on **Bittensor**, a decentralized AI network. Think of Bittensor as the "AWS of AI" — but instead of Amazon running the servers, independent operators run them and get paid based on how well they perform.

There are three roles:

### 1. Miners (The Workers)
Miners are computers that answer questions. When a question comes in, they:
1. Take the plain-English question
2. Convert it into a SQL database query (using AI or templates)
3. Run the query on a local copy of the blockchain data
4. Return the answer + a cryptographic hash (a fingerprint of the answer)

**Think of miners like Uber drivers** — anyone can become one, they compete for work, and the best performers earn the most.

### 2. Validators (The Quality Checkers)
Validators make sure miners aren't lying. They:
1. Take the same question
2. Run the SQL independently on their own copy of the data
3. Compare their hash (fingerprint) to what the miner returned
4. If the hashes match → the answer is provably correct
5. Score the miner and report scores to the blockchain

**Think of validators like restaurant health inspectors** — they independently verify quality and publish ratings.

### 3. The Network (Bittensor Blockchain)
The blockchain handles payments and reputation:
- Miners who consistently give correct, fast answers earn TAO (Bittensor's cryptocurrency)
- Miners who give wrong answers earn nothing
- Over time, bad miners get kicked out and good miners accumulate reputation
- All scores and payments are transparent and on-chain

---

## The Scoring System

Every miner answer is scored on three things:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| **Correctness** | 75% | Hash match — the answer is provably right or wrong. No grey area. |
| **Efficiency** | 15% | How lean is the SQL query? Less compute = better. |
| **Latency** | 10% | How fast did the miner respond? |

This creates a simple competitive dynamic:
- First, get the answer right (or you earn nothing)
- Then, optimize your query to be faster and more efficient
- The best miners earn the most TAO

Scores are smoothed over time using an **EMA (Exponential Moving Average)** — so one bad response doesn't destroy a good miner's reputation, but consistently bad miners drop off.

---

## Why Hash-Based Verification Matters

This is our key technical insight and what makes QueryAgent different from most AI subnets.

**The problem with most AI scoring:** If you ask an AI to write an essay, how do you score it? You need another AI to judge it — and that judge can be gamed. It's subjective.

**QueryAgent's approach:** Database queries are deterministic. Same data + same query = same answer, every time. So we:

1. Give every participant the exact same data snapshot (a frozen copy of blockchain data)
2. Everyone runs queries on their local copy using DuckDB (a fast database engine)
3. Same input → same output → same hash

If a miner's hash matches the validator's hash, the answer is **provably correct**. No AI judges. No subjectivity. No gaming.

**This is why investors in Bittensor subnets should care:** Most subnets struggle with miners gaming the scoring system. Our hash-based approach makes cheating harder than just doing the actual work — which is the gold standard for Bittensor subnet design.

---

## The Technology Stack

```
User's Question (Plain English)
        ↓
   API Gateway (FastAPI)
        ↓
   Validator picks up the question
        ↓
   Broadcasts to all registered Miners via Bittensor Axon/Dendrite
        ↓
   Miners generate SQL (LLM-powered or template-based)
        ↓
   Miners execute SQL on frozen Parquet snapshots via DuckDB
        ↓
   Miners return: SQL query + result hash + execution time + explanation
        ↓
   Validator re-executes SQL on same snapshot
        ↓
   Hash comparison → Score → Weights set on-chain
        ↓
   Best answer returned to user with verification proof
```

**Key tech choices:**
- **DuckDB** — blazing fast analytical database, handles 2TB+ datasets, ~2.5GB peak memory
- **Parquet files** — columnar storage format, compressed, partitioned by chain and date
- **Bittensor v10 SDK** — `bt.Axon` for miners, `bt.Dendrite` for validators, `bt.Metagraph` for network state
- **OpenAI GPT-4o** — powers the LLM miner's SQL generation (hybrid: templates first, LLM fallback)

---

## What We've Built So Far

### Testnet Results (Live Demo Available)

We deployed on a local Bittensor chain and achieved:

| Metric | Result |
|--------|--------|
| **Miner incentive** | 1.0 (maximum score) |
| **Validator trust** | 1.0 (maximum trust) |
| **Miner stake growth** | 0 → 103+ TAO in minutes |
| **Scoring accuracy** | Hash verification working correctly |
| **Test suite** | 124+ tests passing |
| **SQL generation** | Hybrid strategy: 12/20 via templates, 9-10/20 via LLM |

### What's Running Right Now
- Bittensor local chain running on AWS VPS (24/7)
- Template miner — deterministic SQL for common query patterns
- LLM miner — GPT-4o powered for complex/novel questions
- Validator with full hash-based scoring pipeline
- Frozen Parquet snapshot with 6 tables: subnets, validators, miners, stakes, emissions, metagraph

### Competition Status
- **Bittensor Subnet Ideathon** (HackQuest × OpenTensor Foundation, 565+ participants)
- **Round I:** Submitted whitepaper + architecture docs → **Advanced to Round II** (Honorable Mention out of 150+)
- **Round II:** Testnet build phase (deadline March 31, 2026)
- **Prize pool:** Up to $10,000 + potential 1,000 TAO investment (~$260,000) from Unsupervised Capital

---

## The Business Model

### Revenue Streams

1. **Query API fees** — Developers and apps pay per query. Just like Dune charges for premium queries, but our cost structure is lower because compute is decentralized.

2. **Subnet owner emissions** — 18% of all TAO emissions to subnet 2 go to QueryAgent as the subnet owner. At current rates, top subnets earn $10K-$100K+/month.

3. **Premium features** — Scheduled queries, custom dashboards, priority routing, higher rate limits.

4. **Data licensing** — Curated, verified blockchain analytics datasets.

### The Flywheel (Why This Grows)

```
More users asking questions
        ↓
More query fees (revenue)
        ↓
Revenue buys alpha tokens (our subnet's token)
        ↓
Alpha price rises → stakers earn more
        ↓
More TAO staked to our subnet
        ↓
Higher emissions → better miner rewards
        ↓
More miners join → faster, better answers
        ↓
Better product → more users
        ↓
(repeat)
```

This is the same flywheel that made Chutes (SN64) the #1 subnet with 14.4% of all Bittensor emissions and ~$100M market cap.

---

## Anti-Gaming (Why Miners Can't Cheat)

Investors always ask: *"What stops miners from gaming the system?"*

| Attack | Defense |
|--------|---------|
| **Return wrong answers** | Hash verification catches this instantly. Wrong hash = zero score. |
| **Memorize all answers** | Queries are parameterized and randomized. The combinatorial space is too large to precompute. Monthly snapshot rotation invalidates cached answers. |
| **Copy other miners** | Each miner runs independently. Validators query all miners simultaneously. |
| **Copy validator weights** | Commit-reveal system hides weights for multiple epochs. By the time you see weights, rankings have shifted. |
| **Run multiple fake miners** | Registration costs TAO. Bad miners earn nothing. Deregistration pressure removes underperformers. |
| **SQL injection** | DuckDB runs in read-only sandbox mode. Parameterized queries prevent injection. |

**The key insight:** In QueryAgent, doing real work (generating correct SQL) is always easier than trying to cheat. This is the hallmark of a well-designed Bittensor subnet.

---

## Competitive Advantages

### vs. Dune Analytics
- **No SQL required** — plain English queries
- **Decentralized** — no single point of failure, censorship-resistant
- **Verified answers** — cryptographic proof of correctness
- **Cheaper compute** — miners compete on efficiency, driving costs down

### vs. Other Bittensor Subnets
- **Deterministic scoring** — hash-based verification is objectively correct (most AI subnets use subjective model-based scoring that can be gamed)
- **Clear use case** — blockchain analytics is a $500M+ market with proven demand
- **Simple to understand** — "ask a question, get a verified answer" is easy to explain to stakers

### vs. Traditional Analytics Providers
- **Open and transparent** — all scoring, payments, and proofs are on-chain
- **Incentive-aligned** — miners are financially motivated to give the best answers
- **Scalable** — adding more miners = more compute, no centralized bottleneck

---

## The Team

- 2 co-founders with combined experience in blockchain development and AI systems
- Advanced from Round I (150+ submissions) to Round II of the Bittensor Subnet Ideathon
- Active builders in the Bittensor ecosystem

---

## The Ask

We're looking for:

1. **TAO staking** — Stake to our subnet to bootstrap emissions and validate the flywheel
2. **Infrastructure support** — VPS/GPU credits for running validators and expanding to more chains
3. **Strategic introductions** — Connections to Bittensor ecosystem (other subnet teams, validators, stakers)
4. **Advisory** — Guidance on subnet economics, tokenomics, and go-to-market

---

## Roadmap

### Now (March 2026)
- [x] Whitepaper and architecture docs
- [x] Working miner + validator on testnet
- [x] Hash-based scoring pipeline
- [x] 124+ test suite
- [x] Local chain deployment with live incentive flow

### Q2 2026
- [ ] Frontend launch (query interface + miner leaderboard)
- [ ] API gateway for external developers
- [ ] Multi-chain data (Ethereum, Polkadot, Cosmos)
- [ ] Mainnet deployment on Bittensor

### Q3 2026
- [ ] Revenue→alpha buyback loop
- [ ] Progressive difficulty scaling
- [ ] Dashboard builder
- [ ] Partnership with data aggregators

### Q4 2026
- [ ] 10+ chains covered
- [ ] Scheduled query system
- [ ] Premium tier launch
- [ ] Target: 100+ active miners, 1000+ monthly active users

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Bittensor daily emissions (post-halving) | ~3,600 TAO/day |
| Top subnet emission share (Chutes SN64) | 14.4% (~518 TAO/day) |
| TAO price (approx.) | ~$260 |
| Dune Analytics paying customers | 1,500+ |
| Blockchain analytics market | $500M+ and growing |
| Bittensor total market cap | ~$3B+ |
| Our testnet miner incentive score | 1.0 (maximum) |
| Our test suite | 124+ tests passing |

---

## TL;DR

**QueryAgent = "Google for blockchain data" powered by Bittensor.**

- Ask questions in plain English → get verified answers
- Miners compete to give the best answer → earn TAO
- Validators independently verify every answer → no trust required
- Hash-based scoring makes cheating harder than doing real work
- Already working on testnet with live incentive flow
- Building toward a revenue-generating API that creates a self-sustaining flywheel

**We're not just building an AI tool. We're building a decentralized truth engine for blockchain data.**

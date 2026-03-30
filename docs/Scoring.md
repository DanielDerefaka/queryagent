# QueryAgent — Mechanism Design

How miners earn, how validators verify, and why cheating doesn't pay.

---

## The Big Picture

QueryAgent is a Bittensor subnet where miners answer blockchain analytics questions in SQL, and validators check their work by re-running the SQL on frozen data. If the result matches — the miner scores. If it doesn't — zero.

There's no opinion, no judgment call, no subjective grading. Either your hash matches or it doesn't. This is what makes QueryAgent work well with Bittensor's consensus: every honest validator arrives at the exact same score for every miner.

---

## How a Single Round Works

```
Validator                         Miner
   |                                |
   |  1. Sample task (e.g. QB-004)  |
   |  2. Look up ground truth hash  |
   |                                |
   |--- QuerySynapse (question) --->|
   |                                |  3. Generate SQL from question
   |                                |  4. Execute SQL on DuckDB snapshot
   |                                |  5. Hash the result (SHA-256)
   |<-- SQL + result_hash ----------|
   |                                |
   |  6. Re-run miner's SQL         |
   |  7. Hash the result            |
   |  8. Compare to ground truth    |
   |  9. Compute score              |
   | 10. Update EMA weights         |
   |                                |
```

Key point at step 8: the validator doesn't compare the miner's hash to its own re-execution hash. It compares to the **pre-computed ground truth hash**. This means even if a miner sends plausible-looking SQL that returns "close" data, it gets a flat zero unless it matches exactly.

---

## The Scoring Formula

Every round, each miner gets a score between 0.0 and 1.0.

```
IF hash mismatch → score = 0.0 (hard gate, no partial credit)

IF hash matches:
    score = 0.75 + 0.15 * efficiency + 0.10 * latency
```

Where:
- **Correctness (75%)** — binary. Match = 0.75. Mismatch = 0.
- **Efficiency (15%)** — how fast the SQL executes on the validator's DuckDB. `efficiency = max(0, 1 - exec_ms / budget_ms)`. A query that takes 1ms on a 5000ms budget scores nearly full marks. A query that takes 4500ms barely scores.
- **Latency (10%)** — end-to-end response time from the miner. `latency = max(0, 1 - response_ms / latency_ms)`. Penalizes slow network or overloaded miners.

### Why 75/15/10?

Correctness dominates because a fast wrong answer is worthless. But among correct answers, we want to reward miners who write efficient SQL (less compute, scales better) and respond quickly (better UX for real users).

A perfect round scores ~1.0. A correct but slow round scores ~0.75. A wrong answer scores 0.0.

---

## EMA Smoothing

Scores aren't set from a single round. We use Exponential Moving Average to smooth scores over time:

```
EMA[uid] = 0.1 * new_score + 0.9 * EMA[uid]
```

Alpha = 0.1 means it takes roughly 10 correct rounds to go from 0 to near full score. This prevents a miner from getting lucky on one round and riding that forever. It also means a miner that goes offline or starts failing will gradually lose weight rather than getting immediately zeroed.

The EMA scores are then normalized to weights:

```
weight[uid] = EMA[uid] / sum(all EMA scores)
```

These weights go into `set_weights()` on the Bittensor chain. Yuma Consensus combines weights from all validators to determine each miner's emissions.

---

## The Hash: Why It's Deterministic

The entire system hinges on one property: **the same SQL on the same data always produces the same hash**. If this breaks, nothing works. Here's how we guarantee it:

1. **Frozen Parquet snapshots** — the data doesn't change. Everyone reads the same Parquet files into DuckDB.

2. **Canonical form before hashing:**
   - Floats → fixed 6 decimal places (`1.23` → `"1.230000"`)
   - NULLs → special sentinel string (`\x00NULL\x00`)
   - Booleans → lowercase `"true"` / `"false"`
   - Dates → ISO 8601 format
   - Rows → pipe-delimited (`"value1|value2|value3"`)

3. **Rows sorted before hashing** — `ORDER BY` in SQL isn't enough (ties can be non-deterministic). After fetching results, we sort all rows lexicographically on their canonical string form. This means two queries that return the same rows in different order still produce the same hash.

4. **SHA-256 of the canonical string** — column header + sorted rows, UTF-8 encoded.

Result format: `sha256:a3f8c2e1d5b7...`

---

## Task Pool and Difficulty Tiers

Tasks are sampled per round with weighted distribution:

| Tier | Share | Budget | Example |
|------|-------|--------|---------|
| Easy (30%) | Simple aggregations | 5s | "Total TAO staked across all subnets" |
| Medium (50%) | Joins, grouping, ranking | 8s | "Top 10 validators by stake" |
| Hard (20%) | CTEs, window functions, multi-step | 15s | "Gini coefficient of stake distribution per subnet" |

### Hidden Tasks

20% of sampled tasks come from a hidden pool that miners have never seen. These tasks aren't published anywhere. Miners can't pre-compute answers for them — they have to actually understand SQL and the data schema.

This is the main defense against lookup tables. A miner that memorizes all 16 public task answers will fail 20% of the time on hidden tasks, dragging its EMA score down compared to miners that genuinely generate SQL.

### Parameter Injection

Even for known tasks, the validator injects randomized parameters each round (time windows, k values, netuid filters). This prevents miners from caching exact answer hashes.

---

## Anti-Gaming Defenses

### Problem: Copying Other Miners
A lazy miner could intercept other miners' responses and copy them.

**Defense:** Miners respond directly to the validator via `bt.axon`. They don't see each other's responses. The validator queries all miners in parallel — there's no "first response" to copy.

### Problem: Hash Lookup Tables
A miner could pre-compute hashes for every known task and just return them without doing any SQL.

**Defense:** Hidden tasks (20% of rounds) aren't published. Parameter injection changes expected results across rounds. Monthly snapshot rotation invalidates all cached hashes.

### Problem: Running a Fake Validator
An attacker could run a "validator" that always gives their own miner max score.

**Defense:** Yuma Consensus clips outlier validators. If validator A gives miner X a score of 1.0 but validators B, C, D give it 0.0, validator A's weight gets clipped. With hash-based scoring, all honest validators compute identical scores — the outlier is obvious.

### Problem: SQL Injection
A miner sends `DROP TABLE validators; --` as their SQL.

**Defense:** DuckDB runs in-memory with read-only semantics. The `execute_sql_safe()` function rejects any SQL starting with `CREATE`, `DROP`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `COPY`, or `EXPORT`. Even if something slips through, there's nothing to damage — the snapshot is loaded fresh from Parquet files each time.

### Problem: Sybil Attacks
An attacker registers 100 miners that all return the same answer.

**Defense:** Registration requires stake (TAO). Deregistration pressure removes low-performing neurons. Running 100 identical miners means 100x the stake for the same total weight — it's economically irrational.

---

## dTAO and Emissions

QueryAgent runs under Bittensor's dTAO (dynamic TAO) model:

```
Emissions split:
  41% → Miners (proportional to weight from validators)
  41% → Validators (proportional to stake delegated to them)
  18% → Subnet owner
```

dTAO means QueryAgent has its own token market. Stakers buy into the subnet if they believe it produces value. Zero stakers = zero emissions = the subnet dies. This creates real market pressure to deliver useful analytics.

---

## The Full Loop

Putting it all together, here's what happens every ~12 seconds on the network:

1. Each validator samples a random task (weighted by difficulty)
2. Sends the question to all miners via `bt.dendrite` → `QuerySynapse`
3. Miners generate SQL, execute it, hash the result, send it back
4. Validator re-runs the SQL, compares hash to ground truth
5. Scores: 0.0 for mismatch, 0.75+ for match (bonus for speed)
6. EMA update smooths scores over time
7. Every 20 blocks (~4 min), validator calls `set_weights()` on chain
8. Yuma Consensus combines all validators' weights
9. Emissions flow to miners proportional to their consensus weight

Better SQL = higher score = more weight = more TAO. That's the whole incentive.

---

## Config Reference

| Parameter | Value | What It Does |
|-----------|-------|-------------|
| `CORRECTNESS_WEIGHT` | 0.75 | Base score for correct hash |
| `EFFICIENCY_WEIGHT` | 0.15 | Bonus for fast SQL execution |
| `LATENCY_WEIGHT` | 0.10 | Bonus for fast response |
| `EMA_ALPHA` | 0.1 | Smoothing factor (higher = more reactive) |
| `EASY_SHARE` | 30% | Probability of sampling easy task |
| `MEDIUM_SHARE` | 50% | Probability of sampling medium task |
| `HARD_SHARE` | 20% | Probability of sampling hard task |
| `HIDDEN_RATIO` | 20% | Probability of hidden (unpublished) task |
| `FLOAT_PRECISION` | 6 | Decimal places in canonical hash |
| `WEIGHTS_RATE_LIMIT` | 20 blocks | Min gap between set_weights calls |

---

## Why This Design Works

1. **Objectivity** — Hash match is binary. No LLM grading, no rubrics, no gray areas.
2. **Consensus-friendly** — All honest validators compute identical scores. Yuma Consensus converges cleanly.
3. **Economically sound** — Correct miners earn more. Faster miners earn slightly more. Cheaters earn zero.
4. **Sybil-resistant** — Duplicate miners share the same weight pool. No advantage to running copies.
5. **Future-proof** — Snapshot rotation and hidden tasks prevent stale strategies. Miners must keep improving.

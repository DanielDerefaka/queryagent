# QueryAgent — Testnet Readiness Checklist

Based on all findings, here's what we need to build and validate.

---

## Critical Path (Must Have for Testnet)

### Infrastructure
- [ ] Initialize git repo with proper structure
- [ ] Set up Python project (pyproject.toml, requirements.txt)
- [ ] Create `queryagent/protocol.py` — QuerySynapse definition
- [ ] Create `queryagent/snapshot.py` — Parquet → DuckDB loader

### Data Pipeline
- [ ] Connect to `bt.subtensor` and index chain data
- [ ] Tables to index: subnets, validators, miners, stakes, emissions, metagraph
- [ ] Export to Parquet files (versioned, frozen)
- [ ] Generate `schema.json` + `metadata.json` per snapshot
- [ ] Create at least ONE working snapshot

### Task Pool
- [ ] Write 50+ tasks across Easy (30%) / Medium (50%) / Hard (20%)
- [ ] Author reference SQL for each task
- [ ] Execute reference SQL on snapshot → compute SHA-256 ground truth hashes
- [ ] Include 10-15 hidden tasks (never published)
- [ ] Store in `benchmark/tasks/` and `benchmark/ground_truth/`

### Scoring Engine
- [ ] Hash comparison (hard gate — wrong hash = 0.0)
- [ ] Efficiency scoring: `max(0, 1 - exec_ms / budget_ms)` — validator-timed
- [ ] Latency scoring: `max(0, 1 - response_ms / latency_budget_ms)`
- [ ] Combined: `score = 0.75 + 0.15 × efficiency + 0.10 × latency`
- [ ] EMA smoothing: `EMA[uid] = 0.1 × new + 0.9 × old`
- [ ] Weight normalization: `weight[uid] = EMA[uid] / Σ(EMA)`

### Reference Miner
- [ ] Receive QuerySynapse via bt.axon (NOT Docker HTTP)
- [ ] Load snapshot into DuckDB (read-only, sandboxed)
- [ ] Generate SQL from question (template-based baseline)
- [ ] Execute SQL, compute SHA-256 hash of result
- [ ] Return Answer Package within 30s timeout
- [ ] Handle errors gracefully (return empty response, not crash)

### Validator
- [ ] Sample task from pool (public + hidden, all difficulty tiers)
- [ ] Build QuerySynapse, broadcast to miners via bt.dendrite
- [ ] Collect responses within timeout
- [ ] Re-execute each miner's SQL on own DuckDB (timed)
- [ ] Compare hash to ground_truth_hash
- [ ] Compute scores, apply EMA
- [ ] Call `subtensor.set_weights()` on-chain
- [ ] Respect `weights_rate_limit` (default 100 blocks)

### Testnet Deployment
- [ ] Create subnet on Bittensor testnet (`btcli subnet create --network test`)
- [ ] Register miner hotkey on subnet
- [ ] Register validator hotkey on subnet
- [ ] Run full loop: task → answer → verify → score → weights
- [ ] Demonstrate weights changing based on miner performance
- [ ] Record demo video

---

## Important Corrections from Findings

### Master Plan Errors to Fix
1. **Docker HTTP model is WRONG** — miners use bt.axon (Bittensor P2P), not Docker HTTP endpoints
2. **"QueryBench" branding** — already removed, use "QueryAgent" everywhere
3. **Data source** — use `bt.subtensor` indexer (already decided), not taostats

### SDK Patterns to Follow
- Use `bt.config(parser)` for configuration
- Use `bt.wallet.add_args(parser)` for wallet args
- Use `bt.subtensor.add_args(parser)` for network args
- Metagraph sync: `metagraph.sync(subtensor=subtensor)` every ~10-20 blocks
- Weight setting: respect rate limits, normalize to sum=1.0

### Anti-Gaming (Already Designed)
- 50 hidden tasks ✓
- Parameterised task injection ✓
- Monthly snapshot rotation ✓
- DuckDB sandboxing (read-only) ✓
- Deregistration pressure (Bittensor built-in) ✓
- Yuma Consensus clips outlier validators ✓

---

## Nice to Have (Post-Testnet)

- [ ] LLM fallback in miner (beyond template SQL)
- [ ] Commit-reveal for weight confidentiality
- [ ] Snapshot CDN/IPFS distribution for validators
- [ ] Public leaderboard web UI
- [ ] QueryAgent Chat demo (user-facing)
- [ ] SDK/API for external consumers
- [ ] Query Packs (prebuilt templates)
- [ ] Multi-chain expansion (EVM, Solana)

---

## Hardware Requirements (Estimated)

### Miner
- CPU: 4+ cores
- RAM: 8GB+ (DuckDB in-memory)
- Storage: 5GB+ (snapshot cache)
- GPU: Not required
- Network: Stable connection for axon server

### Validator
- CPU: 4+ cores
- RAM: 16GB+ (re-executing multiple miners' SQL concurrently)
- Storage: 10GB+ (snapshot + task pool + ground truth)
- GPU: Not required
- Network: Stable connection for dendrite queries

---

## Build Order (Recommended)

```
1. protocol.py (QuerySynapse)     — everything depends on this
2. snapshot.py (Parquet → DuckDB) — data foundation
3. build_snapshot.py (indexer)     — create real data
4. generate_tasks.py (task pool)   — create evaluation tasks
5. scoring.py (score computation)  — evaluation logic
6. miner.py (reference miner)     — responds to tasks
7. validator.py (validator)        — sends tasks, scores, sets weights
8. Test locally (mock network)     — verify full loop
9. Deploy to testnet               — real Bittensor network
10. Record demo                    — proof for judges
```

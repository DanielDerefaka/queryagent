# QueryAgent — Round II Roadmap

**Deadline:** March 31, 2026
**Status:** Testnet working on local chain. Incentive loop proven. 124+ tests passing.

---

## P0 — Must Ship (judge-facing, high impact)

### 1. Frontend + Leaderboard App
Build a web app that serves as both the **product demo** and the **miner dashboard**.

**Product side (public):**
- Search bar: type a question in plain English, get verified SQL + results
- Shows which miner answered, their score, response time
- Result includes the hash proof (verifiable answer)
- A few example questions pre-loaded for first-time visitors

**Miner leaderboard side:**
- Live leaderboard: rank, UID, hotkey (truncated), total score, tasks answered, accuracy %
- Per-miner detail page: score history over time, task breakdown, earnings
- Validator stats: rounds run, average response time, weight history

**Tech:** FastAPI backend + simple React/Next.js frontend (or even plain HTML/JS if faster). Backend talks to the validator's scoring data + on-chain metagraph.

### 2. API Gateway for Organic Queries (Gap 1)
- POST `/api/query` → accepts natural language question → routes to miners via validator
- Returns: SQL, result, hash, miner UID, verification status
- This is what makes QueryAgent a real product, not just a subnet
- Rate limiting, API keys for production (can be stub for testnet demo)

### 3. Demo Video
- Screen recording of: frontend query → miner processing → validator scoring → on-chain weights
- Show leaderboard updating in real time
- Show `btcli subnet show` with real emissions flowing
- Keep under 3 minutes

---

## P1 — Mechanism Improvements (shows sophistication to judges)

### 4. Partial Credit Scoring (Gap 2)
Current: binary pass/fail on hash match.
Improved:
- Exact hash match = full correctness (0.75)
- Partial credit tiers: right tables but wrong aggregation (0.3), right structure but off values (0.5)
- Implement by comparing result shape (column names, row count) before hash
- Prevents all-or-nothing cliff that discourages new miners

### 5. Task Difficulty Progression (Gap 5)
- Track each miner's rolling accuracy per tier
- If accuracy > 80% on current tier for 10+ tasks, increase hard task weight
- If accuracy < 40%, decrease hard task weight
- Adaptive difficulty shows a living, evolving incentive mechanism

### 6. Baseline Miner (Gap 12)
- `neurons/miner_baseline.py` — dead simple miner that returns canned answers for known task IDs
- Scores ~30-40% (only matches exact tasks it has memorized)
- Purpose: easy onboarding for new miners, demonstrates scoring differentiation
- Include in README as "start here" option

### 7. Anti-Memorization Measures (Gap 3)
- Parameterized task injection: same question template, different constraints each round
  - e.g., "Top K validators on subnet N" where K and N change
- Rotate hidden task pool every epoch
- Log and flag miners that answer hidden tasks suspiciously fast

---

## P2 — Production Readiness (important but can describe as "planned")

### 8. Commit-Reveal Weights (Gap 7)
- Currently disabled for local chain testing
- For testnet/mainnet: enable commit-reveal, update validator to use `commit_weights()` + `reveal_weights()`
- Document the two-phase weight submission flow

### 9. Snapshot Coordination (Gap 6)
- Validators and miners must use the same snapshot version
- Add snapshot version negotiation: validator announces current snapshot in synapse
- Miners that don't have it can download from a known URL
- Pin DuckDB version in requirements.txt (Gap 9)

### 10. Multi-Validator Support (Gap 8)
- Current code assumes single validator — works for testnet demo
- For mainnet: handle multiple validators setting weights, Yuma Consensus resolving disagreements
- Test with 2+ validators on local chain

### 11. Revenue → Alpha Buyback Loop (Gap 4)
- Outline the model: API query fees → treasury → buy subnet alpha token
- Even if not implemented, describe the mechanism in docs and frontend "About" page
- Shows judges we understand dTAO sustainability

### 12. Efficiency Scoring Depth (Gap 10)
- Current: basic latency component (10%)
- Improved: measure DuckDB query plan complexity, rows scanned, memory usage
- Reward miners who write optimized SQL, not just correct SQL

---

## P3 — Future / Can Mention in Docs

### 13. Multi-Chain Roadmap (Gap 11)
- Currently Bittensor-only snapshots
- Future: Ethereum, Solana, Cosmos chain data
- Each chain = new snapshot type, same verification mechanism
- Mention in whitepaper/pitch as growth path

### 14. EMA Tuning (Gap 14)
- Current α=0.1 may be too slow to reward rapid improvement
- Test different α values, possibly adaptive α based on task tier
- Lower priority — current value works fine for demo

### 15. External Integrations
- Telegram bot that answers blockchain questions via QueryAgent
- Discord bot for Bittensor community
- Shows real-world utility beyond the web app

---

## Infrastructure / Cleanup

### 16. Git Init + GitHub Push
- Initialize git repo (currently not a git repo)
- .gitignore for __pycache__, .env, snapshots (large parquet files)
- Push to GitHub — required for submission

### 17. README.md
- Quick start: how to run miner + validator
- Architecture diagram
- API docs for the query endpoint
- Link to frontend demo

### 18. Fix Known Bugs
- Miner metagraph sync crash on fast-blocks (wrap in try/except)
- `set_weights()` silent failure logging — add `wait_for_inclusion=True` with timeout

### 19. CI / Tests
- GitHub Actions: run test suite on push
- Add test for partial credit scoring once implemented
- Add integration test for API gateway

---

## What's Already Done

- [x] QuerySynapse protocol
- [x] Snapshot pipeline (Parquet → DuckDB)
- [x] 35 tasks (20 public + 15 hidden) with ground truth hashes
- [x] Deterministic hashing (SHA-256, verified across 100 runs)
- [x] Template miner (15 regex patterns, 12/20 correct)
- [x] LLM miner (gpt-4o, 9-10/20 correct)
- [x] Hybrid miner (template + LLM fallback)
- [x] Validator with full scoring (75/15/10 + EMA)
- [x] SQL sandboxing (injection attacks blocked)
- [x] Local chain deployment — miner earning TAO, incentive=1.0
- [x] 124+ tests across 11 test files
- [x] Testnet deployment report
- [x] Round I docs (whitepaper, mechanism design, pitch deck, video script)

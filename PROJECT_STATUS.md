# QueryAgent — Full Project Status

Everything we've built so far, how it works, and what's left.

---

## What is QueryAgent?

A Bittensor subnet that lets you ask blockchain questions in plain English and get verified, provable answers. Miners compete to generate correct SQL, validators re-execute and verify via hash comparison, and Yuma Consensus distributes TAO emissions based on performance.

---

## Part 1: Subnet Logic (Python Backend)

### File Structure

```
queryagent/
├── protocol.py       # Wire format — QuerySynapse (bt.Synapse subclass)
├── config.py         # All tunable constants in one place
├── hashing.py        # Deterministic SHA-256 of DuckDB query results
├── snapshot.py       # Parquet → DuckDB loader (read-only, sandboxed)
├── tasks.py          # Task pool manager (sampling, tiers, hidden tasks)
├── scoring.py        # Score computation + EMA + weight normalization
│
neurons/
├── miner.py          # Reference miner — template-based SQL generation
├── miner_llm.py      # LLM-powered miner variant (future)
├── validator.py      # Validator — sends tasks, re-executes, scores, sets weights
│
scripts/
├── build_snapshot.py  # bt.subtensor → Parquet snapshot indexer
├── generate_tasks.py  # Create task pool + compute ground truth hashes
│
benchmark/
├── snapshots/bt_snapshot_test_v1/
│   ├── schema.json        # Table definitions
│   ├── metadata.json      # Build time, row counts, checksums
│   └── tables/
│       ├── subnets.parquet
│       ├── validators.parquet
│       ├── miners.parquet
│       ├── stakes.parquet
│       ├── emissions.parquet
│       └── metagraph.parquet
├── tasks/
│   ├── public_tasks.json   # ~15 public tasks
│   └── hidden_tasks.json   # ~5 hidden tasks (never published)
└── ground_truth/
    ├── QB-001.json through QB-033.json  # 19 ground truth entries
```

---

### `queryagent/protocol.py` — Wire Format (DONE)

Defines `QuerySynapse(bt.Synapse)` — the message format between validators and miners.

**Request fields** (validator fills):
- `task_id` — unique task ID (e.g. "QB-001")
- `snapshot_id` — which frozen dataset to query
- `question` — natural language analytics question
- `constraints` — optional dict (time_window, max_rows, k, netuid_filter)

**Response fields** (miner fills):
- `sql` — the SQL query the miner generated
- `result_hash` — SHA-256 hash of the deterministic result
- `result_preview` — first N rows (columns + rows)
- `tables_used` — which tables the SQL references
- `explanation` — short text explaining the logic

Both validator and miner import the exact same class. All response fields are `Optional[...] = None` so the synapse is valid before the miner fills it.

---

### `queryagent/config.py` — Constants (DONE)

All tunable parameters centralized:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `CORRECTNESS_WEIGHT` | 0.75 | Score weight for hash correctness |
| `EFFICIENCY_WEIGHT` | 0.15 | Score weight for SQL execution speed |
| `LATENCY_WEIGHT` | 0.10 | Score weight for end-to-end response time |
| `EMA_ALPHA` | 0.1 | Smoothing factor (rewards consistency) |
| `EASY/MEDIUM/HARD_SHARE` | 0.30/0.50/0.20 | Task difficulty distribution |
| `HIDDEN_RATIO` | 0.20 | Fraction of tasks that are hidden |
| `DEFAULT_TIMEOUT_S` | 30 | Miner response timeout (seconds) |
| `DEFAULT_BUDGET_MS` | 5000 | Max SQL execution time (ms) |
| `FLOAT_PRECISION` | 6 | Decimal places for float hashing |
| `WEIGHTS_RATE_LIMIT_BLOCKS` | 100 | Min blocks between set_weights() calls |
| `METAGRAPH_SYNC_INTERVAL_S` | 120 | Seconds between metagraph syncs |

Also defines paths (`SNAPSHOT_DIR`, `TASKS_DIR`, `GROUND_TRUTH_DIR`), expected tables list, and tier budgets.

---

### `queryagent/hashing.py` — Deterministic Hashing (DONE)

The core of verification. Produces identical SHA-256 hashes for identical query results regardless of who runs the query.

**Canonicalization rules:**
- Floats rounded to 6 decimal places
- NULLs → sentinel string `\x00NULL\x00`
- Booleans → "true"/"false"
- Dates → ISO 8601
- Bytes → hex
- Rows sorted lexicographically (prevents ordering differences)
- Column header is part of the hash (prevents column renaming tricks)

**Functions:**
- `hash_result(conn, sql)` → execute SQL, hash result, return `"sha256:<hex>"`
- `hash_from_rows(columns, rows)` → hash pre-fetched data (no DB needed)
- `verify_hash(conn, sql, expected)` → boolean check

---

### `queryagent/snapshot.py` — Snapshot Loader (DONE)

Loads frozen Parquet snapshots into DuckDB in-memory databases.

**Key features:**
- In-memory cache (`_cache` dict) — avoids reloading on every request
- Read-only safety — DuckDB connection only used for SELECT
- `execute_sql_safe()` — rejects forbidden operations (CREATE, DROP, INSERT, DELETE, etc.)
- Timed execution — returns `(columns, rows, exec_ms)` for scoring
- Schema/metadata loading from JSON
- Used by BOTH miner and validator

**Current snapshot:** `bt_snapshot_test_v1` with 6 tables (subnets, validators, miners, stakes, emissions, metagraph)

---

### `queryagent/tasks.py` — Task Pool (DONE)

Manages the pool of benchmark tasks with ground truth.

**Task dataclass:**
- `task_id`, `snapshot_id`, `question`, `tier`, `is_hidden`
- `constraints`, `reference_sql`, `ground_truth_hash`
- `budget_ms`, `latency_ms`

**TaskPool class:**
- Loads public + hidden tasks from JSON files
- Loads ground truth (one JSON per task) and attaches to tasks
- Indexes tasks by tier for weighted sampling
- `sample_task()` — weighted random: 30% easy, 50% medium, 20% hard, ~20% hidden
- Parameter injection — randomizes `time_window`, `k`, `netuid_filter` to prevent memorization

**Current pool:** ~15 public tasks + ~5 hidden tasks across easy/medium/hard tiers, with 19 ground truth entries.

---

### `queryagent/scoring.py` — Score Engine (DONE)

**Formula:**
```
IF hash mismatch → score = 0.0 (hard gate)
IF hash matches:
  efficiency = max(0, 1 - exec_ms / budget_ms)
  latency    = max(0, 1 - response_ms / latency_ms)
  score      = 0.75 + 0.15 × efficiency + 0.10 × latency
```

Score range: `[0.0]` for wrong answers, `[0.75, 1.0]` for correct answers. Speed only differentiates correct miners.

**EMA smoothing:** `EMA[uid] = 0.1 × new + 0.9 × old` — rewards consistent performers over lucky one-shot wins.

**Weight normalization:** `weight[uid] = EMA[uid] / sum(EMA)` — weights sum to 1.0 for `set_weights()`.

**Functions:**
- `compute_score()` — single miner, single round
- `score_responses()` — batch scoring with re-execution results
- `update_ema()` — apply smoothing to scores tensor
- `normalize_weights()` — normalize for on-chain submission

---

### `neurons/miner.py` — Reference Miner (DONE)

Template-based SQL generation (v1). Receives `QuerySynapse` via `bt.axon`, not Docker HTTP.

**SQL Templates:** 14 patterns covering:
- Easy: total staked, subnet count, active miners, total emissions, validator count, average stake
- Medium: top-k validators by stake, highest emission subnet, top-k miners by incentive, average vtrust per subnet, subnets ranked by active miners, stake distribution, top dividends, neuron count

**Forward function flow:**
1. Receive `QuerySynapse` from validator
2. Load snapshot into DuckDB (cached)
3. Match question to template via regex
4. Inject parameters (`k`, `netuid`) from constraints or regex groups
5. Execute SQL, compute SHA-256 hash
6. Build result preview (first 10 rows)
7. Fill synapse response fields and return

**Main loop:**
- Parse args (netuid, wallet, subtensor)
- Create axon, attach forward function, serve + start
- Sync metagraph every 12 seconds
- Log miner status (UID, stake, incentive)
- Graceful shutdown on SIGINT

---

### `neurons/validator.py` — Validator (DONE)

The orchestrator. Sends tasks, collects answers, verifies, scores, sets weights on-chain.

**Validation round flow:**
1. Sample task from pool (weighted by difficulty, mix hidden/public)
2. Build `QuerySynapse` with task details
3. Broadcast to all miners via `bt.dendrite` (30s timeout)
4. For each response: re-execute miner's SQL on validator's DuckDB (timed, sandboxed)
5. Compare validator's result hash to ground truth hash
6. Compute scores using 75/15/10 formula
7. Update EMA scores
8. Log round results

**Main loop:**
- Parse args, connect to subtensor, load task pool + snapshot
- Initialize EMA scores tensor (zeros)
- Every ~12 seconds: run validation round
- Every 100 blocks: normalize weights + `set_weights()` on-chain
- Sync metagraph every 120 seconds
- Resize scores tensor if metagraph changes
- Graceful shutdown on SIGINT

---

### `scripts/build_snapshot.py` — Indexer (DONE)

Connects to `bt.subtensor` and indexes chain data into Parquet files.

**Tables indexed:**
| Table | Key Columns |
|-------|-------------|
| subnets | netuid, name, owner, tempo, emission, created_at |
| validators | uid, hotkey, stake, vtrust, dividends, active, netuid |
| miners | uid, hotkey, stake, rank, trust, incentive, emission, active, netuid |
| stakes | hotkey, coldkey, stake_amount, netuid, timestamp |
| emissions | netuid, uid, emission, block, timestamp |
| metagraph | netuid, uid, hotkey, stake, rank, trust, consensus, incentive, emission, dividends, active |

**Output:** versioned snapshot bundle with `schema.json`, `metadata.json`, and Parquet files in `tables/`.

---

### `scripts/generate_tasks.py` — Task Generator (DONE)

Creates the task pool and computes ground truth hashes by executing reference SQL against the snapshot.

**Output:**
- `public_tasks.json` — tasks visible to everyone (no reference SQL or ground truth)
- `hidden_tasks.json` — validator-only tasks
- `ground_truth/QB-XXX.json` — one per task with reference SQL + expected hash

---

### Tests (DONE)

| File | What It Tests |
|------|---------------|
| `test_protocol.py` | QuerySynapse creation, serialization, deserialization |
| `test_hashing.py` | Determinism — same SQL = same hash. Float precision. NULLs. Empty results. |
| `test_scoring.py` | Score = 0 on wrong hash. Score in [0.75, 1.0] on correct. EMA convergence. |
| `test_snapshot.py` | Parquet loads into DuckDB. Read-only enforced. Schema matches. |
| `test_tasks.py` | Task loading, sampling, tier distribution, parameter injection |
| `test_wire.py` | Wire format serialization round-trip |
| `test_determinism.py` | Cross-run determinism checks |
| `test_adversarial.py` | Adversarial SQL injection, forbidden operations |
| `test_e2e.py` | Full loop: sample task → generate SQL → hash → verify → score |
| `test_llm_miner.py` | LLM miner variant tests |

---

### Supporting Files (DONE)

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies (bittensor, duckdb, pyarrow, torch, numpy) |
| `requirements.txt` | Pinned dependencies |
| `min_compute.yml` | Hardware requirements (miner: 4 CPU, 8GB RAM; validator: 4 CPU, 16GB RAM) |
| `Dockerfile` | Container build for miner/validator |
| `docker-compose.yml` | Multi-service setup |
| `.env.example` | Environment variable template |
| `README.md` | Overview and setup instructions |

---

## Part 2: Frontend (Next.js + TypeScript)

### Stack
- **Framework:** Next.js 15 App Router
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Animations:** GSAP + ScrollTrigger + `@gsap/react`
- **Components:** shadcn/ui
- **Fonts:** Aeonik (headings/nav), Formular (body)
- **Brand colors:** Emerald (#10B981), Deep green (#064e3b)
- **Background:** #f0f0f0 (landing), white (card sections)

### Landing Page (`/`)

| Section | Component | Description |
|---------|-----------|-------------|
| Navbar | `navbar.tsx` | Fixed top, glass blur on scroll, Platform (dropdown → Leaderboard), Docs, Blog, Miners, Launch App button |
| Hero | `hero.tsx` | Full-height dark section, headline, CTA buttons, trust badges, embedded video preview (loops `demo.mov`), click opens fullscreen modal player |
| Hero Background | `hero-background.tsx` | Simplex noise canvas animation behind hero |
| Showcase | `showcase.tsx` | Horizontal scrolling cards with Unsplash images, left heading + right cards with arrow navigation |
| Bento Features | `bento-features.tsx` | Meridian-style product feature cards with GSAP scroll animations |
| How It Works | `how-it-works.tsx` | 4-column layout: ASK → COMPETE → VERIFY → DELIVER with timeline dots and visual cards (ChatCard, ScoreCard, HashCard, TableCard) |
| API Section | `api-section.tsx` | Split layout — grid pattern + heading on left, request/response code blocks on right (gray bg) |
| Integrations | `integrations.tsx` | White rounded container with grid pattern strip, auto-scrolling card columns (pause on hover), tech icons from SimpleIcons/CryptoLogos CDN |
| CTA | `cta.tsx` | Green gradient section with email input, testimonial card, grid pattern overlay |
| Footer | `footer.tsx` | White card with grid pattern bg, logo, newsletter signup, 4-column links, social icons (X, Discord, GitHub, Telegram) |

**Animations:**
- GSAP ScrollTrigger on all sections (parallax, stagger, fade-in)
- CSS keyframe auto-scrolling on integration cards
- Intro loader exists (`intro-loader.tsx`, `landing-wrapper.tsx`) but not currently wired in due to cursor-blocking issues

### Auth Pages

| Route | Description |
|-------|-------------|
| `/signup` | Split layout — form on left (45%), dark emerald panel on right (55%) with grid pattern, live query preview card, 3 feature callouts |
| `/login` | Same split layout — login form on left, dark emerald panel on right with grid pattern, testimonial quote |

Both have Google + GitHub OAuth buttons, emerald-branded inputs, cross-links between login/signup.

### Dashboard App (Inner Product)

**Shared layout:** Collapsible sidebar (240px → 60px icon rail) + topbar with notification bell and "New" button. Grid pattern background on all pages.

**Sidebar navigation:**
- Home, Discover, Queries, Data, Dashboards, Leaderboard
- "New Query" button
- Favorites placeholder
- Settings
- User profile with dropdown (Public profile, Log out)

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | Home | Welcome banner (dark green + grid), quick action cards (Queries, Dashboards, Data, Blockchains), stats row (Active Subnets, Total Miners, Emissions, Top Subnet), activity feed + trending queries |
| `/dashboard/queries` | Query List | Search + filters, tabs (All/My/Starred), table with title, SQL preview, runs count, verified status, hover actions (Run, Copy, More) |
| `/dashboard/queries/[id]` | Query Editor | Full-screen SQL editor (dark theme) + results panel, title input, verified badge, Save/Share/Export/Run buttons, table/chart view toggle, syntax-highlighted SQL |
| `/dashboard/queries/new` | New Query | Blank SQL editor, placeholder guidance, Run button disabled until SQL entered |
| `/dashboard/dashboards` | Dashboard List | Search, grid of dashboard cards with chart type icons, star/more actions, "Create new" dashed card |
| `/dashboard/discover` | Explore | Search + category pills (All, Subnets, Staking, Emissions, Miners, Validators), grid of trending queries/dashboards with stars/views/forks |
| `/dashboard/data` | Table Browser | Left panel: searchable table list with row/col counts. Right panel: selected table schema viewer with column names, types (with type icons), descriptions |
| `/dashboard/settings` | Settings | Dune-style layout — left tabs (Public profile, Plan, Usage, Teams, Account, API Keys, Notifications), right content area. Account shows email/password with Edit buttons + delete account. API Keys with show/copy. Usage with progress bars. Notifications with toggles. |
| `/leaderboard` | Leaderboard | Public page (uses landing navbar/footer), miner rankings table with rank badges, scores color-coded, accuracy/latency/tasks/stake/incentive columns, sort controls, scoring explanation cards (75/15/10) |

### Other Pages

| Route | Description |
|-------|-------------|
| `/chat` | AI Chat interface (exists from earlier build) |
| `/query` | Query page (exists from earlier build) |

---

## Part 3: Data Flow (End-to-End)

```
┌─────────────────────────────────────────────────────────────┐
│                     EVERY TEMPO (~72 min)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  VALIDATOR                           MINERS (via bt.axon)    │
│  ─────────                           ───────────────────     │
│  1. Sample task from pool                                    │
│  2. Build QuerySynapse                                       │
│     (task_id, snapshot_id,                                   │
│      question, constraints)                                  │
│  3. Broadcast via bt.dendrite  ───→  4. Receive synapse      │
│                                      5. Load snapshot        │
│                                      6. Generate SQL         │
│                                      7. Execute on DuckDB    │
│                                      8. Hash result          │
│  9. Collect responses          ←───  9. Return filled        │
│                                         synapse              │
│  10. For each miner:                                         │
│      a. Re-execute SQL on own DuckDB                         │
│      b. Compute hash of own result                           │
│      c. Compare to ground_truth_hash                         │
│      d. Wrong → 0.0                                          │
│      e. Right → 0.75 + 0.15×eff + 0.10×lat                  │
│  11. EMA smooth scores                                       │
│  12. Normalize weights                                       │
│  13. set_weights() on-chain                                  │
│                                                              │
│              ↓                                                │
│  YUMA CONSENSUS                                              │
│  → 41% TAO to miners                                        │
│  → 41% TAO to validators                                    │
│  → 18% TAO to subnet owner                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 4: Anti-Gaming Measures

| Measure | How It Works |
|---------|-------------|
| Hidden tasks (50) | Never published — miners can't pre-compute answers |
| Parameter injection | time_window, k, netuid randomized per round |
| Monthly snapshot rotation | Data changes, old memorized answers break |
| DuckDB sandboxing | Read-only, no filesystem/network access |
| SQL safety filter | Rejects CREATE, DROP, INSERT, DELETE, ALTER, COPY, EXPORT |
| Deregistration pressure | Bittensor built-in — low performers get deregistered |
| Yuma Consensus | Clips outlier validators — honest majority wins |
| EMA smoothing (α=0.1) | Rewards consistency, punishes one-shot gaming |

---

## Part 5: What's Left

### Subnet Logic
- [ ] Run full test suite and fix any failures
- [ ] Test on Bittensor testnet (create subnet, register miner + validator)
- [ ] Run full incentive loop on testnet (task → answer → verify → score → weights)
- [ ] Record demo video showing weights changing based on performance
- [ ] Expand task pool to 50+ public + 50 hidden (currently ~20 total)

### Frontend → Backend Wiring
- [ ] Connect dashboard to real Bittensor data (currently mock/static data)
- [ ] Wire SQL editor to actual DuckDB query execution
- [ ] Wire leaderboard to live metagraph data
- [ ] Auth system (currently UI-only, no backend)
- [ ] API endpoints for frontend to call

### Landing Page Polish
- [ ] Fix intro loader animation (green → white wipe transition)
- [ ] Hero video player (small preview + fullscreen modal) needs testing
- [ ] CTA section needs grid pattern overlay added

### Nice to Have (Post-Testnet)
- [ ] LLM fallback in miner (beyond template SQL)
- [ ] Commit-reveal for weight confidentiality
- [ ] Snapshot CDN/IPFS distribution
- [ ] Multi-chain expansion (EVM, Solana)
- [ ] Query Packs (prebuilt templates for common analytics)

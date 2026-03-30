# What makes a Bittensor subnet excellent, and where QueryAgent stands

**QueryAgent's hash-based SQL verification on frozen Parquet/DuckDB snapshots is a technically sound foundation, but the subnet needs significant work on organic demand, anti-memorization, progressive task difficulty, and external revenue to compete with top-tier subnets.** The best Bittensor subnets—Chutes (SN64) with 400,000+ users and 14.4% of emissions, Ridges AI (SN62) earning miners $62K/day, and TAOHash (SN14) bootstrapping 6 EH/s of Bitcoin hashrate with zero capex—succeed because they combine bulletproof incentive mechanisms with real external value creation. Under the dTAO flow-based emission model launched November 2025, subnets live or die by net TAO inflows from stakers, making "would anyone use this if emissions stopped tomorrow?" the existential test. This report synthesizes deep research across all 14 requested dimensions, mapping the Bittensor competitive landscape against QueryAgent's architecture and identifying specific gaps.

---

## The top subnets share five traits that drive emissions dominance

Across the 128 active Bittensor subnets (capped since October 2025), the top 10 command **56.5% of all TAO emissions**. Three entities—Rayon Labs (SN64, SN56, SN19), Macrocosmos (SN1, SN9, SN13, SN25), and Latent Holdings (SN14)—dominate. After the first halving on December 14, 2025, daily emissions dropped from ~7,200 TAO to **~3,600 TAO** (0.5 TAO per 12-second block), intensifying competition.

**Chutes (SN64)** leads with 14.4% of emissions and a ~$100M market cap. It offers serverless AI compute **85% cheaper than AWS**, processes 30+ billion tokens daily, and has 100,000+ API users—most of whom don't know they're on Bittensor. Miners are scored on compute availability, cold-start times, uptime, and GPU authenticity (verified via GraVal middleware). Revenue auto-stakes into alpha token buybacks, creating a self-reinforcing flywheel.

**TAOHash (SN14)** takes 8.2% of emissions by doing something no other subnet does: incentivizing Bitcoin miners to allocate SHA-256 hashrate. Its TIDES distribution system uses Inverse Fourier Transform to let small miners contribute effectively. A perpetual BTC↔alpha buyback loop means validators buy alpha with BTC earnings while miners swap BTC payouts for alpha tokens. It bootstrapped 6 EH/s (~0.7% of global Bitcoin hashrate) within its first week with only 11 miners.

**Zeus (SN18)** demonstrates what "proof of intelligence" looks like for data subnets. It forecasts weather using ERA5 reanalysis data, scoring miners via **weighted RMSE adjusted by regional difficulty** (z-score based on variance). Forecasting mountainous/volatile regions earns more than ocean predictions. Its "Best Recent Performer" system routes forecasts through the top miner per forecast window, creating a decentralized mixture of experts that achieved **45–66% improvement** over baseline and surpassed ECMWF's HRES model on some metrics—with a published ICML spotlight paper.

**Ridges AI (SN62)** runs autonomous software engineering agents, scoring via Cerebro—a learning-based system that classifies task difficulty, supervises solutions, and continuously refines the reward model. It achieved 80% on SWE-Bench in 45 days. Its OpenMine portal lets any developer submit agents without crypto complexity.

The five common traits: **(1)** a scoring mechanism that makes gaming harder than doing real work, **(2)** real external users who don't care about TAO, **(3)** a revenue→alpha buyback loop, **(4)** continuous task difficulty escalation, and **(5)** tight alignment between what's measured and what creates value.

---

## Incentive mechanism design: the single most important subnet decision

The Bittensor docs state a foundational principle: **"Subnets should be endlessly improving."** Miners optimize whatever you measure—Goodhart's Law is the central challenge of every subnet. Score CEO Max Sebti puts it bluntly: "Trying to be smart is the worst thing. Good incentive mechanisms have to make sense and really have to be limited to optimizing for one continuous target. Less is more."

The best incentive mechanisms share these properties. First, **scoring functions must never cap improvement**. If the score hits an upper limit, miners stagnate. Second, **tasks must realistically mimic intended user interactions**—synthetic benchmarks that diverge from real use cases lead to miners that are useless in production. Third, **expect 50+ iterations**. BitMind went through three major overhauls and 60+ smaller changes. Score threw away their repo twice. Fourth, **design exploit-proof first, then verify**—Score tested with five different mining teams, sharing different information with each to discover attack vectors before launch.

Common anti-patterns that destroy subnets include measuring only one dimension (a speed-only text subnet gets garbage returned instantly), using static reward components (the OCR tutorial warns that easily predictable invoice positions render position rewards ineffective), launching without adequate testing (Taostats founder Mog warns "when any team tells me they're ready to push their subnet live, they are not ready for what's coming"), and patching exploits reactively instead of redesigning fundamentals.

**For QueryAgent specifically**, the 75% correctness / 15% efficiency / 10% latency split is reasonable but creates a risk: once miners achieve near-perfect correctness on the frozen snapshot (which is deterministic and thus eventually solvable), the remaining differentiation comes from only 25% of the score. The scoring function needs an expansion pathway—either unbounded difficulty scaling or additional scoring dimensions—to prevent convergence at the top.

---

## How dTAO and the flow-based emission model actually work

Dynamic TAO, deployed February 13, 2025, replaced the old root network where ~64 validators manually assigned subnet weights. Now each subnet has its own **alpha (α) token** with a 21M hard cap, own halving schedule, and functions as a constant-product AMM (similar to Uniswap V2): **α price = TAO reserves / α reserves**.

The system evolved through three phases. The initial price-based model (Feb–Nov 2025) allocated emissions proportional to smoothed alpha token prices, but this was gamed—projects artificially pumped prices, collected inflated emissions, then let prices decay. Co-founder Jacob Steeves acknowledged the "TAO Treasury" attack and liquidity asymmetry problems.

The current **flow-based model ("Taoflow")**, launched November 2025, allocates emissions based on **net TAO inflows** from staking. The math works as follows: each block, net flow (TAO staked minus TAO unstaked) feeds into an EMA with a **30-day half-life** (α ≈ 0.000003209, effective ~86.8-day window). Subnets with negative net flows receive **zero emissions**. The smoothed flow is then linearly normalized across all subnets (power exponent p=1, so a subnet with 2× the flow gets exactly 2× the emissions). Each block, **0.5 TAO** (post-halving) is injected into subnet pools proportional to their emission share.

The emission split per subnet is **41% to miners, 41% to validators/stakers, 18% to the subnet owner** (owner portion burned). Validator stake weight equals alpha stake plus TAO stake × 0.18 (the TAO weight parameter), designed to make root TAO staking increasingly irrelevant as alpha supply grows.

**What this means for QueryAgent**: attracting stakers requires demonstrating real value creation. Under TaoFlow, narrative-driven hype is insufficient—sustained positive net TAO inflows require ongoing staker conviction. A revenue→alpha buyback loop (where external query fees purchase alpha tokens) creates structural demand independent of speculative staking. Without external revenue, QueryAgent competes purely on belief, which is unsustainable post-halving when emission scarcity intensifies.

---

## Yuma Consensus mechanics that every subnet builder must understand

Yuma Consensus runs on-chain every **360 blocks (~72 minutes)** per subnet, transforming the validator weight matrix into miner and validator emissions. The critical steps are weight collection, normalization, stake-weighted median computation, clipping, bond calculation, and emission distribution.

The **stake-weighted median** is the core anti-collusion mechanism. For each miner j, the consensus benchmark W̄_j equals the maximum weight level where validators holding at least κ (default 0.5) fraction of total stake assigned weight ≥ that level. Any validator weight above W̄_j is clipped, and the clipped portion earns **zero emissions for both the miner and the validator**. This means a minority coalition (<50% stake) cannot inflate a miner's score.

**Bonds** are the intermediary between stake and yield. Each validator's proportional "ownership" in a miner's emissions evolves via EMA smoothing: `B(t) = α × ΔB + (1-α) × B(t-1)`. In basic mode, α ≈ 0.1 (bonds change ~10% per epoch). With **Liquid Alpha** enabled (recommended), α ranges dynamically from 0.7 to 0.9 based on consensus alignment—validators in consensus build bonds faster, while deviants accumulate slowly. YC3 adds per-bond EMA scaling with configurable sigmoid steepness.

**When there's only one validator** (QueryAgent's likely early state), that validator's weights pass through with no clipping since κ-majority is trivially satisfied. The validator gets 100% of validator emissions and vtrust of 1.0. This is a known edge case—there's no consensus check, meaning the single validator's scoring function is the entire truth. This makes the validator's correctness critical and eliminates the network's natural defense against scoring errors.

**VTrust** (validator trust) measures how closely a validator's weights match consensus. Higher vtrust → higher dividends. Validator dividends equal `VTrust × Stake / Σ(VTrust × Stake)` times total validator emissions. For QueryAgent with one validator, vtrust is always 1.0, but as additional validators join, any scoring discrepancies will reduce vtrust for deviating validators.

---

## Ground truth verification: QueryAgent's hash approach is strong but brittle

Bittensor subnets use four main verification approaches, each with distinct tradeoffs.

**Oracle-based verification** anchors rewards to external, authoritative data feeds. The S&P 500 Oracle subnet scores predictions against actual market prices. Sportstensor verifies against real match outcomes. Strengths: objectively verifiable, manipulation-resistant. Weaknesses: requires waiting for oracle data to mature, limited to domains with external truth sources.

**Hash-based verification** (QueryAgent's approach) uses deterministic operations producing bit-identical outputs verifiable by hash comparison. SHA-256 on frozen Parquet/DuckDB is **perfectly deterministic when the environment is controlled**—same file, same DuckDB version, same query produces identical bytes. Strengths: zero ambiguity (binary pass/fail), computationally trivial to verify, strong gaming resistance. Weaknesses: brittle to any environment drift (DuckDB version, floating-point handling, sort order for ties), no partial credit (a nearly-correct answer scores identically to garbage), and vulnerable to memorization if the query space is finite.

**Model-based verification** uses ML models to evaluate outputs. Targon (SN4) compares logprobs token-by-token. Text prompting subnets combine string literal and semantic similarity. Strengths: handles non-deterministic outputs, captures semantic quality. Weaknesses: reward models are gameable, requires expensive GPU compute on validators.

**Consensus-based verification** uses agreement among multiple participants. Yuma Consensus itself is the ultimate consensus mechanism—outlier evaluations are clipped by the stake-weighted median. Brain (SN90) cross-validates by sending miner answers to other miners for verification.

**QueryAgent's hash approach compared**: The frozen Parquet/DuckDB architecture is one of the strongest verification systems in the Bittensor ecosystem because it eliminates evaluation subjectivity entirely. However, three critical mitigations are needed: **(1)** pin exact DuckDB version across all participants, **(2)** require explicit ORDER BY on unique keys in all queries and use DECIMAL types for exact arithmetic, and **(3)** implement randomized query generation to prevent lookup-table attacks.

---

## Anti-gaming: the arms race that never ends

The most common gaming vectors on Bittensor are **weight copying** (validators duplicating others' weights instead of evaluating independently), **result memorization** (miners pre-computing answers to predictable queries), **model/output copying** (miners sharing backends or running identical models on multiple UIDs), and **Goodhart's Law exploitation** (optimizing the measured metric rather than the intended objective).

**Commit-reveal** (introduced v7.3.0, July 2024) is the primary defense against weight copying. Validators submit time-lock encrypted weight hashes that remain hidden for a configurable number of tempos. Copiers accessing only stale weights from previous tempos get punished when miner performance shifts. However, **commit-reveal only works if miner rankings change during the concealment period**. If rankings are static—as they could be on a frozen snapshot where miners memorize answers—stale weights remain accurate, and copying stays profitable.

For QueryAgent, this creates a critical design requirement: **the query pool must continuously evolve**. Rotating queries, randomized parameterization, and new snapshot versions must ensure that miner rankings shift frequently enough to make weight copying unprofitable. Additional measures from top subnets include: unique challenges per miner (Dojo sends uniquely obfuscated responses), validator-provided random seeds, timing constraints that make relay impractical, and statistical anomaly detection for suspicious response patterns.

An arXiv analysis (2507.02951v1) of 64 active subnets found that **rewards are overwhelmingly driven by stake rather than performance**, with performance scores only weakly correlated with actual earnings. This systemic issue means QueryAgent should design for clear, measurable performance differentiation that generates genuine variance in miner scores—a narrow score distribution makes the system effectively stake-driven regardless of mechanism quality.

---

## Task design determines whether miners innovate or stagnate

Successful subnets generate tasks through three methods: **synthetic/algorithmic generation** (validators create challenges procedurally—the OCR subnet uses Python Faker to generate synthetic invoices), **LLM-generated tasks** (SN1 validators use LLMs to create prompts and reference answers), and **organic queries** (real user requests routed through validators). The best subnets blend all three.

Task difficulty must scale continuously. The official docs emphasize: "The task should be designed to capture the intended use case for the commodity to be produced by the subnet." For query complexity scaling, subnets use several approaches: the OCR subnet gradually increases noise levels, SN1 increases persona corruption of instructions, and scoring functions evolve over time to raise the bar. The key insight is that **competition naturally drives difficulty**—if most miners solve easy tasks equally, the scoring model must ensure harder tasks provide greater differentiation.

**For QueryAgent**, task design presents both opportunity and risk. A blockchain analytics query can range from trivial (`SELECT COUNT(*) FROM transactions`) to expert-level (multi-join queries with window functions, CTEs, and chain-specific logic). The query generator should implement **tiered difficulty** where harder queries carry more weight in scoring. Critically, queries should be **parameterized and randomized**—the same query template with different addresses, date ranges, and thresholds prevents memorization while testing the same SQL generation capabilities.

---

## Data freshness: the unique challenge of analytics subnets

No major Bittensor data subnet uses frozen Parquet snapshots as its primary data model. SN13 (Data Universe) uses continuous scraping with a strict policy: **data older than 30 days scores zero**. SN15 (Blockchain Insights/BitQuant) runs full blockchain nodes with continuous ingestion. SN82 (Hermes by SubQuery) uses live indexing frameworks.

QueryAgent's frozen snapshot approach is architecturally novel in the Bittensor ecosystem. The advantage—perfect deterministic verification—is significant. But the tradeoffs need management. The recommended architecture is a **hybrid approach**: use frozen snapshots for verification/scoring (ensuring determinism), but signal value for freshness. Snapshots should rotate on a defined schedule, ideally **every 4–6 hours** for recent data, with older historical data using daily or weekly snapshots. Each snapshot should be tagged with a block height cutoff and distributed via HuggingFace or IPFS with SHA-256 checksums in a manifest file.

DuckDB handles Parquet impressively well at scale—tested up to **2 TB with peak memory under ~2.5 GB**, with optimal file sizes of 100 MB to 10 GB per file and row groups of 100K–1M rows. For QueryAgent, Hive-format partitioning by chain and date, combined with zstd compression, would dramatically improve query performance while keeping file sizes manageable.

**Critical risk**: snapshot rotation coordination. Validators on different snapshot versions will compute different hashes, causing false negatives. Mitigation: implement a grace period where both old and new snapshots are accepted, with validators checking snapshot hash in a manifest before scoring.

---

## Miner onboarding and validator design determine early survival

The official Bittensor docs are explicit: "To attract high-performing subnet miners and subnet validators, make sure that you publish sufficient documentation. Good docs are important!" Top subnets provide hardware requirements tables, step-by-step setup instructions from wallet creation through registration, scoring criteria transparency, and working baseline miner implementations that new miners can fork and improve.

**Bootstrapping early participation** relies on several mechanisms: the `immunity_period` hyperparameter gives new miners a grace period before deregistration risk, subnet owners register the first miner and validator keys, and testnet-first development allows mechanism validation before mainnet stakes. The Ideathon explicitly evaluates "bootstrapping strategies for miners, validators, and users."

For validator design, the core architecture follows a loop: generate challenge → query miners via Dendrite (batch, concurrent) → score responses → update EMA scores → set weights on-chain. Critical edge cases include handling UID changes (the metagraph is one epoch outdated at weight-setting time, so newly registered keys inherit the previous key's stats), hardware variance affecting output, and partial/timed-out responses (non-responsive miners receive zero scores, with EMA smoothing preventing a single timeout from zeroing a miner's accumulated reputation).

**QueryAgent needs** a reference miner implementation that works out-of-the-box against the current snapshot, clear SQL generation requirements (what schema knowledge is needed, what output format is expected), explicit DuckDB version pinning, and a gradual difficulty ramp that lets new miners earn some rewards while learning the system.

---

## External value creation separates surviving subnets from dead ones

Under TaoFlow, the existential question is: "Would anyone use this service if TAO emissions stopped tomorrow?" Subnets with real external value create a **structural demand flywheel**: external users pay for service → revenue purchases alpha tokens → alpha price rises → stakers earn returns → more staking → higher emissions → more resources for better service.

Chutes has 400,000+ users who mostly don't know they're on Bittensor. Nineteen AI set a world record for fastest LLM inference. BitMind has a deepfake detection app live on app stores. Gradients has trained 118+ trillion parameters for AI customers. These subnets generate revenue **independent of TAO emissions**.

The Crucible Labs framework classifies subnets along two axes: research-oriented versus service-oriented, and intelligence-focused versus resource-focused. **Service-oriented subnets with product-market fit** are the highest-value category because they allow validators to monetize their bandwidth—the only way an external user can query a subnet is through a validator's hotkey, making validators natural API gateways.

**For QueryAgent**, the external value proposition is clear: natural-language blockchain analytics. Dune Analytics has 1,500+ paying customers and handles 3+ petabytes of data. Flipside Crypto covers 26+ blockchains. The market for SQL-based blockchain analytics is proven—but QueryAgent needs an **API gateway** where external developers can submit plain-English questions and receive SQL-generated answers, independent of any knowledge of Bittensor. This API should be monetized, with revenue flowing into alpha buybacks.

---

## What Ideathon judges are evaluating on March 31, 2026

The Bittensor Subnet Ideathon (HackQuest × OpenTensor Foundation) is the first-ever global subnet competition, attracting 565+ participants with ~$23K in direct prizes plus potential investment of up to **1,000 TAO (~$260,000)** from Unsupervised Capital. Round II (testnet phase, March 8–30, 2026) requires functional implementations with results announced March 31.

The Hackathon Winner ($10,000) is judged on five criteria, listed in priority order: **(1)** quality and robustness of incentive and mechanism design, **(2)** clear definition of miner/validator roles, tasks, and evaluation logic, **(3)** relevance and credibility of the use case within the Bittensor ecosystem, **(4)** consistency between proposed design and observed testnet behavior, and **(5)** overall coherence of idea, execution, and outcomes.

The Hackathon Runner-Up ($3,000) focuses on engineering quality: functional correctness, reliability of miner-validator interactions, architecture choices, and operational soundness on testnet. The five Subnet Ideathon Awards ($1,000 each) prioritize novelty—originality of incentive/scoring/coordination design, clarity of mechanism logic, evidence from testnet that the mechanism works, and potential impact on future subnet design.

The explicit instruction for Round II states: **"Polish is not necessary, but functional correctness and conceptual integrity are required."** This means judges want to see that the core mechanism works on testnet—miners produce outputs, validators correctly evaluate and score, and the incentive mechanism distributes rewards as designed—without requiring production-ready UI or comprehensive documentation. The code must run without critical failures.

**What separates Top 7 from Honorable Mentions**: strong emission/reward logic with clear incentive alignment, robust anti-adversarial mechanisms (explicitly required: "mechanisms to discourage low-quality or adversarial behavior"), compelling competitive analysis (both within and outside Bittensor), and a plausible path to long-term adoption. Honorable mentions typically have solid concepts but lack differentiated competitive positioning, robust anti-gaming measures, or clearly articulated business sustainability.

---

## Fourteen specific gaps QueryAgent should close

Based on the comprehensive research above, here are the actionable gaps ordered by impact.

**Gap 1: No organic query pathway.** Every top subnet blends real external queries into validation. QueryAgent should build an API gateway where external users submit natural-language blockchain questions, with these organic queries mixed into the validation flow alongside synthetic challenges. This simultaneously creates revenue and prevents overfitting to synthetic benchmarks.

**Gap 2: Binary scoring prevents continuous improvement.** Hash-based verification produces pass/fail results—a miner that returns 999 of 1,000 correct rows scores identically to one returning garbage. Implement **partial credit** by hashing result subsets (e.g., hash the first N rows, hash column subsets) and using semantic similarity for SQL structure comparison alongside exact-match scoring.

**Gap 3: Memorization vulnerability from predictable queries.** If the query space is finite or templated, miners will build lookup tables mapping query→hash. Implement **parameterized query templates** with randomized addresses, date ranges, token amounts, and block ranges. Use validator-provided random seeds. Ensure the combinatorial space is large enough that precomputation is impractical.

**Gap 4: No revenue→alpha buyback loop.** Top subnets (Chutes, Nineteen, Zeus) convert external revenue into alpha token purchases, creating structural demand. QueryAgent needs a monetization path—even a simple pay-per-query API where fees auto-stake into alpha purchases would differentiate it from emissions-only subnets.

**Gap 5: Missing task difficulty progression.** The scoring function should weight harder queries more heavily. Implement tiered difficulty: simple aggregations (easy), multi-table joins (medium), window functions with CTEs and chain-specific logic (hard). Harder tiers should carry **disproportionately higher scores** to differentiate top miners.

**Gap 6: Snapshot coordination risk.** Without a formal snapshot versioning and distribution protocol, validators may evaluate miners against different data, causing hash mismatches. Implement a manifest system: publish snapshot checksums at defined block heights via HuggingFace/IPFS, with a grace period during rotation where both old and new snapshots are accepted.

**Gap 7: No commit-reveal enabled.** Without commit-reveal, weight copying is trivially profitable. Enable it immediately with a commit_reveal_period of at least 3–5 tempos. Combine with continuous query rotation to ensure miner rankings shift during the concealment period.

**Gap 8: Single-validator fragility.** With one validator, there's no consensus-based error correction. A bug in the validator's scoring logic becomes undetectable network truth. Prioritize onboarding a second independent validator, or implement self-checking mechanisms (validator runs scoring twice with different parameters to verify consistency).

**Gap 9: No DuckDB version pinning.** Any difference in DuckDB version, floating-point handling, or sort order produces different hashes. Mandate an exact DuckDB version in all participant requirements. Require explicit ORDER BY on unique keys. Use DECIMAL types for arithmetic.

**Gap 10: Insufficient efficiency scoring granularity.** The 15% efficiency component needs clear metrics: query execution time in DuckDB, number of rows scanned, memory usage. Consider using DuckDB's EXPLAIN ANALYZE to extract actual execution metrics and score based on query plan quality, not just result correctness.

**Gap 11: No multi-chain scaling roadmap.** Top data subnets (SN13 covers Twitter/Reddit/YouTube; Dune covers 100+ chains) succeed by expanding coverage. QueryAgent should have a clear roadmap from single-chain to multi-chain, with each new chain adding snapshot complexity but also broader market appeal.

**Gap 12: Missing baseline miner implementation.** Top subnets provide working reference miners that new participants can fork. QueryAgent needs a baseline miner that uses a simple SQL generation approach (even rule-based or template-based) against the current snapshot, with clear documentation of the schema and expected output format.

**Gap 13: No external value demonstration for judges.** The Ideathon explicitly evaluates "relevance and credibility of the use case." QueryAgent should demonstrate a working end-to-end flow: natural-language question → miner generates SQL → validator verifies on DuckDB → correct answer returned to user. A simple web demo showing this loop would powerfully demonstrate external value.

**Gap 14: EMA smoothing may mask rapid improvement.** QueryAgent's EMA smoothing interacts with Yuma Consensus's own EMA bond smoothing. If both smoothing rates are conservative, a genuinely improved miner takes too long to see reward increases, reducing the incentive to innovate. Tune the subnet-level EMA alpha to be responsive enough that improvements are rewarded within 2–3 epochs while still filtering noise.

---

## Conclusion: QueryAgent's path from sound architecture to competitive subnet

QueryAgent's core architecture—hash-based verification on frozen Parquet snapshots with DuckDB—is one of the most deterministic and manipulation-resistant verification systems possible on Bittensor. The 75/15/10 scoring split across correctness, efficiency, and latency creates meaningful multi-dimensional competition. But technical soundness alone doesn't win in the post-dTAO era where **3,600 TAO per day** is split across 128 subnets competing for staker attention.

The highest-impact improvements are external: an API gateway for non-Bittensor users, a revenue→alpha buyback mechanism, and a compelling demo showing natural-language blockchain analytics working end-to-end. The highest-impact technical improvements are internal: parameterized query randomization to defeat memorization, progressive difficulty tiers weighted toward expert-level SQL, and formal snapshot versioning with coordinated rotation.

The Ideathon's top criterion—"quality and robustness of incentive and mechanism design"—rewards exactly the kind of clean, deterministic verification that QueryAgent already has. What judges will scrutinize is whether the mechanism **drives continuous miner improvement** or allows convergence and stagnation. The answer depends entirely on whether the query pool is unbounded enough, the difficulty scales aggressively enough, and the anti-gaming measures are robust enough to keep the competitive pressure on miners indefinitely. The subnets that survive on Bittensor are the ones where doing real work is always easier than cheating—and where the work itself creates value that someone outside the network is willing to pay for.
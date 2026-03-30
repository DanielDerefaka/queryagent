# What Makes a Good Subnet — Patterns, Const's Advice, and Evaluation Framework

## Const's (Bittensor Founder) Core Philosophy

> "Bittensor is a programmable incentive computer which you can direct to solve any well defined problem faster, and more impressively, than was ever possible."

### Critical Success Factors (from @const_reborn)

1. **Be Very Specific and Metric Focused**
   - "You are the intelligence creating the evaluation heuristic for intelligence"
   - Best approach: use machine intelligence itself to evaluate
   - Based on computational asymmetry: P ≠ NP — determining if something is good is easier than creating it

2. **Incentive Design Requires Paranoia**
   - Assume everyone will try to exploit your system
   - Design exploit-proof mechanisms
   - Expect 50+ iterations to get right

3. **Three Success Phases**
   - Phase 1: Technical validation (prove it works)
   - Phase 2: Convince TAO holders (get stake)
   - Phase 3: Build revenue-generating company (show real utility)

4. **Target Scalable Demand**
   - Solve measurable AI problems
   - Focus on areas Big Tech ignores
   - Create genuine economic value

5. **Team Composition**
   - Lean teams of 3-5 expert people
   - Constant evolution beats stagnation
   - Experienced in AI and Web3

---

## Subnet Evaluation Framework

### Two Axes
1. **Objective**: Research-oriented ↔ Service-oriented
2. **Coordination**: Intelligence-focused ↔ Resource-focused

**Best position**: Service-oriented + Intelligence-focused (e.g., Chutes, IOTA, Ridges)

### Infrastructure vs. Application
| Type | Examples | Characteristics |
|------|----------|----------------|
| **Infrastructure** | Chutes, Affine, SN1 | Provide backend others use. First-mover advantage. Higher value. |
| **Application** | SN15, SN28, SN29 | Direct competition with established players. Need unique data/expertise. |

**QueryAgent sits in between** — infrastructure (analytics oracle for other subnets) + application (user-facing chat interface)

---

## What Stakers and Validators Look For

1. **Mechanism Design Quality** — simple, clear, resistant to gaming
2. **Team Track Record** — proven delivery, public team, regular updates
3. **Real-World Utility** — solving genuine problems, generating revenue
4. **Validator Trust Score** — consensus alignment (honest evaluation)
5. **Subnet Health** — positive TAO flows, growing participation
6. **Economic Alignment** — performance-weighted rewards, low variance

---

## Anti-Gaming Best Practices (from successful subnets)

1. **Code-Level Obfuscation** — each miner receives uniquely obfuscated responses
2. **Feedback Permutation** — combinatorial permutations make Sybil attacks uneconomical
3. **Weight Clipping** — Yuma clips generous validators to match least generous
4. **DDoS Shield** — assign unique validator address to miners
5. **Volume Accountability** — penalize miners for missed queries
6. **Randomization** — randomize task selection, parameters, evaluation timing

---

## Questions to Validate Subnet Quality

Use these as a self-check for QueryAgent:

### Mechanism Design
- [ ] Can scoring be gamed without doing genuine work?
- [ ] Is evaluation objective (not opinion-based)?
- [ ] Does competition actually improve the output?
- [ ] Can any third party verify results independently?
- [ ] Are there multiple layers of anti-gaming?

### Economic Viability
- [ ] Who are the real users (not just miners)?
- [ ] Why would someone stake TAO into this subnet?
- [ ] Can the subnet generate revenue beyond emissions?
- [ ] Is the market large enough to sustain growth?

### Technical Feasibility
- [ ] Can the reference miner run on modest hardware?
- [ ] Is the snapshot/data pipeline practical?
- [ ] Can validators run scoring without expensive infrastructure?
- [ ] Is the system deterministic and reproducible?

### Competitive Position
- [ ] How is this different from existing subnets (Hermes, SN15)?
- [ ] What unique advantage does this have?
- [ ] Can this be the #1 subnet in its category?

---

## QueryAgent Self-Assessment

| Question | Answer |
|----------|--------|
| Objective evaluation? | **YES** — hash comparison is binary, deterministic |
| Can be gamed? | **Hard** — hidden tasks, parameterization, snapshot rotation, DuckDB sandbox |
| Real users? | **TBD** — need to attract analytics users and subnet teams |
| Revenue model? | **TBD** — API access, query packs, SDK licensing |
| Competitive edge? | **YES** — only system with frozen snapshots + hash verification + full reproducibility |
| Modest hardware? | **YES** — DuckDB runs on CPU, no GPU needed |
| Deterministic? | **YES** — frozen Parquet + DuckDB = same result every time |

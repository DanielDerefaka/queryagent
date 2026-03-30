# Successful Bittensor Subnets — What Makes Them Work

## Top Subnets (2025-2026)

### SN64 — Chutes (Serverless AI Compute)
- **First subnet to hit $100M** milestone (9 weeks after dTAO launch)
- 30 billion tokens/day, 100,000+ API users
- 85% lower cost than AWS
- Revenue: $2.4M annually projected
- **Why it works**: Real compute demand, clear cost advantage, massive user base

### SN4 — Targon (Multi-Modality Inference)
- Revenue projections: $10.4M annually
- Multi-modal AI inference
- **Why it works**: Addresses genuine inference demand at scale

### SN62 — Ridges AI (Autonomous Coding)
- Fixes bugs, writes tests, ships code
- "Cerebro" system for task classification and reward refinement
- **Why it works**: Clear success criteria (code works or doesn't), evolutionary approach

### SN9 — IOTA (Pretraining)
- Largest pretraining effort on Bittensor
- Miners train 700M-14B parameter models, upload to HuggingFace
- Validators download and evaluate against Falcon dataset
- Outperforms DeepSeek, Mistral, Google on multiple benchmarks
- **Why it works**: Objective loss-based scoring, public model hosting, clear iteration path

### SN1 — Prompting (Text Generation)
- Foundational subnet by OpenTensor Foundation
- Challenge-response: validators generate prompts with reference answers
- Miners scored by alignment with ground truth
- **Why it works**: Backed by OTF, diverse task types, trusted reference answers

### SN82 — Hermes (Analytics) — OUR COMPETITOR
- GraphQL queries for blockchain data
- Validators create synthetic GraphQL challenges from project schemas
- Miners scored on accuracy + latency
- Partnership with Polymarket for oracle services
- **Why it works**: Real on-chain data as ground truth, objective evaluation

### SN15 — Blockchain Insights — OUR COMPETITOR
- Natural language → SQL/Cypher queries
- Graph-based analytics (Neo4j/Memgraph)
- LLM transforms user questions to queries
- **Challenge**: LLM hallucination requires rigorous validation

### SN13 — Data Universe (Data Scraping)
- 350M rows/day from X, Reddit
- Validators serve external requests for revenue
- **Why it works**: External revenue generation model

### SN120 — Affine (Infrastructure Orchestration)
- Connects multiple subnets (Chutes, Ridges, others)
- Infrastructure layer enabling interoperability
- **Why it works**: First-mover in cross-subnet orchestration

---

## Patterns of Success

### 1. Objective Evaluation
- Ground truth from: datasets (SN9), APIs (SN1), query results (SN82), on-chain data (SN15)
- Harder to game when evaluation is objective, not subjective
- **QueryAgent fits perfectly** — hash comparison is maximally objective

### 2. Real-World Utility
- Solving problems Big Tech ignores
- Generating actual revenue (not just emissions)
- Attracting genuine users beyond just miners
- **QueryAgent needs**: Real analytics users who care about verified answers

### 3. Ecosystem Synergy
- SN9 (pretrain) → SN37 (fine-tune) → SN64 (inference) → SN120 (orchestrate)
- Subnets feeding outputs into other subnets
- **QueryAgent opportunity**: Be the analytics layer other subnets consume

### 4. Experienced Teams
- AI expertise + Bittensor knowledge + proven delivery
- Public teams (not anonymous)
- Regular communication and updates

### 5. Clear Metrics
- Simple, specific (loss, accuracy, latency, correctness)
- Avoid fuzzy metrics like "quality" or "usefulness"
- Machine intelligence evaluating intelligence

### 6. Low Entry Barriers
- Easy for miners to participate
- Clear hardware requirements
- Good documentation + reference implementations
- **QueryAgent**: CPU-friendly baseline miner is a strong selling point

---

## Common Failures — Why Subnets Die

1. **No genuine user demand** — without real users staking, dTAO gives zero emissions
2. **Poor incentive mechanism** — gameable, miners optimize for tricks not work
3. **High entry barriers** — expensive hardware, poor docs, complex setup
4. **Bad positioning** — competing directly with AWS/Google on cost
5. **Lack of validator support** — no top validators = no trust
6. **No revenue model** — can't sustain on mining emissions alone
7. **Weak team credibility** — unknown, anonymous, no track record

---

## QueryAgent vs. Competitors

| Dimension | Hermes (SN82) | SN15 | QueryAgent |
|-----------|---------------|------|------------|
| Query type | GraphQL | Cypher/SQL | Standard SQL |
| Data state | Live | Live | Frozen snapshots |
| Reproducibility | Limited | Limited | Full (deterministic) |
| Verification | Accuracy scoring | Validator check | Re-execution + hash match |
| Ground truth | Schema-derived | API comparison | Pre-computed hashes |
| Decentralized | Yes | Yes | Yes |

**Our edge**: Frozen snapshots + hash verification = the only system where ANY third party can independently verify ANY answer.

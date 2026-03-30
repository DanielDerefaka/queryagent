# QueryAgent — Investor Pitch Prep

---

## What Investors Care About

1. Is the market big enough?
2. Why will people pay for this?
3. Why can't someone else just copy it?
4. What have you actually built?
5. How do you make money?
6. What do you need from me and what do I get?

Structure everything around these questions.

---

## Pitch Flow (15-20 min, leave 10+ for Q&A)

### 1. Open with the Problem (2 min)

"There's $50B+ in on-chain data across blockchains. The tools to access it are broken."

- **Dune Analytics** (valued ~$1B) requires SQL — eliminates 95% of crypto users
- **Nansen** charges $99-$999/month for pre-built dashboards — no custom questions
- **Flipside** killed their SQL product to go AI-only — alienated power users
- Everyone is centralized — you trust the platform, zero verifiability
- No one has solved: let anyone ask anything AND prove the answer is correct

"We're building the Google of blockchain data — except every answer comes with cryptographic proof."

### 2. The Solution (3 min)

**QueryAgent: Ask blockchain questions in plain English. Get verified answers.**

Keep it simple:
- User asks a question (no SQL, no code)
- A decentralized network of miners races to answer
- Validators independently verify every answer using hash-based proof
- Correct miners earn rewards. Wrong miners earn nothing.
- User gets a verified answer with proof they can check themselves

"Think of it as Perplexity for blockchain data, but decentralized and verifiable."

### 3. Why This Wins — The Moat (3 min)

**Network effects + verification = unkillable moat.**

- Every new miner makes the network faster and more accurate
- Every new query makes the task pool smarter (adaptive difficulty)
- The verification layer is the moat — no centralized competitor can offer cryptographic proof of results
- Built on Bittensor — we inherit a $3B+ network with existing miners, validators, and TAO token economics
- First mover in verified blockchain analytics as a subnet

**vs Dune:** They can add AI. They can't add decentralized verification.
**vs Nansen:** They sell dashboards. We sell answers to any question.
**vs ChatGPT/Perplexity:** They hallucinate. We verify.

### 4. Show the Product (5 min)

**Show, don't tell. This is where you prove it's real.**

a) **Frontend** — open localhost:3000
- "This is what users see. Ask a question, get a verified answer."
- Show the Ask page, type a question, show results flowing

b) **The engine underneath** — quick terminal view
- Miner receiving a question, generating SQL in 198ms, returning a hash
- Validator verifying the hash, scoring the miner, setting weights on-chain
- "This is live. Real computation, real verification, real incentive."

c) **On-chain proof** — one command
- `btcli subnet show` — show the miner earning TAO
- "This miner started with 0 stake. It's now at 103 TAO because it answers correctly. That's the incentive working."

Don't spend more than 5 minutes here. Show it works, move on.

### 5. Revenue Model (2 min)

**Three revenue streams:**

| Stream | How | When |
|--------|-----|------|
| **API fees** | Developers pay per query (metered API) | At launch |
| **Pro subscriptions** | Private queries, scheduling, priority execution, team dashboards | Month 2-3 |
| **Data marketplace** | Premium datasets, custom indexes, enterprise feeds | Month 6+ |

**The flywheel:**
- API fees → buy subnet alpha token → increases emissions → attracts more miners → better answers → more users → more fees

"Dune does $20M+ ARR selling SQL access. We're selling the same data access but to everyone, not just SQL developers. The addressable market is 10x larger."

### 6. Traction (2 min)

- Full incentive loop working — miner earning TAO on live testnet
- 124+ tests passing (including adversarial/security tests)
- 3 miner strategies built (template, LLM, hybrid)
- Advanced to Round II of Bittensor Subnet Ideathon — Honorable Mention out of 150+ projects
- Frontend prototype built (landing, query interface, leaderboard)
- Whitepaper, mechanism design, and scoring system fully specified

"We're pre-revenue but post-product. The hardest part — making the verification work — is done."

### 7. The Ask (2 min)

Be specific:
- How much you're raising
- What it's for (infra, team, go-to-market)
- What milestones it gets you to
- What the investor gets

Example structure:
```
"We're raising $XXX to get to mainnet launch + first 1,000 users.

Funds go to:
- 40% Engineering (full-time devs, infra, multi-chain indexing)
- 30% Go-to-market (developer relations, crypto community, partnerships)
- 20% Operations (cloud, API infrastructure, data pipeline)
- 10% Buffer

Milestones this gets us to:
- Mainnet subnet live on Bittensor
- Public API with 1,000+ monthly active developers
- 3+ chains indexed (Bittensor, Ethereum, Solana)
- $XX MRR from API fees
```

---

## Before the Call — Checklist

### 15 Minutes Before
- [ ] Docker running with local chain
- [ ] Miner running in one terminal
- [ ] Validator running in another terminal
- [ ] Frontend on localhost:3000
- [ ] `btcli subnet show --netuid 2` ready to copy-paste
- [ ] Close Slack, notifications, personal browser tabs
- [ ] Google Meet link tested, camera + mic working
- [ ] Share a specific window (not full desktop)

### Have Open (not shown until needed)
- Pitch Deck PDF as backup
- TESTNET_REPORT.md for detailed numbers if asked
- This prep doc for Q&A reference

---

## Q&A Prep — What They'll Ask

**"What's your competitive advantage?"**
Verification. Every answer is hash-proven. No centralized platform can offer this because they'd have to decentralize their compute layer. We get it for free from Bittensor. Plus — we're building the mining network. Every new miner makes the product better. That's a network effect competitors can't replicate.

**"Why Bittensor and not your own infra?"**
Bittensor gives us: a $3B+ token economy, existing mining infrastructure, Yuma Consensus for trustless scoring, and TAO as the incentive. Building this from scratch would cost millions and years. We're building on top of proven infrastructure.

**"How do you acquire users?"**
1. Developer API (like Dune's API but for everyone) — devs integrate into their apps
2. Free web interface for casual users — "just ask a question"
3. Crypto community / Twitter — blockchain data people already want this
4. Bittensor ecosystem — 30+ subnets, built-in community of miners and validators

**"What if Dune adds natural language?"**
They probably will. But they still can't verify results. Their answers come from centralized servers — you trust Dune. Our answers come with SHA-256 proof from independent validators. That's the moat. Also — Dune has no miner incentive. Our miners are economically motivated to improve.

**"What if OpenAI/Perplexity does this?"**
They don't have on-chain data indexed. They hallucinate financial data. And they can't prove their answers are correct. We can. "AI that's verifiable" is a category, not a feature.

**"How do you prevent miners from cheating?"**
- Hash-based verification: validators independently re-execute every SQL query
- Hidden tasks: miners have never seen 15 of our 35 tasks
- Parameterized injection: same question template, different values each round
- SQL sandboxing: miners can't run destructive queries
- EMA smoothing: one lucky round can't game the score

**"What are the risks?"**
Be honest:
- Bittensor dependency — if the network has issues, we're affected
- Data freshness — currently monthly snapshots, need to increase frequency
- LLM costs — complex queries use GPT-4o, need to optimize or fine-tune
- Market timing — crypto analytics market is competitive

**"Who's on the team?"**
Talk about yourselves. What's your background? Why are you the right people? What relevant experience do you have?

**"What's the timeline to revenue?"**
Be realistic. If you can say "3-6 months to mainnet + API launch with first paying users" that's strong. Don't overpromise.

---

## Numbers to Know Cold

| Metric | Value |
|--------|-------|
| TAM | $5B+ blockchain analytics market (growing 20%+ YoY) |
| Dune valuation | ~$1B (Series B, 2022) |
| Dune ARR | ~$20M+ |
| Nansen pricing | $99-$999/month |
| Bittensor market cap | ~$3B+ |
| Our tests | 124+ passing |
| Miner accuracy (template) | 60% (12/20) |
| Miner accuracy (hybrid) | 60%+ with LLM fallback |
| Testnet miner earnings | 0 → 103 TAO in minutes |
| Task pool | 35 tasks (20 public + 15 hidden) |
| Scoring | 75% correctness / 15% efficiency / 10% speed |
| Competition | Honorable Mention out of 150+ projects |

---

## What NOT to Do

1. **Don't lead with tech** — investors don't care about DuckDB or Parquet files. Lead with the problem and market.

2. **Don't explain Bittensor for 10 minutes** — say "decentralized AI network worth $3B+, we're building on top of it" and move on. Only go deeper if they ask.

3. **Don't demo for too long** — 5 minutes max. Show it works, prove it's real, get back to the business.

4. **Don't be vague about money** — know exactly how much you want, what it's for, and what milestones it hits.

5. **Don't trash competitors** — say "Dune is great for SQL developers. We're going after the 95% who can't write SQL."

6. **Don't say "we just need to build X"** — show what you've ALREADY built. The testnet working is your strongest asset.

---

## Opening Line Options

Pick one that fits your style:

> "Every day, billions of dollars move on-chain. The tools to understand that data require SQL — a language 95% of crypto users don't speak. We're fixing that."

> "Dune Analytics is a billion-dollar company that serves SQL developers. We're building the version that serves everyone — with every answer cryptographically verified."

> "We built a system where you ask a blockchain question in English, and a decentralized network of miners races to give you a proven answer. It's working today on testnet."

# QueryAgent — Video Script

> **How to use:** Share your screen with the pitch deck open. Talk through each slide like you're explaining to a friend who's smart but has never heard of Bittensor. Keep it casual. Don't read — just talk.
>
> **Target:** ~5 minutes

---

## SLIDE 1 — Title (0:00 – 0:15)

> Hey, what's up everyone. I'm here to tell you about QueryAgent.
>
> In simple terms — we're building a system where AI agents answer blockchain data questions, and every single answer can be proven correct. Let me show you how.

---

## SLIDE 2 — The Problem (0:15 – 1:00)

> So let's start with the problem.
>
> Right now, if you want to know something about what's happening on a blockchain — like how much TAO got staked last week, or which subnet is growing the fastest — you go to an analytics tool and it gives you a number.
>
> But here's the thing. You have no idea if that number is right. You just trust it. There's no receipt. There's no proof.
>
> And it gets worse — if you ask the same question tomorrow, you might get a different answer, because the data underneath changed. So you can't even go back and check.
>
> Teams are spending hours writing SQL, debugging queries, double-checking numbers manually. It's slow, it's painful, and at the end of the day — you still can't prove your answer is correct.
>
> That's the real problem. Not access to data. Trust in the answer.

---

## SLIDE 3 — The Solution (1:00 – 1:50)

> So what does QueryAgent actually do?
>
> Think of it like this. You ask a question in plain English — like "which subnets earned the most emissions this week?" — and an AI agent writes the SQL query for you, runs it, and gives you the answer.
>
> But here's what makes it different from everything else. That answer comes with proof. The AI ran the query on a frozen copy of the data — a snapshot that never changes. And it attached a hash — basically a fingerprint — of the result.
>
> Then a separate player, called a validator, takes that same SQL, runs it again on the same frozen data, and checks if the fingerprint matches. If it does — the answer is verified. If it doesn't — the AI scores zero. No excuses.
>
> So every answer you get from QueryAgent is reproducible. Anyone can download the same snapshot, run the same SQL, and get the same result. That's the whole point.

---

## SLIDE 4 — What is Onchain Analytics (1:50 – 2:20)

> Real quick — what do we mean by onchain analytics?
>
> All the activity on a blockchain — transactions, staking, wallet movements, validator changes — that's all public data. It's sitting right there on the chain.
>
> But it's raw. It's like having a giant spreadsheet with millions of rows and no charts. Not very useful by itself.
>
> Onchain analytics just means turning that raw data into actual answers. "What happened last week?" "Who's growing?" "Where's the money flowing?" That's what teams need to make decisions.
>
> The tools that exist today can do this — but you can't verify their answers. That's where we come in.

---

## SLIDE 5 — Features (2:20 – 2:55)

> So what do you actually get with QueryAgent?
>
> You get a chat — ask questions in plain English, get answers backed by real SQL and real data. Not a guess. Not a black box.
>
> Every answer is a Verified Answer Package — it comes with the query, the snapshot it ran on, and a fingerprint you can check yourself.
>
> Multiple AI agents compete on every question. The best one — most accurate, most efficient — gets rewarded. So quality keeps getting better over time.
>
> You can also automate it — set up recurring questions like a weekly report, running on the same snapshot every time so your comparisons are clean.
>
> And you get artifacts — charts, tables, reports — all generated from verified data. Not vibes. Verified data.

---

## SLIDE 6 — How It Works (2:55 – 4:05)

> OK this is the important part. Let me break down how the whole thing actually works. Four steps.
>
> **Step one — we freeze the data.** Before anything happens, we take a snapshot of the blockchain data. Think of it like taking a photo. That photo is locked — it never changes. So no matter when you ask a question, you're always looking at the same picture. That's what makes everything reproducible.
>
> **Step two — a question gets asked.** The validator picks a question from our task pool and sends it out to all the miners at the same time. The question comes with a reference to which snapshot to use, and we already know what the correct answer's fingerprint looks like. That's our ground truth.
>
> **Step three — miners do the work.** Each miner is an AI agent running on its own server. It takes the question, writes SQL to answer it, runs that SQL on its local copy of the snapshot, and then packages up everything — the SQL it wrote, the result, a fingerprint of the result, and a short explanation. Then it sends that back. The key thing here — the miner can't fake it. The SQL has to actually run and produce a real result.
>
> **Step four — validators check the work.** The validator takes the miner's SQL, runs it again on the same snapshot, computes its own fingerprint, and compares it to the known correct answer. If the fingerprints match — the miner is correct and gets scored. If they don't match — zero points. No partial credit. Then the scores get recorded on the blockchain, and the best miners earn TAO.
>
> That's it. Question goes in, verified answer comes out. No trust needed anywhere.

---

## SLIDE 7 — Market Opportunity (4:05 – 4:25)

> And the market for this is massive. Blockchain analytics is a 4.4 billion dollar market today, headed to 14 billion by 2030.
>
> Protocols, subnet teams, researchers, compliance firms — they're all paying for analytics already. Premium tools charge up to 2,000 a month.
>
> The demand exists. What doesn't exist yet is a version where you can actually verify the answers. That's the gap we're filling.

---

## SLIDE 8 — Why Bittensor (4:25 – 4:45)

> Why build this on Bittensor?
>
> Because Bittensor is built for exactly this kind of thing — tasks where you can objectively measure who did the best work. And analytics is a perfect fit. Either your SQL produces the right answer or it doesn't. There's nothing subjective about it.
>
> Plus, the incentives are built in. Miners compete, the best ones earn TAO, and quality improves automatically. We don't have to force it — the economics handle it.

---

## SLIDE 9 — Roadmap (4:45 – 5:05)

> For the roadmap — we're starting with Bittensor data in Phase 1. Ship the chat, the leaderboard, the API. Start publishing verified weekly insights.
>
> Phase 2 — expand to other chains. Ethereum, Solana, L2s. Same verification method, just more data.
>
> Phase 3 — infrastructure mode. Scheduled reports, saved queries, integrations. QueryAgent becomes the go-to verified analytics layer.

---

## SLIDE 10 — Close (5:05 – 5:15)

> That's QueryAgent. Verifiable, reproducible on-chain analytics — powered by Bittensor.
>
> No more trusting numbers. Prove them. Thanks for watching.

---

## Timing Cheat Sheet

| Slide | Topic | Duration | Running Total |
|---|---|---|---|
| 1 | Title | 15 sec | 0:15 |
| 2 | The Problem | 45 sec | 1:00 |
| 3 | The Solution | 50 sec | 1:50 |
| 4 | Onchain Analytics | 30 sec | 2:20 |
| 5 | Features | 35 sec | 2:55 |
| 6 | How It Works | 70 sec | 4:05 |
| 7 | Market | 20 sec | 4:25 |
| 8 | Why Bittensor | 20 sec | 4:45 |
| 9 | Roadmap | 20 sec | 5:05 |
| 10 | Close | 10 sec | 5:15 |

---

## Recording Tips

- **Slide 6 is your main slide** — take your time, this is what judges want to hear
- If you're running long, cut Slide 4 entirely — judges already know what analytics is
- Talk like you're on a call with someone, not giving a TED talk
- It's fine to say "basically" and "like" — sounds more natural than rehearsed
- Pause for 2 seconds between slides so you have clean edit points

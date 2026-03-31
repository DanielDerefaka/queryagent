# Node Setup — QueryAgent

Evidence of functional miner and validator nodes, with a full incentive loop simulation.

---

## Miner Node Setup

```
Snapshot loaded: bt_snapshot_test_v1
  Table emissions:  24 rows
  Table metagraph:  1115 rows
  Table miners:     1106 rows
  Table stakes:     490 rows
  Table subnets:    10 rows
  Table validators: 9 rows
Task pool: 16 public, 4 hidden
SQL templates loaded: 14 regex patterns
```

### Miner startup command

```bash
python -m neurons.miner \
    --netuid <NETUID> \
    --wallet.name miner_wallet \
    --wallet.hotkey default \
    --subtensor.network test \
    --axon.port 8091
```

### Miner architecture

```
1. Receives QuerySynapse on bt.Axon (port 8091)
2. Loads frozen Parquet snapshot into DuckDB (in-memory)
3. Generates SQL from question (template regex / LLM / hybrid)
4. Executes SQL on DuckDB → computes SHA-256 hash
5. Returns Answer Package: {sql, result_hash, tables_used, explanation}
```

### Three miner strategies available

| Strategy | File | Method | Cost |
|----------|------|--------|------|
| Template | neurons/miner.py | 14 regex patterns | Free |
| LLM | neurons/miner_llm.py | GPT-4o | ~$0.01/query |
| Hybrid | neurons/miner_llm.py | Template first, LLM fallback | Minimal |

---

## Validator Node Setup

```
Ground truth entries: 20
Scoring weights: correctness=0.75, efficiency=0.15, latency=0.10
EMA alpha: 0.1
Validation interval: 120s
Weight rate limit: 200 blocks (~40 min)
```

### Validator startup command

```bash
python -m neurons.validator \
    --netuid <NETUID> \
    --wallet.name validator_wallet \
    --wallet.hotkey default \
    --subtensor.network test
```

### Validator evaluation flow

```
1. Sample task from pool (30% easy, 50% medium, 20% hard, 20% hidden)
2. Build QuerySynapse → broadcast to ALL miners via bt.Dendrite
3. Collect responses within 30s timeout
4. For each response:
   a. Re-execute miner's SQL on validator's own DuckDB
   b. Time the execution
   c. Compute SHA-256 hash of result
   d. Compare to ground truth hash
5. Score: 0.75 (correctness) + 0.15 (efficiency) + 0.10 (latency)
6. Apply EMA smoothing: EMA = 0.1 * new + 0.9 * old
7. Normalize weights → set_weights() on-chain
8. Save scored responses as training data (JSONL)
```

---

## Full Node Simulation — 3 Miners, 5 Rounds

Simulated three miners with different capabilities to demonstrate that the incentive mechanism correctly differentiates performance.

| Miner | Strategy | Description |
|-------|----------|-------------|
| strong_miner | Reference SQL | Always produces correct answer |
| medium_miner | Template regex | Correct when pattern matches |
| weak_miner | Garbage SQL | Always wrong |

### Round-by-Round Results

```
======================================================================
QUERYAGENT — FULL NODE SIMULATION
======================================================================

--- SIMULATED VALIDATION ROUNDS (3 miners, 5 rounds) ---

Round 1: task=QB-001 tier=easy
  Question: What is the total TAO staked across all subnets?
  strong_miner   : score=0.9993 [CORRECT]
  medium_miner   : score=0.9990 [CORRECT]
  weak_miner     : score=0.0000 [WRONG]
  EMA scores: ['0.0999', '0.0999', '0.0000']
  Weights:    ['0.5001', '0.4999', '0.0000']

Round 2: task=QB-002 tier=easy
  Question: How many active subnets are there?
  strong_miner   : score=0.9993 [CORRECT]
  medium_miner   : score=0.9990 [CORRECT]
  weak_miner     : score=0.0000 [WRONG]
  EMA scores: ['0.1899', '0.1898', '0.0000']
  Weights:    ['0.5001', '0.4999', '0.0000']

Round 3: task=QB-003 tier=easy
  Question: How many active miners are on subnet 1?
  strong_miner   : score=0.9993 [CORRECT]
  medium_miner   : score=0.9990 [CORRECT]
  weak_miner     : score=0.0000 [WRONG]
  EMA scores: ['0.2708', '0.2707', '0.0000']
  Weights:    ['0.5001', '0.4999', '0.0000']

Round 4: task=QB-004 tier=easy
  Question: What is the total emission across all subnets?
  strong_miner   : score=0.9993 [CORRECT]
  medium_miner   : score=0.9990 [CORRECT]
  weak_miner     : score=0.0000 [WRONG]
  EMA scores: ['0.3437', '0.3436', '0.0000']
  Weights:    ['0.5001', '0.4999', '0.0000']

Round 5: task=QB-005 tier=easy
  Question: How many validators have non-zero stake?
  strong_miner   : score=0.9993 [CORRECT]
  medium_miner   : score=0.9990 [CORRECT]
  weak_miner     : score=0.0000 [WRONG]
  EMA scores: ['0.4092', '0.4091', '0.0000']
  Weights:    ['0.5001', '0.4999', '0.0000']

--- INCENTIVE MECHANISM VERIFICATION ---
Final EMA:  strong=0.4092  medium=0.4091  weak=0.0000
Final Wts:  strong=0.5001  medium=0.4999  weak=0.0000

RESULT: strong > medium > weak — Incentive mechanism works as intended
======================================================================
```

### Key Observations

1. **Hard gate works**: The weak miner (wrong SQL) gets score=0.0 every round. Zero EMA. Zero weight. No emissions.

2. **Correct miners are rewarded**: Both strong and medium miners get ~0.999 per round since they produce matching hashes.

3. **Speed differentiation**: The strong miner scores slightly higher (0.9993 vs 0.9990) because it responds marginally faster. Over many rounds, this compounds via EMA.

4. **EMA convergence**: After 5 rounds, scores are converging toward their true performance levels. After ~10 rounds (alpha=0.1), EMA fully reflects steady-state behavior.

5. **Weight normalization**: Weights sum to 1.0. The weak miner gets 0% of emissions. The strong and medium miners split emissions proportionally.

6. **Yuma Consensus**: In production, multiple independent validators run this same loop. Since all validators use the same frozen snapshot and deterministic hashing, they arrive at the same scores — producing consensus.

---

## Wire Protocol Test (Axon-Dendrite)

Real network communication test between miner axon and validator dendrite:

```
tests/test_wire.py::test_axon_starts PASSED
tests/test_wire.py::test_dendrite_sends_synapse PASSED
tests/test_wire.py::test_full_wire_loop PASSED
tests/test_wire.py::test_multiple_tasks_over_wire PASSED
```

This confirms that:
- Miner axon starts and listens on a port
- Validator dendrite can send QuerySynapse to the axon
- Full round-trip works: dendrite sends task, axon processes, returns Answer Package
- Multiple consecutive tasks work over the same wire connection

---

## Local Deployment Script

For a full multi-node deployment on a local chain:

```bash
bash scripts/run_local.sh
```

This starts:
- 10 miners (3 strong, 4 medium, 3 weak) on ports 8091-8100
- 3 validators scoring independently
- All connected to local subtensor at ws://127.0.0.1:9944

Monitor with:
```bash
tail -f /tmp/miner_logs/miner_1.log
tail -f /tmp/validator_logs/validator_1.log
```

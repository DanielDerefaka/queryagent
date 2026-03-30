# Validator Mechanics

## Registration & Permits
- **Step 1**: Register hotkey on subnet to receive UID
- **Step 2**: Need minimum stake-weight of 1,000 (`alpha + 0.18 × TAO`)
- **Step 3**: Must rank in top 64 by emissions to get **validator permit**
- **Validator permit**: Allows weight-setting on-chain
- **Recalculated**: Every epoch using stake-weighted system
- **Loss**: When permit lost, associated bonds are deleted

## Dendrite Client
The validator's client for querying miners:

```python
class MyValidator(bt.BaseValidator):
    def forward(self):
        synapse = QuerySynapse(
            task_id="QB-001",
            snapshot_id="bt_snapshot_2026_03_01_v1",
            question="Top 10 subnets by emission growth"
        )

        # Query ALL miners simultaneously
        responses = self.dendrite(
            axons=self.metagraph.axons,    # All miner axons
            synapse=synapse,
            timeout=30,                     # 30 second timeout
        )

        # Score each response
        scores = [self.score(r) for r in responses]

        # Submit weights on-chain
        self.set_weights(scores)
```

- **Protocol**: Transmits Synapse objects to miners' Axon servers
- **Parallel**: Queries multiple axons simultaneously
- **Timeout**: Waits until timeout expires, then processes whatever responses arrived

## Setting Weights

### API
```python
subtensor.set_weights(
    wallet=wallet,
    netuid=netuid,
    uids=uids,              # Array of miner UIDs
    weights=weights,         # Array of float weights
    version_key=0,
    wait_for_inclusion=False,
    wait_for_finalization=False
)
```

### Processing
- **Normalization**: `sum(weights) = 1.0` after processing
- **Clipping**: Max weight normalized to u16 limit (65,535)
- **Rate limiting**: `weights_rate_limit` blocks between commits (default: 100 blocks ≈ 20 min)
- **Minimum UIDs**: Subnet hyperparameter controls minimum weights to set

## Validator Loop Pattern
```python
while True:
    # 1. Sync metagraph
    if should_sync_metagraph():
        metagraph.sync(subtensor=subtensor)

    # 2. Sample task and query miners
    task = sample_task()
    synapse = build_synapse(task)
    responses = dendrite.forward(
        axons=metagraph.axons,
        synapse=synapse,
        timeout=30
    )

    # 3. Score responses
    scores = compute_scores(responses, task.ground_truth)

    # 4. Set weights (rate-limited)
    if should_set_weights():
        weights = normalize(scores)
        subtensor.set_weights(netuid=netuid, weights=weights)

    # 5. Sleep until next block
    time.sleep(12)
```

## Dividends & Rewards
- **Bond-based**: `validator_dividends = bond_value × miner_incentive`
- **Default validator take**: 18% of delegated stake emissions
- **Delegator share**: 82% proportional to stake
- **Key**: Validators earn more by staying near consensus (honest evaluation)

## Stake Delegation
- TAO delegated to validator converts to subnet alpha via AMM
- Minimum: 0.1 TAO to delegate
- Delegators earn proportional emissions

## For QueryAgent Validators
1. Sample task from pool (200 public + 50 hidden)
2. Build QuerySynapse, broadcast to all miners via dendrite
3. Collect responses within 30s timeout
4. Re-execute each miner's SQL on own DuckDB (timed for efficiency scoring)
5. Compare result hash to ground_truth_hash
6. Compute score: `0.75 + 0.15 × efficiency + 0.10 × latency` (or 0.0 if hash mismatch)
7. EMA smooth scores (α = 0.1)
8. Call `set_weights()` on-chain

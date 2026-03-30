# Miner Mechanics

## Registration
- **Command**: `btcli subnet register --netuid <number>`
- **Cost**: Dynamic burn (doubles per registration, halves linearly over 4 days if no registrations)
- **Mainnet cost**: ~3,420 TAO ($1.6M+)
- **Testnet cost**: ~100 TAO
- **UID**: Each subnet has max 256 UIDs — one hotkey = one UID per subnet

## Axon Server
The miner's server that listens for validator requests:

```python
import bittensor as bt

class MyMiner(bt.BaseMiner):
    def forward(self, synapse: CustomSynapse) -> CustomSynapse:
        # Receive task from validator
        # Process and produce response
        synapse.sql = generate_sql(synapse.question)
        synapse.result_hash = execute_and_hash(synapse.sql, synapse.snapshot_id)
        return synapse

    def run(self):
        with self.axon:  # Axon = miner's HTTP-like server ON Bittensor P2P
            while True:
                self.metagraph.sync()
                time.sleep(12)  # one block ≈ 12s
```

- **Protocol**: FastAPI-based HTTP server
- **Discovery**: Publishes IP:PORT on blockchain for validator discovery
- **Middleware**: AxonMiddleware handles verification, blacklisting, prioritization
- **Attach pattern**: `axon.attach(forward_fn, verify_fn=None, blacklist_fn=None, priority_fn=None)`

## Immunity Period
- **Duration**: 4,096 blocks (~13.7 hours) by default (configurable by subnet owner)
- **Protection**: New miners protected from deregistration during this window
- **Calculation**: `is_immune = (current_block - registered_at) < immunity_period`
- **Subnet owner hotkey**: Has permanent immunity

## Deregistration
- **Trigger**: All 256 UIDs occupied + lowest-ranked neuron + outside immunity
- **Metric**: Based on `pruning_score` (emissions-only metric)
- **Frequency**: Once per tempo (~72 minutes)
- **Cost of re-registration**: Must pay burn cost again

## Miner Entry Point Pattern
```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    # Custom args
    parser.add_argument("--netuid", type=int)

    config = bt.config(parser)
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(netuid=config.netuid)

    # Create axon and attach forward function
    axon = bt.axon(wallet=wallet)
    axon.attach(forward_fn=forward)
    axon.serve(netuid=config.netuid, subtensor=subtensor)
    axon.start()

    # Main loop
    while True:
        metagraph.sync(subtensor=subtensor)
        time.sleep(12)
```

## Key Rules
- Miners expose an **axon** (Bittensor P2P), NOT a Docker HTTP endpoint
- The axon handles incoming **Synapse** objects (typed request/response structs)
- Miners must respond within the timeout or get score = 0
- Lowest-ranked miners get deregistered each tempo
- **IMPORTANT**: The master plan mentioned Docker HTTP endpoints — this is WRONG. Must use axon.

## For QueryAgent Miners
- Receive `QuerySynapse` via axon
- Load frozen Parquet snapshot into DuckDB
- Generate SQL from question (template-based or LLM)
- Execute SQL on local DuckDB, compute SHA-256 hash
- Return Answer Package (sql, result_hash, tables_used, explanation)
- Must respond within 30s timeout

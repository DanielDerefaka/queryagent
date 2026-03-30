# Bittensor SDK Key Classes

## bt.Subtensor
Gateway to the blockchain layer.

```python
subtensor = bt.subtensor(network="finney")   # mainnet
subtensor = bt.subtensor(network="test")      # testnet
subtensor = bt.subtensor(chain_endpoint="ws://127.0.0.1:9944")  # local
```

### Key Methods
| Method | Purpose |
|--------|---------|
| `set_weights(wallet, netuid, uids, weights)` | Submit validator weights on-chain |
| `metagraph(netuid)` | Get subnet state |
| `get_balance(address)` | Query TAO balance |
| `burned_register(wallet, netuid)` | Register neuron with burn cost |
| `delegate(wallet, delegate_ss58, amount)` | Stake TAO to validator |
| `undelegate(wallet, delegate_ss58, amount)` | Unstake from validator |

### AsyncSubtensor
```python
async_subtensor = bt.AsyncSubtensor(network="finney")
# All methods return coroutines — must await
# ~120X faster than sync on high-latency networks
```

---

## bt.Wallet
Manages coldkey + hotkey pair.

```python
wallet = bt.wallet(name="default", hotkey="default")
```

### Key Concepts
- **Coldkey**: High-security key for financial operations (transfers, staking, subnet creation)
- **Hotkey**: Operational key for runtime (mining, validating, setting weights)
- **Relationship**: One coldkey → many hotkeys. One hotkey → one coldkey.
- **Seed phrase**: 12+ words for recovery
- **Existential deposit**: 500 RAO minimum — below this, account deactivated

### Wallet Configuration
```python
# Via args
parser.add_argument("--wallet.name", type=str, default="default")
parser.add_argument("--wallet.hotkey", type=str, default="default")

# Via environment variables
# BITTENSOR_WALLET_NAME, BITTENSOR_WALLET_HOTKEY
```

---

## bt.Metagraph
Complete subnet state at a specific block.

```python
metagraph = bt.metagraph(netuid=1, network="finney", lite=True, sync=True)
metagraph.sync(subtensor=subtensor)  # Update from chain
```

### Core Arrays (indexed by UID)
```python
metagraph.uids              # [0, 1, 2, ..., 255]
metagraph.hotkeys           # Hotkey strings
metagraph.stake             # Stake values (in subnet alpha)
metagraph.ranks             # Performance rankings [0.0 - 1.0]
metagraph.trust             # Trust scores
metagraph.validator_trust   # VTrust (consensus alignment)
metagraph.consensus         # Consensus scores
metagraph.incentive         # Incentive values (miner emissions)
metagraph.emission          # Emission values
metagraph.dividends         # Dividend values (validator earnings)
metagraph.active            # Active status booleans
metagraph.axons             # Axon objects (IP, port, etc.)
```

### Matrix Data (full mode only)
```python
metagraph = bt.metagraph(netuid=1, lite=False)  # Full sync
metagraph.W    # Weight matrix (validators × miners)
metagraph.B    # Bond matrix (validators × miners)
```

### Metadata
```python
metagraph.netuid   # Subnet ID
metagraph.n        # Total neurons
metagraph.block    # Block number of snapshot
metagraph.network  # Network name
```

### State Persistence
- Saved to: `~/.bittensor/metagraphs/network-{network}/netuid-{netuid}/block-{block}.pt`
- TTL-based caching with 1-minute default
- Persisted across runs

---

## bt.Axon
Miner's server — FastAPI-based.

```python
axon = bt.axon(wallet=wallet, port=8091)

# Attach handler for a synapse type
axon.attach(
    forward_fn=my_forward,       # Required: process synapse
    verify_fn=my_verify,         # Optional: verify request
    blacklist_fn=my_blacklist,   # Optional: reject bad actors
    priority_fn=my_priority      # Optional: queue priority
)

# Serve on subnet
axon.serve(netuid=netuid, subtensor=subtensor)
axon.start()
```

### Middleware Chain
1. **Verify**: Check request signatures and hotkeys
2. **Blacklist**: Reject known bad actors
3. **Priority**: Queue management for concurrent requests
4. **Forward**: Process the actual synapse

---

## bt.Dendrite
Validator's client for querying miners.

```python
dendrite = bt.dendrite(wallet=wallet)

# Query specific axons
responses = dendrite(
    axons=metagraph.axons,     # List of miner axons
    synapse=my_synapse,        # Synapse object with request data
    timeout=30                 # Timeout in seconds
)
```

- Sends to multiple axons simultaneously
- Collects responses within timeout
- Signs requests with validator's hotkey
- Returns list of response synapses (one per miner)

---

## Configuration Pattern
```python
parser = argparse.ArgumentParser()
parser.add_argument("--netuid", type=int, required=True)
bt.wallet.add_args(parser)
bt.subtensor.add_args(parser)

config = bt.config(parser)
wallet = bt.wallet(config=config)
subtensor = bt.subtensor(config=config)
metagraph = subtensor.metagraph(netuid=config.netuid)
```

## Common Environment Variables
| Variable | Purpose |
|----------|---------|
| `BITTENSOR_WALLET_NAME` | Default wallet name |
| `BITTENSOR_WALLET_HOTKEY` | Default hotkey name |
| `BT_SUBTENSOR_CHAIN_ENDPOINT` | Chain endpoint URL |

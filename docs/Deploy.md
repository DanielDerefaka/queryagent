# Deploying QueryAgent on Bittensor: from code to on-chain demo

**Your subnet code is done — what remains is purely on-chain plumbing.** The path from 124 passing tests to a working incentive loop requires six concrete steps: launch a local subtensor node, provision wallets using the pre-funded Alice account, create and activate a subnet, register miner and validator neurons, stake TAO for a validator permit, then run your `miner.py` and `validator.py` against the local chain. Both teammate errors — `InvalidWorkBlock` and the commit-reveal storage error — stem from version mismatches with the local subtensor node, and both have clean fixes. This report walks through every step, command, and pitfall.

---

## The complete step-by-step deployment sequence

The entire process below assumes you're targeting a **local chain first** (recommended for hackathon iteration speed), then optionally moving to testnet for a polished demo.

### Step 1: Launch a local subtensor node

The fastest path is Docker. Pull the official `devnet-ready` image, which bundles a pre-configured local Bittensor L1 blockchain:

```bash
docker pull ghcr.io/opentensor/subtensor-localnet:devnet-ready
docker run --rm --name local_chain -p 9944:9944 -p 9945:9945 \
  ghcr.io/opentensor/subtensor-localnet:devnet-ready
```

This launches in **fast-blocks mode** — **250ms per block** instead of the mainnet's 12 seconds. A full tempo cycle (360 blocks) completes in ~90 seconds rather than 72 minutes, which dramatically accelerates testing. To use normal 12-second blocks instead, append `False` to the command. Remove the `--rm` flag if you want chain state to persist across container restarts.

Verify the chain is running:
```bash
btcli subnet list --network ws://127.0.0.1:9944
```

You should see netuid 0 (`τ root`), netuid 1 (`α apex`), and a placeholder netuid 2. The Docker endpoint is **port 9944**; if building from source via `./scripts/localnet.sh`, use **port 9945** instead.

Alternatively, to build from source (required if you need to enable special features like the PoW faucet):
```bash
git clone https://github.com/opentensor/subtensor.git && cd subtensor
./subtensor/scripts/init.sh
./scripts/localnet.sh          # fast blocks
```

### Step 2: Provision wallets using Alice as the faucet

Every local Bittensor blockchain ships with a pre-funded **"Alice" development account** holding **1,000,000 TAO**. Alice is a well-known Substrate/Polkadot development keypair (derived from `//Alice` URI) with the SS58 address `5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY`. On a local chain, Alice replaces the faucet entirely — you simply transfer TAO from Alice to your working wallets.

Import Alice and create three role-specific wallets:

```bash
# Import the Alice account
btcli wallet create --uri alice
# When prompted, name the coldkey "alice" and hotkey "default"

# Create subnet owner wallet
btcli wallet create --wallet.name sn-creator --hotkey default

# Create validator wallet
btcli wallet create --wallet.name test-validator --hotkey default

# Create miner wallet
btcli wallet create --wallet.name test-miner --hotkey default
```

Now fund each wallet from Alice. Run `btcli wallets list` to find each wallet's SS58 coldkey address, then transfer:

```bash
btcli wallet transfer --wallet.name alice \
  --destination <SN_CREATOR_SS58_ADDRESS> \
  --network ws://127.0.0.1:9944

btcli wallet transfer --wallet.name alice \
  --destination <VALIDATOR_SS58_ADDRESS> \
  --network ws://127.0.0.1:9944

btcli wallet transfer --wallet.name alice \
  --destination <MINER_SS58_ADDRESS> \
  --network ws://127.0.0.1:9944
```

Transfer at least **1,100 TAO** to the subnet creator (1,000 for subnet creation burn + buffer), and **100+ TAO** each to the miner and validator wallets (registration costs ~0.1 TAO, and the validator needs stake).

**This is why the `InvalidWorkBlock(Module)` error was fixed by using Alice.** The PoW faucet (`btcli wallet faucet`) is **disabled by default** on the standard `devnet-ready` Docker image. It requires a custom subtensor build with the `--features pow-faucet` flag. The error occurs because the PoW solution becomes stale (solved >3 blocks behind current block) in fast-blocks mode where blocks fly by at 250ms. Using Alice's direct TAO transfers sidesteps the faucet entirely.

### Step 3: Create and activate the subnet

```bash
btcli subnet create \
  --subnet-name queryagent \
  --wallet.name sn-creator \
  --wallet.hotkey default \
  --network ws://127.0.0.1:9944 \
  --no-mev-protection
```

The `--no-mev-protection` flag is **required in fast-blocks mode** to prevent transaction timing issues. The burn cost is typically τ 1,000 on a fresh local chain. You'll be prompted to confirm.

After creation, **start emissions** on the subnet:
```bash
btcli subnet start --netuid <YOUR_NETUID> \
  --wallet.name sn-creator \
  --network ws://127.0.0.1:9944
```

On mainnet, new subnets have a ~1-week waiting period before they can be started. On a local chain in fast-blocks mode, this delay is negligible. Verify the subnet exists with `btcli subnet list --network ws://127.0.0.1:9944`.

### Step 4: Register miner and validator neurons

```bash
# Register validator
btcli subnets register --netuid <YOUR_NETUID> \
  --wallet-name test-validator \
  --hotkey default \
  --network ws://127.0.0.1:9944

# Register miner
btcli subnets register --netuid <YOUR_NETUID> \
  --wallet-name test-miner \
  --hotkey default \
  --network ws://127.0.0.1:9944
```

Each registration costs a small recycle fee (~τ 0.1). On success, each neuron receives a unique **UID** on the subnet. Verify with:
```bash
btcli subnet show --netuid <YOUR_NETUID> --network ws://127.0.0.1:9944
```

### Step 5: Stake TAO to the validator for a permit

Validators need a **validator permit** to set weights. This requires staking enough TAO to be among the top 64 neurons by stake weight on the subnet. On a local chain with only two neurons, any meaningful stake suffices:

```bash
btcli stake add --netuid <YOUR_NETUID> \
  --wallet-name test-validator \
  --hotkey default \
  --partial \
  --network ws://127.0.0.1:9944 \
  --no-mev-protection
```

Stake at least 50+ TAO. Verify the permit appeared:
```bash
btcli wallet overview --wallet.name test-validator \
  --network ws://127.0.0.1:9944
```

An asterisk (`*`) in the `VPERMIT` column confirms the permit is active. If it's not there yet, wait one tempo (~90 seconds in fast-blocks mode) — permits are recalculated at each epoch boundary.

### Step 6: Run QueryAgent's miner and validator

Open two terminal sessions and run your actual code:

```bash
# Terminal 1: Miner
python neurons/miner.py \
  --wallet.name test-miner \
  --wallet.hotkey default \
  --netuid <YOUR_NETUID> \
  --axon.port 8901 \
  --subtensor.network local

# Terminal 2: Validator
python neurons/validator.py \
  --wallet.name test-validator \
  --wallet.hotkey default \
  --netuid <YOUR_NETUID> \
  --subtensor.network local
```

The `--subtensor.network local` flag automatically connects to `ws://127.0.0.1:9944`. Add `--logging.info` for real-time logs. After one full tempo cycle, check emissions:

```bash
btcli subnet show --netuid <YOUR_NETUID> --network ws://127.0.0.1:9944
```

You should see non-zero values in the **Incentive** (miner), **Dividends** (validator), and **Emissions** columns. This confirms the full incentive loop is working: your validator is querying miners, scoring responses, calling `set_weights()`, Yuma Consensus is processing the weights, and TAO is flowing.

---

## Why the commit-reveal error happens and how to handle it

The error `Storage function "SubtensorModule.get_commit_reveal_weights_enabled" not found` when running `btcli weights commit` on netuid 2 is a **version mismatch between the SDK/CLI and the local subtensor runtime**.

Commit-reveal weights (CRv4) uses **Drand time-lock encryption** to conceal validator weights for a configurable number of tempos before automatic reveal. The mechanism prevents weight-copying attacks where lazy validators free-ride by copying others' publicly visible weights. When enabled, validators still call the same `set_weights()` function — the chain automatically encrypts, conceals, and reveals weights transparently.

Here's what's going wrong: the `commit_reveal_weights_enabled` storage function was added in a specific subtensor runtime version that includes the **Drand pallet**. If your local subtensor Docker image or source build predates this addition, the storage query fails because the on-chain module literally doesn't have that field. Three specific causes and fixes:

- **Outdated Docker image**: Ensure you're using `ghcr.io/opentensor/subtensor-localnet:devnet-ready` (not an older tag). This image should include the latest runtime.
- **SDK-chain mismatch**: Bittensor SDK v10 removed explicit CRv3 client-side logic because the chain now handles CR internally. If your btcli or SDK version expects storage fields the chain doesn't expose, you get this error. Match SDK and subtensor versions.
- **CR not needed locally**: The simplest fix for a hackathon demo is to **not use commit-reveal on the local chain at all**. The `commit_reveal_weights_enabled` hyperparameter defaults to `False`. Your validator's `set_weights()` call works normally without CR. Only use `btcli weights commit` if you've explicitly enabled CR on your subnet — and for a demo, you don't need to.

**Bottom line: skip `btcli weights commit` entirely.** Your `validator.py` calls `set_weights()` through the SDK, which handles everything. On a local chain with CR disabled (the default), weights are written directly to chain storage. This is the correct path for a hackathon demo.

---

## How Yuma Consensus and the incentive loop actually work

Understanding the flow from your `validator.py`'s `set_weights()` call to TAO emissions is critical for debugging and for your demo pitch.

**Every tempo cycle (360 blocks), the chain runs Yuma Consensus.** Your validator evaluates miners using QueryAgent's scoring engine, produces a weight vector mapping miner UIDs to scores, and submits it via `subtensor.set_weights()`. The SDK normalizes these floats to uint16 values and submits an on-chain extrinsic. The chain validates that the hotkey is registered, has a validator permit, respects rate limits (`weights_rate_limit` blocks between submissions), and satisfies minimum weight vector length (`min_allowed_weights`).

At the end of each tempo, **Yuma Consensus processes the weight matrix**. It computes a stake-weighted median for each miner's scores across all validators. Weights exceeding this consensus benchmark are clipped downward — this prevents any single validator from inflating a miner's score. Clipped, stake-weighted ranks determine each miner's **incentive share** of emissions. Validators earn **dividends** based on their bond positions, which accumulate through an exponential moving average rewarding consistent consensus alignment. The validator's **vtrust** score reflects how well their weights match consensus — higher vtrust means higher dividends.

Key implications for QueryAgent: since you likely have only one validator and one miner on a local chain, your validator's weights *are* the consensus. The miner will receive all incentive emissions and the validator all dividends. This is perfectly fine for a demo — it proves the loop works. With multiple miners, you'd see differentiated scores and emissions proportional to QueryAgent's scoring engine output.

---

## Local chain versus testnet: which to use for the hackathon

| Factor | Local chain | Testnet |
|---|---|---|
| **Setup time** | ~5 minutes (Docker) | Hours (get testnet TAO from Discord, wait for confirmations) |
| **Iteration speed** | 250ms blocks, 90-second tempos | 12-second blocks, 72-minute tempos |
| **Token funding** | Unlimited via Alice (1M TAO) | Must request testnet TAO; limited supply |
| **Commit-reveal support** | Requires specific subtensor build with Drand pallet | Fully supported (Drand works on testnet) |
| **Network realism** | Isolated, no real network conditions | Real peer-to-peer network, latency, competition |
| **State persistence** | Ephemeral by default | Persistent |
| **Demo reliability** | 100% under your control | Depends on testnet availability and network conditions |

**For a hackathon demo, use the local chain.** It's faster, more reliable, and entirely under your control. Testnet adds real-world fidelity but also introduces variables that can derail a live demo (network latency, testnet outages, waiting 72 minutes per tempo cycle). If you want to show testnet deployment as a bonus, do it before the demo and screenshot/record the results, but run the live demo on local.

The testnet endpoint is `wss://test.finney.opentensor.ai:443`, accessible via `--network test` in btcli commands or `--subtensor.network test` in your neuron scripts.

---

## Common pitfalls teams hit during this phase

**The `--no-mev-protection` flag is required for most write operations in fast-blocks mode.** Subnet creation, staking, and registration can silently fail or timeout without it. Add it to every `btcli subnet create` and `btcli stake add` command on a local fast-blocks chain.

**Validators won't earn dividends until miners are actually running and responding.** If your validator calls `set_weights()` with an empty or all-zero weight vector (because no miners responded), you'll hit the `WeightVecLengthIsLow` error. Always start the miner *before* the validator, or ensure your validator handles the case where no miners are active yet.

**The `NeuronNoValidatorPermit` error means insufficient stake.** This isn't just about having TAO in the coldkey — you must explicitly stake to the validator's hotkey on the specific subnet using `btcli stake add --netuid`. On a local chain, stake ~50+ TAO, then wait one tempo for the permit to activate.

**Registration can expire in fast-blocks mode.** Blocks fly by at 250ms, so PoW-based registration solutions become stale quickly. Use `--period 20` flag to extend the registration window, or just use burn-based registration (the default) which doesn't have this issue.

**Don't use `btcli wallet faucet` on the standard Docker image.** It's disabled. Use Alice transfers instead. If you absolutely need the faucet, build subtensor from source with `cargo build -p node-subtensor --features pow-faucet`.

**Your `validator.py` must call `set_weights()` within the `activity_cutoff` window each epoch.** If the validator doesn't submit weights frequently enough, Yuma Consensus treats it as offline, and it receives zero dividends. Ensure your validator loop runs faster than the cutoff period.

**Port confusion between Docker and source builds**: Docker exposes the local chain on **port 9944**; building from source via `localnet.sh` uses **port 9945**. Using the wrong port causes silent connection failures.

---

## What a minimum viable on-chain demo looks like

For a hackathon submission, you need to demonstrate that QueryAgent's incentive loop works end-to-end on-chain. Here is the minimum set of artifacts and evidence:

The demo should show **five things**: (1) a running local subtensor node with your subnet created and active, (2) a registered miner responding to queries via its Axon, (3) a registered validator scoring miner responses and calling `set_weights()`, (4) non-zero emissions flowing in `btcli subnet show` output after at least one tempo, and (5) your custom QueryAgent protocol (QuerySynapse, scoring engine, DuckDB snapshots) running as the actual incentive mechanism rather than the default template dummy protocol.

A compelling demo video would walk through: starting the local chain → creating the subnet → registering neurons → launching the miner and validator → showing real-time logs of the validator querying miners with QuerySynapse, scoring responses, and setting weights → then showing `btcli subnet show` with active emissions. In fast-blocks mode, the entire cycle from chain launch to emissions takes under **10 minutes**.

For extra credit, show differentiated scoring by running both `neurons/miner.py` (template miner) and `neurons/miner_llm.py` (GPT-4o hybrid) simultaneously on different UIDs, demonstrating that the LLM miner earns higher incentive scores through your scoring engine — this proves QueryAgent's incentive mechanism actually differentiates quality.

---

## Concise command reference for the full lifecycle

```bash
# 1. Launch local chain
docker pull ghcr.io/opentensor/subtensor-localnet:devnet-ready
docker run --rm -p 9944:9944 -p 9945:9945 \
  ghcr.io/opentensor/subtensor-localnet:devnet-ready

# 2. Import Alice, create wallets
btcli wallet create --uri alice
btcli wallet create --wallet.name sn-creator --hotkey default
btcli wallet create --wallet.name test-validator --hotkey default
btcli wallet create --wallet.name test-miner --hotkey default

# 3. Fund wallets from Alice
btcli wallet transfer --wallet.name alice --destination <ADDR> --network ws://127.0.0.1:9944

# 4. Create and start subnet
btcli subnet create --subnet-name queryagent --wallet.name sn-creator \
  --wallet.hotkey default --network ws://127.0.0.1:9944 --no-mev-protection
btcli subnet start --netuid <NETUID> --wallet.name sn-creator \
  --network ws://127.0.0.1:9944

# 5. Register neurons
btcli subnets register --netuid <NETUID> --wallet-name test-validator \
  --hotkey default --network ws://127.0.0.1:9944
btcli subnets register --netuid <NETUID> --wallet-name test-miner \
  --hotkey default --network ws://127.0.0.1:9944

# 6. Stake for validator permit
btcli stake add --netuid <NETUID> --wallet-name test-validator \
  --hotkey default --partial --network ws://127.0.0.1:9944 --no-mev-protection

# 7. Run neurons (separate terminals)
python neurons/miner.py --wallet.name test-miner --wallet.hotkey default \
  --netuid <NETUID> --axon.port 8901 --subtensor.network local
python neurons/validator.py --wallet.name test-validator --wallet.hotkey default \
  --netuid <NETUID> --subtensor.network local

# 8. Verify emissions
btcli subnet show --netuid <NETUID> --network ws://127.0.0.1:9944
```

## Conclusion

QueryAgent's remaining work is entirely operational, not architectural. The code is built; you need roughly 30 minutes of terminal commands to go from zero to emissions flowing. **Use the local chain with fast-blocks mode for development and demo** — it gives you 90-second tempo cycles and infinite TAO from Alice. Skip commit-reveal entirely on local (it's disabled by default and the storage error confirms your local node doesn't support it). Your `validator.py`'s existing `set_weights()` call works without modification — Yuma Consensus handles the rest. For the demo video, the single most impressive thing to show is differentiated emissions between your template miner and LLM miner, proving that QueryAgent's incentive mechanism produces meaningful quality signals on-chain.
# Bittensor Core Architecture

## Blockchain Layer
- **Chain Type**: Layer 1 blockchain built on Polkadot Substrate (migrated 2023)
- **Consensus**: Proof of Authority (PoA) under Opentensor Foundation trusted nodes
- **Block Finality**: Aura for block authoring, GRANDPA for finality
- **Networks**: Mainnet = "finney", separate testnet available

## Key Numbers
| Parameter | Value |
|-----------|-------|
| Block time | 12 seconds |
| Tempo | 360 blocks (~72 minutes) |
| Block emission | 0.5 TAO/block (post-halving Dec 2024) |
| Max supply | 21 million TAO (Bitcoin-like cap) |
| Max UIDs per subnet | 256 (typically 64 validators + 192 miners) |
| Active subnets | 120+ (as of late 2025) |

## Tempo Cycle
Every 360 blocks (~72 minutes), the chain runs **Yuma Consensus**:
1. Validators submit weight vectors (how good each miner is)
2. Yuma aggregates → allocates TAO emissions
3. Distribution: **41% miners, 41% validators/stakers, 18% subnet owner**

## Token Economics
- **Halving**: Every ~10.5M tokens mined (approximately 4-year cycles)
- **First halving**: December 14, 2024 — reduced from 1 TAO/block to 0.5 TAO/block
- **Daily emission**: ~3,600 TAO/day (post-halving)

## Network Hierarchy
```
Bittensor Network
├── Root Network (Subnet 0) — governance, manages network-wide emissions
│   └── 64 max validators, no miners
│   └── Root validators assess all subnets
└── Subnets (netuid 1-65535)
    ├── Validators (run dendrite, set weights on-chain)
    └── Miners (run axon server, process forward calls)
```

## Transaction Fees
- Weight-based fee for extrinsics
- TAO preferred; falls back to Alpha if TAO insufficient
- Staking fee: 0.05% of transacted liquidity
- State queries (reads) are always free

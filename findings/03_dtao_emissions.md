# Dynamic TAO (dTAO) — Post November 2025

## What Changed
Replaced previous price-based emission model with **net TAO staking inflows**. Each subnet now has its own token economy.

## Alpha Tokens
- **Per Subnet**: Each subnet has its own alpha (α) token
- **Emission Rate**: 2 alpha tokens per block per subnet
- **Max Supply**: 21 million per subnet (same cap as TAO)
- **AMM Model**: Constant-product formula (Uniswap V2-style)
  - `K = TAO_reserve × α_reserve`
  - Token price increases with more TAO deposits

## Flow-Based Emissions
- **Formula**: Emissions based on Exponential Moving Average of net staking flows
- **Half-life**: ~86.8 days
- **Zero Emissions**: Subnets with negative net flows (more unstaking than staking) get **zero emissions**
- **Scale-invariant**: Doesn't favor large liquidity pools — rewards genuine demand

### What This Means
```
Net Flow = TAO staked into subnet - TAO unstaked from subnet

Positive net flow → Subnet earns emissions
Zero/negative net flow → Subnet earns nothing
```

## Staking Mechanics
- Users swap TAO for alpha tokens via AMM bonding curve
- Minimum: 0.1 TAO to delegate
- Slippage: Larger amounts have more slippage
- AMM fees: 0.05% on staking/unstaking

## Validator Stake Weight
```
Validator Stake Weight = α (alpha stake) + 0.18 × τ (TAO stake)
```
- TAO weight of 0.18 is a global parameter (adjustable)
- Prevents rapid alpha accumulation exploits in early subnet phases

## Growth Impact
- 32 subnets (early 2025) → 128+ subnets (late 2025)
- Highest quality subnets funded first by market
- Capital allocation determined by actual demand

## Why This Matters for QueryAgent
- **We MUST attract real stakers** — without positive TAO inflows, we get zero emissions
- Can't survive on just miners and validators — need genuine users who stake
- Our go-to-market strategy directly impacts our economic survival
- Subnet utility = staking demand = emissions = sustainability

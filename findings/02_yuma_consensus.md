# Yuma Consensus

The on-chain algorithm that converts validator weight submissions into miner and validator emissions. Runs once per tempo (every 360 blocks, ~72 minutes).

## How It Works

### 1. Weight Submission
- Each validator submits a weight vector: `[w1, w2, ..., w256]` — one weight per miner UID
- Weights normalized so `sum(weights) = 1.0`
- Rate limited by `weights_rate_limit` hyperparameter (default: 100 blocks between submissions)

### 2. Stake-Weighted Median & Clipping
- Computes stake-weighted median based on highest-stake validators
- Weights exceeding the benchmark are **clipped** — neither miner nor validator receives emissions for the excess
- Example: If the bottom 50% of validators (by stake) set weight ≤ x for a miner, the top 50% get clipped to x
- **Effect**: Prevents any single validator from over-rewarding a miner

### 3. Validator Bonds (EMA)
- Validators build Exponential Moving Average bonds with miners
- Formula: `B_ij(t) = 0.9 × ΔB_ij(t) + 0.1 × B_ij(t-1)` (alpha = 0.9)
- Validators staying near consensus **strengthen bonds** → higher emissions
- Validators deviating from consensus → **penalties** to bonds and dividends

### 4. Validator Trust (VTrust)
- Consensus-alignment score measuring how closely each validator's weights match the stake-weighted median
- **Higher VTrust** → higher dividends per TAO staked → higher APY
- Calculated as stake-weighted clipped sum of validator weights
- Key metric for validator profitability

### 5. Emission Distribution
```
Miner emissions    = INCENTIVE × (EMISSION × 0.41)
Validator dividends = DIVIDENDS × (EMISSION × 0.41)
Subnet owner       = EMISSION × 0.18
```

## Commit-Reveal Scheme
Prevents weight copying (validators copying other validators' weights):
- **Encryption**: Drand time-lock encryption hides weights for configurable tempos
- **Auto-reveal**: Drand automatically reveals after period expires
- **Effect**: Copiers access stale weights → inaccurate → deviate from consensus → lose vtrust
- **Hyperparameters**:
  - `commit_reveal_weights_enabled`: Boolean toggle
  - `commit_reveal_period`: Number of tempos before reveal

## Why This Matters for QueryAgent
- Our validators MUST set weights that align with consensus — honest evaluation is the only profitable strategy
- Hash-based scoring (correct/incorrect) means all honest validators will agree — perfect for Yuma Consensus
- Weight copying is irrelevant because our evaluation is deterministic

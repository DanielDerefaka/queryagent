# QueryAgent — Research Findings & Knowledge Base

Comprehensive research compiled before starting the testnet build phase. Read these before writing any code.

## Index

| # | File | What's Inside |
|---|------|---------------|
| 01 | [bittensor_core.md](01_bittensor_core.md) | Blockchain layer, block time, tempo, token economics, network hierarchy |
| 02 | [yuma_consensus.md](02_yuma_consensus.md) | Consensus algorithm, weight clipping, bonds, VTrust, commit-reveal |
| 03 | [dtao_emissions.md](03_dtao_emissions.md) | Dynamic TAO, alpha tokens, flow-based emissions, staking mechanics |
| 04 | [miners.md](04_miners.md) | Axon server, registration, deregistration, immunity, forward pattern, code examples |
| 05 | [validators.md](05_validators.md) | Dendrite client, set_weights API, permits, scoring loop, code examples |
| 06 | [synapse_protocol.md](06_synapse_protocol.md) | bt.Synapse class, custom fields, serialization, request/response pattern |
| 07 | [sdk_classes.md](07_sdk_classes.md) | bt.subtensor, bt.wallet, bt.metagraph, bt.axon, bt.dendrite — full API reference |
| 08 | [successful_subnets.md](08_successful_subnets.md) | Top subnets (Chutes, IOTA, Ridges, Hermes), why they work, competitor analysis |
| 09 | [subnet_patterns.md](09_subnet_patterns.md) | What makes a good subnet, Const's advice, failure modes, self-assessment checklist |
| 10 | [repo_structure.md](10_repo_structure.md) | GitHub patterns, file structure, code templates, Docker, testing, dependencies |
| 11 | [queryagent_checklist.md](11_queryagent_checklist.md) | Testnet readiness checklist, build order, hardware requirements, corrections |

## Key Takeaways

1. **Miners use bt.axon, NOT Docker HTTP** — our master plan had this wrong, now corrected
2. **dTAO means we need real users staking** — without positive TAO inflows, zero emissions
3. **Hash-based scoring is perfect for Yuma Consensus** — all honest validators will agree
4. **Frozen snapshots are our unique edge** — no other subnet does deterministic, reproducible analytics
5. **Build order**: protocol → snapshot → tasks → scoring → miner → validator → testnet
6. **CPU-friendly** — DuckDB runs on CPU, making our subnet accessible to more miners

## Sources
- Bittensor docs: docs.learnbittensor.org, docs.bittensor.com
- GitHub: opentensor/bittensor-subnet-template, macrocosm-os/prompting, macrocosm-os/pretraining
- Competitor repos: SN-Hermes/hermes-subnet, blockchain-insights/blockchain-data-subnet
- Const's posts: @const_reborn on X
- Research papers: arxiv.org/html/2507.02951v1

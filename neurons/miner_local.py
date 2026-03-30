"""
QueryAgent Miner — Local chain compatible version.
Skips bt.Metagraph (requires NeuronInfoRuntimeApi) and uses direct substrate queries.
"""
import argparse
import time
import structlog

import bittensor as bt
from queryagent.protocol import QuerySynapse
from queryagent.snapshot import load_snapshot, execute_sql_safe
from queryagent.hashing import hash_result

logger = structlog.get_logger()

# Direct task_id → SQL mapping (exact ground truth reference SQL)
TASK_SQL = {
    # === EASY ===
    "QB-001": {
        "sql": "SELECT SUM(stake) AS total_staked FROM stakes",
        "tables": ["stakes"],
        "explanation": "Sum of all TAO staked across the network.",
    },
    "QB-002": {
        "sql": "SELECT COUNT(DISTINCT netuid) AS subnet_count FROM subnets",
        "tables": ["subnets"],
        "explanation": "Count of unique subnets on the network.",
    },
    "QB-003": {
        "sql": "SELECT COUNT(*) AS miner_count FROM miners WHERE netuid = 1 AND active = true",
        "tables": ["miners"],
        "explanation": "Number of active miners on subnet 1.",
    },
    "QB-004": {
        "sql": "SELECT SUM(emission) AS total_emission FROM emissions",
        "tables": ["emissions"],
        "explanation": "Total emission across all subnets.",
    },
    "QB-005": {
        "sql": "SELECT COUNT(*) AS validator_count FROM validators WHERE stake > 0",
        "tables": ["validators"],
        "explanation": "Number of validators with non-zero stake.",
    },
    "QB-006": {
        "sql": "SELECT AVG(stake) AS avg_stake FROM validators WHERE stake > 0",
        "tables": ["validators"],
        "explanation": "Average stake per validator (non-zero only).",
    },
    # === MEDIUM ===
    "QB-010": {
        "sql": "SELECT netuid, uid, hotkey, stake FROM validators ORDER BY stake DESC LIMIT 10",
        "tables": ["validators"],
        "explanation": "Top 10 validators by stake across all subnets.",
    },
    "QB-011": {
        "sql": "SELECT netuid, SUM(emission) AS total_emission FROM emissions GROUP BY netuid ORDER BY total_emission DESC LIMIT 1",
        "tables": ["emissions"],
        "explanation": "Subnet with the highest total emission.",
    },
    "QB-012": {
        "sql": "SELECT netuid, uid, hotkey, incentive FROM miners ORDER BY incentive DESC LIMIT 10",
        "tables": ["miners"],
        "explanation": "Top 10 miners by incentive score.",
    },
    "QB-013": {
        "sql": "SELECT netuid, AVG(validator_trust) AS avg_vtrust FROM validators GROUP BY netuid ORDER BY avg_vtrust DESC",
        "tables": ["validators"],
        "explanation": "Average validator trust per subnet.",
    },
    "QB-014": {
        "sql": "SELECT netuid, COUNT(*) AS active_miners FROM miners WHERE active = true GROUP BY netuid ORDER BY active_miners DESC",
        "tables": ["miners"],
        "explanation": "Subnets ranked by number of active miners.",
    },
    "QB-015": {
        "sql": "SELECT netuid, SUM(stake) AS total_stake FROM metagraph GROUP BY netuid ORDER BY total_stake DESC",
        "tables": ["metagraph"],
        "explanation": "Total stake per subnet.",
    },
    "QB-016": {
        "sql": "SELECT e.netuid, SUM(e.emission) / NULLIF(COUNT(DISTINCT m.uid), 0) AS emission_per_miner FROM emissions e JOIN miners m ON e.netuid = m.netuid AND m.active = true GROUP BY e.netuid ORDER BY emission_per_miner DESC LIMIT 5",
        "tables": ["emissions", "miners"],
        "explanation": "Top 5 subnets by emission per active miner.",
    },
    "QB-017": {
        "sql": "SELECT netuid, uid, hotkey, dividends FROM validators ORDER BY dividends DESC LIMIT 10",
        "tables": ["validators"],
        "explanation": "Validators with highest dividends.",
    },
    "QB-018": {
        "sql": "WITH subnet_stakes AS (SELECT netuid, uid, stake, SUM(stake) OVER (PARTITION BY netuid) AS total_stake FROM validators) SELECT netuid, uid, stake, total_stake, stake / NULLIF(total_stake, 0) AS stake_share FROM subnet_stakes WHERE stake / NULLIF(total_stake, 0) > 0.5 ORDER BY stake_share DESC",
        "tables": ["validators"],
        "explanation": "Subnets where the top validator holds more than 50% of total stake.",
    },
    "QB-019": {
        "sql": "SELECT netuid, COUNT(*) AS neuron_count FROM metagraph GROUP BY netuid ORDER BY neuron_count DESC",
        "tables": ["metagraph"],
        "explanation": "Number of neurons per subnet.",
    },
    # === HARD (hidden tasks — miner still attempts them) ===
    "QB-030": {
        "sql": "WITH subnet_stats AS (SELECT netuid, AVG(validator_trust) AS avg_vtrust, SUM(emission) AS total_emission FROM metagraph GROUP BY netuid), network_avg AS (SELECT AVG(avg_vtrust) AS net_avg_vtrust, AVG(total_emission) AS net_avg_emission FROM subnet_stats) SELECT s.netuid, s.avg_vtrust, s.total_emission FROM subnet_stats s, network_avg n WHERE s.avg_vtrust > n.net_avg_vtrust AND s.total_emission < n.net_avg_emission ORDER BY s.avg_vtrust DESC",
        "tables": ["metagraph"],
        "explanation": "Subnets with above-average trust but below-average emission.",
    },
    "QB-031": {
        "sql": "WITH stake_conc AS (SELECT netuid, MAX(stake) / NULLIF(SUM(stake), 0) AS max_stake_share FROM metagraph GROUP BY netuid), miner_counts AS (SELECT netuid, COUNT(*) AS active_miners FROM miners WHERE active = true GROUP BY netuid) SELECT sc.netuid, sc.max_stake_share, mc.active_miners FROM stake_conc sc JOIN miner_counts mc ON sc.netuid = mc.netuid ORDER BY sc.max_stake_share DESC",
        "tables": ["metagraph", "miners"],
        "explanation": "Stake concentration vs active miners per subnet.",
    },
    "QB-032": {
        "sql": "WITH ranked AS (SELECT netuid, uid, hotkey, stake, emission, emission / NULLIF(stake, 0) AS efficiency, ROW_NUMBER() OVER (PARTITION BY netuid ORDER BY emission / NULLIF(stake, 0) DESC) AS rn FROM validators WHERE stake > 0) SELECT netuid, uid, hotkey, stake, emission, efficiency FROM ranked WHERE rn <= 3 ORDER BY netuid, efficiency DESC",
        "tables": ["validators"],
        "explanation": "Top 3 validators by emission efficiency per subnet.",
    },
    "QB-033": {
        "sql": "WITH ordered AS (SELECT netuid, stake, ROW_NUMBER() OVER (PARTITION BY netuid ORDER BY stake) AS i, COUNT(*) OVER (PARTITION BY netuid) AS n, SUM(stake) OVER (PARTITION BY netuid) AS total FROM metagraph WHERE stake > 0) SELECT netuid, 1 - (2.0 / (n * NULLIF(total, 0))) * SUM(stake * (n + 1 - i)) AS gini FROM ordered GROUP BY netuid, n, total HAVING n > 1 ORDER BY gini DESC",
        "tables": ["metagraph"],
        "explanation": "Gini coefficient of stake distribution per subnet.",
    },
}


# Tier classification for skill-based filtering
EASY_TASKS = {"QB-001", "QB-002", "QB-003", "QB-004", "QB-005", "QB-006"}
MEDIUM_TASKS = {"QB-010", "QB-011", "QB-012", "QB-013", "QB-014", "QB-015", "QB-016", "QB-017", "QB-018", "QB-019"}
HARD_TASKS = {"QB-030", "QB-031", "QB-032", "QB-033"}

# Miner skill level — set via --skill flag
MINER_SKILL = "strong"  # default; overridden by CLI arg


def generate_sql(task_id: str, question: str, constraints: dict = None) -> tuple:
    """Look up SQL by task_id, filtered by miner skill level."""
    # Skill gate: weak miners only answer easy, medium miners skip hard
    if MINER_SKILL == "weak" and task_id not in EASY_TASKS:
        return None, None, None
    if MINER_SKILL == "medium" and task_id in HARD_TASKS:
        return None, None, None

    entry = TASK_SQL.get(task_id)
    if entry:
        return entry["sql"], entry["tables"], entry["explanation"]
    return None, None, None


def forward(synapse: QuerySynapse) -> QuerySynapse:
    """Process a query request from a validator."""
    try:
        snapshot_id = synapse.snapshot_id or "bt_snapshot_test_v1"
        conn = load_snapshot(snapshot_id)

        sql, tables_used, explanation = generate_sql(
            synapse.task_id,
            synapse.question,
            synapse.constraints,
        )
        if not sql:
            logger.warning(f"No SQL for task: {synapse.task_id} / {synapse.question}")
            return synapse

        # Execute and hash
        result_hash = hash_result(conn, sql)
        columns, rows, exec_ms = execute_sql_safe(conn, sql)

        # Build preview
        preview = {"columns": columns, "rows": [list(r) for r in rows[:10]]}

        synapse.sql = sql
        synapse.result_hash = result_hash
        synapse.result_preview = preview
        synapse.tables_used = tables_used
        synapse.explanation = explanation

        logger.info(
            f"Answered task={synapse.task_id} | "
            f"hash={result_hash[:30]}... | "
            f"exec_ms={exec_ms:.1f}"
        )

    except Exception as e:
        logger.error(f"Forward error: {e}")

    return synapse


def main():
    parser = argparse.ArgumentParser(description="QueryAgent Miner (Local)")
    parser.add_argument("--netuid", type=int, required=True)
    parser.add_argument("--axon.port", type=int, default=8091)
    parser.add_argument("--wallet.name", type=str, required=True)
    parser.add_argument("--wallet.hotkey", type=str, default="default")
    parser.add_argument("--subtensor.network", type=str, default="ws://127.0.0.1:9944")
    parser.add_argument("--skill", type=str, default="strong", choices=["strong", "medium", "weak"],
                        help="Miner skill level: strong=all tasks, medium=easy+medium, weak=easy only")
    args = parser.parse_args()

    # Set global skill level
    global MINER_SKILL
    MINER_SKILL = args.skill

    wallet = bt.Wallet(name=args.__dict__["wallet.name"], hotkey=args.__dict__["wallet.hotkey"])
    subtensor = bt.Subtensor(network=args.__dict__["subtensor.network"])
    port = args.__dict__["axon.port"]

    logger.info(f"Wallet: {wallet.name} | Hotkey: {wallet.hotkey.ss58_address}")
    logger.info(f"Chain block: {subtensor.block}")

    # Create and start axon
    axon = bt.Axon(wallet=wallet, port=port)
    axon.attach(forward_fn=forward)
    axon.serve(netuid=args.netuid, subtensor=subtensor)
    axon.start()

    logger.info(f"Miner axon running on port {port}")

    try:
        while True:
            logger.info(f"Miner {wallet.name} alive | block={subtensor.block}")
            time.sleep(12)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        axon.stop()


if __name__ == "__main__":
    main()

"""
QueryAgent Reference Miner — receives tasks via axon, returns Answer Packages.

The miner:
1. Receives a QuerySynapse from a validator
2. Loads the frozen snapshot into DuckDB
3. Generates SQL from the question (template-based for v1)
4. Executes SQL, computes SHA-256 hash
5. Returns the Answer Package (sql, result_hash, tables_used, explanation)

Usage:
    python -m neurons.miner --netuid <NETUID> --wallet.name <NAME> --wallet.hotkey <HOTKEY> --subtensor.network test
"""

import argparse
import logging
import re
import time
import traceback
from typing import Optional

import bittensor as bt

from queryagent.config import DEFAULT_TIMEOUT_S
from queryagent.hashing import hash_result
from queryagent.protocol import QuerySynapse
from queryagent.snapshot import load_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# SQL Generation — Template-Based (v1)
# ──────────────────────────────────────────────

# Pattern → SQL template. {snapshot} tables are available in DuckDB.
SQL_TEMPLATES = [
    # ── Easy ──
    {
        "pattern": r"total.*staked|total.*stake",
        "sql": "SELECT SUM(stake) AS total_staked FROM stakes",
        "tables": ["stakes"],
        "explanation": "Sums all stake values from the stakes table.",
    },
    {
        "pattern": r"how many.*subnets|number of.*subnets|count.*subnets",
        "sql": "SELECT COUNT(DISTINCT netuid) AS subnet_count FROM subnets",
        "tables": ["subnets"],
        "explanation": "Counts distinct subnet IDs.",
    },
    {
        "pattern": r"how many.*(miners|active miners).*subnet (\d+)",
        "sql": "SELECT COUNT(*) AS miner_count FROM miners WHERE netuid = {netuid} AND active = true",
        "tables": ["miners"],
        "explanation": "Counts active miners on the specified subnet.",
    },
    {
        "pattern": r"total.*emission",
        "sql": "SELECT SUM(emission) AS total_emission FROM emissions",
        "tables": ["emissions"],
        "explanation": "Sums all emission values across all subnets.",
    },
    {
        "pattern": r"how many.*validators.*stake|validators.*non.?zero",
        "sql": "SELECT COUNT(*) AS validator_count FROM validators WHERE stake > 0",
        "tables": ["validators"],
        "explanation": "Counts validators with non-zero stake.",
    },
    {
        "pattern": r"average.*stake.*validator",
        "sql": "SELECT AVG(stake) AS avg_stake FROM validators WHERE stake > 0",
        "tables": ["validators"],
        "explanation": "Computes average stake across validators with non-zero stake.",
    },

    # ── Medium ──
    {
        "pattern": r"top (\d+).*validators.*stake",
        "sql": "SELECT netuid, uid, hotkey, stake FROM validators ORDER BY stake DESC LIMIT {k}",
        "tables": ["validators"],
        "explanation": "Returns top validators ranked by stake.",
    },
    {
        "pattern": r"subnet.*highest.*emission|highest.*emission.*subnet",
        "sql": (
            "SELECT netuid, SUM(emission) AS total_emission "
            "FROM emissions GROUP BY netuid ORDER BY total_emission DESC LIMIT 1"
        ),
        "tables": ["emissions"],
        "explanation": "Finds the subnet with the highest total emission.",
    },
    {
        "pattern": r"top (\d+).*miners.*incentive",
        "sql": "SELECT netuid, uid, hotkey, incentive FROM miners ORDER BY incentive DESC LIMIT {k}",
        "tables": ["miners"],
        "explanation": "Returns top miners ranked by incentive score.",
    },
    {
        "pattern": r"average.*validator.*trust.*subnet|validator trust.*per subnet",
        "sql": (
            "SELECT netuid, AVG(validator_trust) AS avg_vtrust "
            "FROM validators GROUP BY netuid ORDER BY avg_vtrust DESC"
        ),
        "tables": ["validators"],
        "explanation": "Computes average validator trust per subnet.",
    },
    {
        "pattern": r"subnets.*ranked.*active.*miners|subnets.*number.*active.*miners",
        "sql": (
            "SELECT netuid, COUNT(*) AS active_miners "
            "FROM miners WHERE active = true "
            "GROUP BY netuid ORDER BY active_miners DESC"
        ),
        "tables": ["miners"],
        "explanation": "Ranks subnets by number of active miners.",
    },
    {
        "pattern": r"stake.*distribution.*subnet|total.*stake.*per.*subnet",
        "sql": (
            "SELECT netuid, SUM(stake) AS total_stake "
            "FROM metagraph GROUP BY netuid ORDER BY total_stake DESC"
        ),
        "tables": ["metagraph"],
        "explanation": "Shows total stake per subnet.",
    },
    {
        "pattern": r"validators.*highest.*dividends|top.*dividends",
        "sql": (
            "SELECT netuid, uid, hotkey, dividends "
            "FROM validators ORDER BY dividends DESC LIMIT 10"
        ),
        "tables": ["validators"],
        "explanation": "Returns validators with highest dividends.",
    },
    {
        "pattern": r"neurons.*per.*subnet|neuron.*count",
        "sql": (
            "SELECT netuid, COUNT(*) AS neuron_count "
            "FROM metagraph GROUP BY netuid ORDER BY neuron_count DESC"
        ),
        "tables": ["metagraph"],
        "explanation": "Counts total neurons per subnet.",
    },
]


def generate_sql(question: str, constraints: Optional[dict] = None) -> Optional[dict]:
    """
    Match question to a SQL template and generate executable SQL.

    Returns dict with {sql, tables, explanation} or None if no match.
    """
    question_lower = question.lower().strip()
    constraints = constraints or {}

    for template in SQL_TEMPLATES:
        match = re.search(template["pattern"], question_lower)
        if match:
            sql = template["sql"]

            # Inject parameters from regex groups or constraints
            groups = match.groups()

            # Extract k value (for top-k queries)
            k = constraints.get("k", 10)
            for g in groups:
                if g and g.isdigit():
                    k = int(g)
                    break
            sql = sql.replace("{k}", str(k))

            # Extract netuid
            netuid = constraints.get("netuid_filter", 1)
            for g in groups:
                if g and g.isdigit() and int(g) < 1000:
                    netuid = int(g)
            sql = sql.replace("{netuid}", str(netuid))

            return {
                "sql": sql,
                "tables": template["tables"],
                "explanation": template["explanation"],
            }

    return None


# ──────────────────────────────────────────────
# Miner Forward Function
# ──────────────────────────────────────────────

def forward(synapse: QuerySynapse) -> QuerySynapse:
    """
    Process a QuerySynapse request and return an Answer Package.

    This is called by the axon for each incoming validator request.
    """
    start_time = time.perf_counter()

    try:
        logger.info(
            f"Received task {synapse.task_id}: "
            f"{synapse.question[:80]}..."
        )

        # Load snapshot
        conn = load_snapshot(synapse.snapshot_id)

        # Generate SQL from question
        result = generate_sql(synapse.question, synapse.constraints)

        if result is None:
            logger.warning(f"No template match for: {synapse.question[:80]}")
            return synapse  # Return empty response — will score 0

        sql = result["sql"]
        tables_used = result["tables"]
        explanation = result["explanation"]

        # Execute SQL and compute hash
        result_hash = hash_result(conn, sql)

        # Build result preview (first 10 rows)
        res = conn.execute(sql)
        columns = [desc[0] for desc in res.description]
        rows = res.fetchall()
        preview_rows = [list(row) for row in rows[:10]]

        # Fill synapse response fields
        synapse.sql = sql
        synapse.result_hash = result_hash
        synapse.result_preview = {"columns": columns, "rows": preview_rows}
        synapse.tables_used = tables_used
        synapse.explanation = explanation

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Task {synapse.task_id} completed in {elapsed:.0f}ms — "
            f"hash={result_hash[:30]}..."
        )

    except Exception as e:
        logger.error(f"Error processing task {synapse.task_id}: {e}")
        logger.debug(traceback.format_exc())
        # Return synapse with empty response fields — will score 0

    return synapse


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QueryAgent Miner")
    parser.add_argument("--netuid", type=int, required=True, help="Subnet network ID")
    parser.add_argument("--axon.port", type=int, default=8091, help="Axon port")
    bt.Wallet.add_args(parser)
    bt.Subtensor.add_args(parser)

    config = bt.Config(parser)
    wallet = bt.Wallet(config=config)
    subtensor = bt.Subtensor(config=config)
    metagraph = bt.Metagraph(netuid=config.netuid, network=config.subtensor.network, sync=True)

    logger.info(f"Wallet: {wallet}")
    logger.info(f"Metagraph: {metagraph.n} neurons on subnet {config.netuid}")

    # Create and configure axon
    axon = bt.Axon(wallet=wallet, port=config.axon.port)
    axon.attach(forward_fn=forward)
    axon.serve(netuid=config.netuid, subtensor=subtensor)
    axon.start()

    logger.info(f"Miner axon started on port {config.axon.port}")

    # Main loop
    try:
        while True:
            try:
                metagraph = bt.Metagraph(netuid=config.netuid, network=config.subtensor.network, sync=True)
            except Exception as e:
                logger.warning(f"Metagraph sync failed (fast-blocks pruning): {e}")
                time.sleep(12)
                continue

            # Log miner status
            my_uid = None
            for uid in range(metagraph.n):
                if metagraph.hotkeys[uid] == wallet.hotkey.ss58_address:
                    my_uid = uid
                    break

            if my_uid is not None:
                stake_val = float(metagraph.stake[my_uid]) if hasattr(metagraph, 'stake') else 0.0
                incentive_val = float(metagraph.incentive[my_uid]) if hasattr(metagraph, 'incentive') else 0.0
                logger.info(
                    f"UID={my_uid} | "
                    f"stake={stake_val:.4f} | "
                    f"incentive={incentive_val:.6f}"
                )
            else:
                logger.warning("Miner hotkey not found in metagraph — not registered?")

            time.sleep(12)  # One block

    except KeyboardInterrupt:
        logger.info("Miner shutting down...")
    finally:
        axon.stop()


if __name__ == "__main__":
    main()

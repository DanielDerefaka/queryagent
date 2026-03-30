"""
QueryAgent Task Generator — creates task pool and computes ground truth hashes.

Reads a snapshot, executes reference SQL for each task definition,
computes SHA-256 ground truth hashes, and outputs:
- benchmark/tasks/public_tasks.json
- benchmark/tasks/hidden_tasks.json
- benchmark/ground_truth/QB-XXX.json (one per task)

Usage:
    python scripts/generate_tasks.py --snapshot bt_snapshot_2026_03_v1
"""

import argparse
import json
import logging
from pathlib import Path

from queryagent.config import GROUND_TRUTH_DIR, TASKS_DIR
from queryagent.hashing import hash_result
from queryagent.snapshot import load_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ── Task definitions ──
# Each task has: task_id, question, reference_sql, tier, budget_ms
# The ground_truth_hash is computed by running reference_sql on the snapshot.

TASK_DEFINITIONS = [
    # ── EASY (30%) ──
    {
        "task_id": "QB-001",
        "question": "What is the total TAO staked across all subnets?",
        "reference_sql": "SELECT SUM(stake) AS total_staked FROM stakes",
        "tier": "easy",
        "budget_ms": 5000,
    },
    {
        "task_id": "QB-002",
        "question": "How many active subnets are there?",
        "reference_sql": "SELECT COUNT(DISTINCT netuid) AS subnet_count FROM subnets",
        "tier": "easy",
        "budget_ms": 5000,
    },
    {
        "task_id": "QB-003",
        "question": "How many active miners are on subnet 1?",
        "reference_sql": "SELECT COUNT(*) AS miner_count FROM miners WHERE netuid = 1 AND active = true",
        "tier": "easy",
        "budget_ms": 5000,
    },
    {
        "task_id": "QB-004",
        "question": "What is the total emission across all subnets?",
        "reference_sql": "SELECT SUM(emission) AS total_emission FROM emissions",
        "tier": "easy",
        "budget_ms": 5000,
    },
    {
        "task_id": "QB-005",
        "question": "How many validators have non-zero stake?",
        "reference_sql": "SELECT COUNT(*) AS validator_count FROM validators WHERE stake > 0",
        "tier": "easy",
        "budget_ms": 5000,
    },
    {
        "task_id": "QB-006",
        "question": "What is the average stake per validator?",
        "reference_sql": "SELECT AVG(stake) AS avg_stake FROM validators WHERE stake > 0",
        "tier": "easy",
        "budget_ms": 5000,
    },

    # ── MEDIUM (50%) ──
    {
        "task_id": "QB-010",
        "question": "Top 10 validators by stake across all subnets",
        "reference_sql": (
            "SELECT netuid, uid, hotkey, stake "
            "FROM validators "
            "ORDER BY stake DESC "
            "LIMIT 10"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-011",
        "question": "Which subnet has the highest total emission?",
        "reference_sql": (
            "SELECT netuid, SUM(emission) AS total_emission "
            "FROM emissions "
            "GROUP BY netuid "
            "ORDER BY total_emission DESC "
            "LIMIT 1"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-012",
        "question": "Top 10 miners by incentive score",
        "reference_sql": (
            "SELECT netuid, uid, hotkey, incentive "
            "FROM miners "
            "ORDER BY incentive DESC "
            "LIMIT 10"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-013",
        "question": "Average validator trust per subnet",
        "reference_sql": (
            "SELECT netuid, AVG(validator_trust) AS avg_vtrust "
            "FROM validators "
            "GROUP BY netuid "
            "ORDER BY avg_vtrust DESC"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-014",
        "question": "Subnets ranked by number of active miners",
        "reference_sql": (
            "SELECT netuid, COUNT(*) AS active_miners "
            "FROM miners "
            "WHERE active = true "
            "GROUP BY netuid "
            "ORDER BY active_miners DESC"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-015",
        "question": "Distribution of stake across subnets (total stake per subnet)",
        "reference_sql": (
            "SELECT netuid, SUM(stake) AS total_stake "
            "FROM metagraph "
            "GROUP BY netuid "
            "ORDER BY total_stake DESC"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-016",
        "question": "Top 5 subnets by emission per active miner",
        "reference_sql": (
            "SELECT e.netuid, "
            "SUM(e.emission) / NULLIF(COUNT(DISTINCT m.uid), 0) AS emission_per_miner "
            "FROM emissions e "
            "JOIN miners m ON e.netuid = m.netuid AND m.active = true "
            "GROUP BY e.netuid "
            "ORDER BY emission_per_miner DESC "
            "LIMIT 5"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-017",
        "question": "Validators with highest dividends across all subnets",
        "reference_sql": (
            "SELECT netuid, uid, hotkey, dividends "
            "FROM validators "
            "ORDER BY dividends DESC "
            "LIMIT 10"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-018",
        "question": "Subnets where the top validator holds more than 50% of total stake",
        "reference_sql": (
            "WITH subnet_stakes AS ("
            "  SELECT netuid, uid, stake, "
            "    SUM(stake) OVER (PARTITION BY netuid) AS total_stake "
            "  FROM validators"
            ") "
            "SELECT netuid, uid, stake, total_stake, "
            "  stake / NULLIF(total_stake, 0) AS stake_share "
            "FROM subnet_stakes "
            "WHERE stake / NULLIF(total_stake, 0) > 0.5 "
            "ORDER BY stake_share DESC"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },
    {
        "task_id": "QB-019",
        "question": "Number of neurons per subnet (validators + miners)",
        "reference_sql": (
            "SELECT netuid, COUNT(*) AS neuron_count "
            "FROM metagraph "
            "GROUP BY netuid "
            "ORDER BY neuron_count DESC"
        ),
        "tier": "medium",
        "budget_ms": 8000,
    },

    # ── HARD (20%) ──
    {
        "task_id": "QB-030",
        "question": "Subnets where average validator trust is above network average but total emission is below network average",
        "reference_sql": (
            "WITH subnet_stats AS ("
            "  SELECT netuid, "
            "    AVG(validator_trust) AS avg_vtrust, "
            "    SUM(emission) AS total_emission "
            "  FROM metagraph "
            "  GROUP BY netuid"
            "), "
            "network_avg AS ("
            "  SELECT "
            "    AVG(avg_vtrust) AS net_avg_vtrust, "
            "    AVG(total_emission) AS net_avg_emission "
            "  FROM subnet_stats"
            ") "
            "SELECT s.netuid, s.avg_vtrust, s.total_emission "
            "FROM subnet_stats s, network_avg n "
            "WHERE s.avg_vtrust > n.net_avg_vtrust "
            "  AND s.total_emission < n.net_avg_emission "
            "ORDER BY s.avg_vtrust DESC"
        ),
        "tier": "hard",
        "budget_ms": 15000,
    },
    {
        "task_id": "QB-031",
        "question": "Correlation between stake concentration (max stake share) and number of active miners per subnet",
        "reference_sql": (
            "WITH stake_conc AS ("
            "  SELECT netuid, "
            "    MAX(stake) / NULLIF(SUM(stake), 0) AS max_stake_share "
            "  FROM metagraph "
            "  GROUP BY netuid"
            "), "
            "miner_counts AS ("
            "  SELECT netuid, COUNT(*) AS active_miners "
            "  FROM miners "
            "  WHERE active = true "
            "  GROUP BY netuid"
            ") "
            "SELECT sc.netuid, sc.max_stake_share, mc.active_miners "
            "FROM stake_conc sc "
            "JOIN miner_counts mc ON sc.netuid = mc.netuid "
            "ORDER BY sc.max_stake_share DESC"
        ),
        "tier": "hard",
        "budget_ms": 15000,
    },
    {
        "task_id": "QB-032",
        "question": "For each subnet, rank validators by emission efficiency (emission / stake) and show top 3",
        "reference_sql": (
            "WITH ranked AS ("
            "  SELECT netuid, uid, hotkey, stake, emission, "
            "    emission / NULLIF(stake, 0) AS efficiency, "
            "    ROW_NUMBER() OVER (PARTITION BY netuid ORDER BY emission / NULLIF(stake, 0) DESC) AS rn "
            "  FROM validators "
            "  WHERE stake > 0"
            ") "
            "SELECT netuid, uid, hotkey, stake, emission, efficiency "
            "FROM ranked "
            "WHERE rn <= 3 "
            "ORDER BY netuid, efficiency DESC"
        ),
        "tier": "hard",
        "budget_ms": 15000,
    },
    {
        "task_id": "QB-033",
        "question": "Subnets with highest Gini coefficient of stake distribution",
        "reference_sql": (
            "WITH ordered AS ("
            "  SELECT netuid, stake, "
            "    ROW_NUMBER() OVER (PARTITION BY netuid ORDER BY stake) AS i, "
            "    COUNT(*) OVER (PARTITION BY netuid) AS n, "
            "    SUM(stake) OVER (PARTITION BY netuid) AS total "
            "  FROM metagraph "
            "  WHERE stake > 0"
            ") "
            "SELECT netuid, "
            "  1 - (2.0 / (n * NULLIF(total, 0))) * SUM(stake * (n + 1 - i)) AS gini "
            "FROM ordered "
            "GROUP BY netuid, n, total "
            "HAVING n > 1 "
            "ORDER BY gini DESC"
        ),
        "tier": "hard",
        "budget_ms": 15000,
    },
]


def generate_ground_truth(snapshot_id: str) -> None:
    """
    Load snapshot, execute reference SQL for each task, compute ground truth hashes,
    and write task + ground truth files.
    """
    logger.info(f"Loading snapshot: {snapshot_id}")
    conn = load_snapshot(snapshot_id, use_cache=False)

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    public_tasks = []
    hidden_tasks = []
    success = 0
    failed = 0

    for task_def in TASK_DEFINITIONS:
        task_id = task_def["task_id"]
        logger.info(f"Processing {task_id}: {task_def['question'][:60]}...")

        try:
            ground_truth_hash = hash_result(conn, task_def["reference_sql"])

            # Ground truth file (validator-only, includes reference SQL + hash)
            gt = {
                "task_id": task_id,
                "snapshot_id": snapshot_id,
                "reference_sql": task_def["reference_sql"],
                "ground_truth_hash": ground_truth_hash,
                "tier": task_def["tier"],
                "budget_ms": task_def["budget_ms"],
            }

            gt_path = GROUND_TRUTH_DIR / f"{task_id}.json"
            with open(gt_path, "w") as f:
                json.dump(gt, f, indent=2)

            # Public task entry (no reference SQL or hash — miners can't see these)
            task_entry = {
                "task_id": task_id,
                "snapshot_id": snapshot_id,
                "question": task_def["question"],
                "tier": task_def["tier"],
                "constraints": {},
                "budget_ms": task_def["budget_ms"],
                "latency_ms": 30000,
            }

            # Mark some tasks as hidden (every 5th task starting from QB-030+)
            is_hidden = task_id.startswith("QB-03")
            if is_hidden:
                hidden_tasks.append(task_entry)
            else:
                public_tasks.append(task_entry)

            success += 1
            logger.info(f"  {task_id}: {ground_truth_hash[:30]}... ({'hidden' if is_hidden else 'public'})")

        except Exception as e:
            failed += 1
            logger.error(f"  {task_id} FAILED: {e}")

    # Write task pool files
    with open(TASKS_DIR / "public_tasks.json", "w") as f:
        json.dump(public_tasks, f, indent=2)

    with open(TASKS_DIR / "hidden_tasks.json", "w") as f:
        json.dump(hidden_tasks, f, indent=2)

    logger.info(
        f"Done! {success} succeeded, {failed} failed. "
        f"{len(public_tasks)} public, {len(hidden_tasks)} hidden."
    )


def main():
    parser = argparse.ArgumentParser(description="Generate QueryAgent tasks and ground truth")
    parser.add_argument(
        "--snapshot",
        type=str,
        required=True,
        help="Snapshot ID (e.g. bt_snapshot_2026_03_v1)",
    )
    args = parser.parse_args()

    generate_ground_truth(args.snapshot)


if __name__ == "__main__":
    main()

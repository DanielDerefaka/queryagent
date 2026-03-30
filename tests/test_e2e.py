"""
End-to-end test: simulates the full miner → validator loop locally.

1. Load snapshot
2. Miner generates SQL from a task question
3. Miner computes hash
4. Validator re-executes miner SQL, computes hash
5. Validator compares hash to ground truth
6. Validator scores the response
"""

import json
from pathlib import Path

import pytest

from queryagent.config import GROUND_TRUTH_DIR, TASKS_DIR
from queryagent.hashing import hash_result
from queryagent.scoring import compute_score
from queryagent.snapshot import execute_sql_safe, load_snapshot

# Import miner's SQL generation
from neurons.miner import generate_sql


SNAPSHOT_ID = "bt_snapshot_test_v1"


@pytest.fixture(scope="module")
def snapshot_conn():
    """Load the real testnet snapshot."""
    return load_snapshot(SNAPSHOT_ID, use_cache=False)


@pytest.fixture(scope="module")
def public_tasks():
    """Load public tasks."""
    path = TASKS_DIR / "public_tasks.json"
    if not path.exists():
        pytest.skip("No public_tasks.json — run generate_tasks.py first")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ground_truth():
    """Load all ground truth hashes."""
    gt = {}
    if not GROUND_TRUTH_DIR.exists():
        pytest.skip("No ground_truth dir — run generate_tasks.py first")
    for gt_file in GROUND_TRUTH_DIR.glob("*.json"):
        with open(gt_file) as f:
            data = json.load(f)
            gt[data["task_id"]] = data
    return gt


def test_snapshot_loads(snapshot_conn):
    """Snapshot loads successfully with real data."""
    result = snapshot_conn.execute("SELECT COUNT(*) FROM metagraph").fetchone()
    assert result[0] > 0, "Metagraph table should have data"


def test_miner_generates_sql_for_easy_tasks(snapshot_conn, public_tasks, ground_truth):
    """Miner should match and correctly answer easy tasks."""
    easy_tasks = [t for t in public_tasks if t["tier"] == "easy"]
    matched = 0
    correct = 0

    for task in easy_tasks:
        result = generate_sql(task["question"], task.get("constraints"))
        if result is None:
            continue
        matched += 1

        # Miner computes hash
        miner_hash = hash_result(snapshot_conn, result["sql"])

        # Validator re-executes and computes hash
        columns, rows, exec_ms = execute_sql_safe(snapshot_conn, result["sql"])

        # Validator checks against ground truth
        gt = ground_truth.get(task["task_id"])
        if gt and miner_hash == gt["ground_truth_hash"]:
            correct += 1

    assert matched >= len(easy_tasks) * 0.8, f"Should match most easy tasks: {matched}/{len(easy_tasks)}"
    assert correct >= matched * 0.8, f"Should get most matched tasks correct: {correct}/{matched}"


def test_miner_generates_sql_for_medium_tasks(snapshot_conn, public_tasks, ground_truth):
    """Miner should match and correctly answer medium tasks."""
    medium_tasks = [t for t in public_tasks if t["tier"] == "medium"]
    matched = 0
    correct = 0

    for task in medium_tasks:
        result = generate_sql(task["question"], task.get("constraints"))
        if result is None:
            continue
        matched += 1

        miner_hash = hash_result(snapshot_conn, result["sql"])
        gt = ground_truth.get(task["task_id"])
        if gt and miner_hash == gt["ground_truth_hash"]:
            correct += 1

    assert matched >= len(medium_tasks) * 0.5, f"Should match most medium tasks: {matched}/{len(medium_tasks)}"


def test_full_scoring_loop(snapshot_conn, public_tasks, ground_truth):
    """Full loop: miner answers → validator re-executes → scores."""
    task = public_tasks[0]  # First easy task
    gt = ground_truth[task["task_id"]]

    # Miner generates SQL
    result = generate_sql(task["question"], task.get("constraints"))
    assert result is not None, f"Miner should match task: {task['question']}"

    # Miner executes and hashes
    miner_hash = hash_result(snapshot_conn, result["sql"])

    # Validator re-executes (timed)
    columns, rows, exec_ms = execute_sql_safe(snapshot_conn, result["sql"])

    # Validator computes own hash
    from queryagent.hashing import hash_from_rows
    validator_hash = hash_from_rows(columns, rows)

    # Hashes should match (determinism)
    assert miner_hash == validator_hash, "Miner and validator hashes should match (deterministic)"

    # Compare to ground truth
    hash_matches = validator_hash == gt["ground_truth_hash"]
    assert hash_matches, f"Hash should match ground truth for {task['task_id']}"

    # Score
    score = compute_score(
        hash_matches=hash_matches,
        exec_ms=exec_ms,
        budget_ms=task["budget_ms"],
        response_ms=100,  # simulated
        latency_ms=task["latency_ms"],
    )

    assert 0.75 <= score <= 1.0, f"Correct answer should score 0.75-1.0, got {score}"
    print(f"\nTask {task['task_id']}: score={score:.4f} (exec={exec_ms:.1f}ms)")


def test_wrong_answer_scores_zero(snapshot_conn, public_tasks, ground_truth):
    """A wrong SQL should score 0.0."""
    task = public_tasks[0]
    gt = ground_truth[task["task_id"]]

    # Execute wrong SQL
    wrong_sql = "SELECT COUNT(*) AS wrong FROM subnets WHERE netuid = 999"
    columns, rows, exec_ms = execute_sql_safe(snapshot_conn, wrong_sql)

    from queryagent.hashing import hash_from_rows
    wrong_hash = hash_from_rows(columns, rows)

    hash_matches = wrong_hash == gt["ground_truth_hash"]
    assert not hash_matches, "Wrong SQL should not match ground truth"

    score = compute_score(
        hash_matches=hash_matches,
        exec_ms=exec_ms,
        budget_ms=task["budget_ms"],
        response_ms=100,
        latency_ms=task["latency_ms"],
    )

    assert score == 0.0, "Wrong answer should score 0.0"

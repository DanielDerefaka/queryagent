"""
Wire test: spins up a real Axon + Dendrite on localhost to test the full
Bittensor network layer without needing chain registration.

Tests:
1. Miner axon starts and accepts QuerySynapse
2. Dendrite sends synapse, gets back Answer Package
3. Validator re-executes miner SQL, verifies hash
4. Scoring produces correct result
"""

import asyncio
import json
import time

import bittensor as bt
import pytest

from queryagent.config import GROUND_TRUTH_DIR, TASKS_DIR
from queryagent.hashing import hash_from_rows, hash_result
from queryagent.protocol import QuerySynapse
from queryagent.scoring import compute_score
from queryagent.snapshot import execute_sql_safe, load_snapshot
from neurons.miner import forward as miner_forward


SNAPSHOT_ID = "bt_snapshot_test_v1"
AXON_PORT = 19091  # Use high port to avoid conflicts


@pytest.fixture(scope="module")
def public_tasks():
    path = TASKS_DIR / "public_tasks.json"
    if not path.exists():
        pytest.skip("No public_tasks.json — run generate_tasks.py first")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ground_truth():
    gt = {}
    if not GROUND_TRUTH_DIR.exists():
        pytest.skip("No ground_truth dir — run generate_tasks.py first")
    for gt_file in GROUND_TRUTH_DIR.glob("*.json"):
        with open(gt_file) as f:
            data = json.load(f)
            gt[data["task_id"]] = data
    return gt


@pytest.fixture(scope="module")
def wallet():
    """Create a mock wallet for testing (no real keys needed)."""
    w = bt.Wallet(name="test_miner", hotkey="test_hotkey")
    w.create_if_non_existent(coldkey_use_password=False, hotkey_use_password=False)
    return w


@pytest.fixture(scope="module")
def axon(wallet):
    """Start a real axon with the miner forward function."""
    ax = bt.Axon(wallet=wallet, port=AXON_PORT)
    ax.attach(forward_fn=miner_forward)
    ax.start()
    time.sleep(1)  # Give axon time to start
    yield ax
    ax.stop()


@pytest.fixture(scope="module")
def dendrite(wallet):
    """Create a dendrite for sending requests."""
    return bt.Dendrite(wallet=wallet)


@pytest.fixture(scope="module")
def snapshot_conn():
    return load_snapshot(SNAPSHOT_ID, use_cache=False)


def test_axon_starts(axon):
    """Axon should start and be reachable."""
    # In bt v10, check that the axon object exists and has started
    assert axon is not None
    assert axon.port == AXON_PORT


def test_dendrite_sends_synapse(axon, dendrite, public_tasks):
    """Dendrite sends QuerySynapse to axon and gets back Answer Package."""
    task = public_tasks[0]

    synapse = QuerySynapse(
        task_id=task["task_id"],
        snapshot_id=SNAPSHOT_ID,
        question=task["question"],
        constraints=task.get("constraints", {}),
    )

    # Send via dendrite to local axon
    response = asyncio.get_event_loop().run_until_complete(
        dendrite.call(target_axon=axon, synapse=synapse, timeout=30.0, deserialize=False)
    )

    assert response.sql is not None, "Miner should return SQL"
    assert response.result_hash is not None, "Miner should return result hash"
    assert response.result_hash.startswith("sha256:"), "Hash should be sha256 format"
    assert response.tables_used is not None, "Miner should return tables used"
    assert response.explanation is not None, "Miner should return explanation"

    print(f"\nMiner response for {task['task_id']}:")
    print(f"  SQL: {response.sql[:80]}...")
    print(f"  Hash: {response.result_hash[:40]}...")
    print(f"  Tables: {response.tables_used}")


def test_full_wire_loop(axon, dendrite, snapshot_conn, public_tasks, ground_truth):
    """
    Full wire loop:
    1. Validator sends task via dendrite
    2. Miner responds via axon
    3. Validator re-executes SQL
    4. Validator compares hash to ground truth
    5. Validator scores
    """
    task = public_tasks[0]
    gt = ground_truth[task["task_id"]]

    # Step 1: Validator sends synapse
    synapse = QuerySynapse(
        task_id=task["task_id"],
        snapshot_id=SNAPSHOT_ID,
        question=task["question"],
        constraints=task.get("constraints", {}),
    )

    start_time = time.perf_counter()
    response = asyncio.get_event_loop().run_until_complete(
        dendrite.call(target_axon=axon, synapse=synapse, timeout=30.0, deserialize=False)
    )
    response_ms = (time.perf_counter() - start_time) * 1000

    assert response.sql is not None, "Miner should return SQL"

    # Step 2: Validator re-executes miner's SQL (timed)
    columns, rows, exec_ms = execute_sql_safe(snapshot_conn, response.sql)

    # Step 3: Validator computes hash from re-execution
    validator_hash = hash_from_rows(columns, rows)

    # Step 4: Compare to ground truth
    hash_matches = validator_hash == gt["ground_truth_hash"]
    assert hash_matches, (
        f"Validator re-execution hash should match ground truth.\n"
        f"  Validator: {validator_hash}\n"
        f"  Truth:     {gt['ground_truth_hash']}\n"
        f"  Miner:     {response.result_hash}"
    )

    # Also verify miner's self-reported hash matches
    assert response.result_hash == validator_hash, (
        "Miner's hash should match validator's re-execution hash (determinism)"
    )

    # Step 5: Score
    score = compute_score(
        hash_matches=hash_matches,
        exec_ms=exec_ms,
        budget_ms=task["budget_ms"],
        response_ms=response_ms,
        latency_ms=task.get("latency_ms", 30000),
    )

    assert 0.75 <= score <= 1.0, f"Correct answer should score 0.75-1.0, got {score}"

    print(f"\n=== Full Wire Loop Result ===")
    print(f"  Task: {task['task_id']} — {task['question'][:60]}")
    print(f"  SQL: {response.sql[:80]}")
    print(f"  Hash match: {hash_matches}")
    print(f"  Exec time: {exec_ms:.1f}ms")
    print(f"  Response time: {response_ms:.1f}ms")
    print(f"  Score: {score:.4f}")


def test_multiple_tasks_over_wire(axon, dendrite, snapshot_conn, public_tasks, ground_truth):
    """Send multiple tasks over the wire and score all of them."""
    results = []

    for task in public_tasks[:5]:  # Test first 5 tasks
        synapse = QuerySynapse(
            task_id=task["task_id"],
            snapshot_id=SNAPSHOT_ID,
            question=task["question"],
            constraints=task.get("constraints", {}),
        )

        start_time = time.perf_counter()
        response = asyncio.get_event_loop().run_until_complete(
            dendrite.call(target_axon=axon, synapse=synapse, timeout=30.0, deserialize=False)
        )
        response_ms = (time.perf_counter() - start_time) * 1000

        if response.sql is None:
            results.append({"task_id": task["task_id"], "score": 0.0, "matched": False})
            continue

        # Validator re-executes
        try:
            columns, rows, exec_ms = execute_sql_safe(snapshot_conn, response.sql)
            validator_hash = hash_from_rows(columns, rows)
        except Exception:
            results.append({"task_id": task["task_id"], "score": 0.0, "matched": True, "error": True})
            continue

        gt = ground_truth.get(task["task_id"])
        hash_matches = gt and validator_hash == gt["ground_truth_hash"]

        score = compute_score(
            hash_matches=bool(hash_matches),
            exec_ms=exec_ms,
            budget_ms=task["budget_ms"],
            response_ms=response_ms,
            latency_ms=task.get("latency_ms", 30000),
        )

        results.append({
            "task_id": task["task_id"],
            "score": score,
            "matched": True,
            "hash_ok": hash_matches,
            "exec_ms": exec_ms,
        })

    print("\n=== Multi-Task Wire Results ===")
    for r in results:
        status = "CORRECT" if r.get("hash_ok") else ("NO MATCH" if r.get("matched") else "NO SQL")
        print(f"  {r['task_id']}: score={r['score']:.4f} [{status}]")

    # At least 3 out of 5 should score > 0
    correct = sum(1 for r in results if r["score"] > 0)
    assert correct >= 3, f"Should get at least 3/5 correct over wire, got {correct}"

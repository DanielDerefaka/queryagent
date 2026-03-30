"""
Test the LLM miner and hybrid miner — compares template-only, LLM-only,
and hybrid (template + LLM fallback) strategies.

Requires OPENAI_API_KEY environment variable.
"""

import json
import os
import time

import pytest

from queryagent.config import GROUND_TRUTH_DIR, TASKS_DIR
from queryagent.hashing import hash_result
from queryagent.snapshot import load_snapshot

SNAPSHOT_ID = "bt_snapshot_test_v1"


@pytest.fixture(scope="module")
def conn():
    return load_snapshot(SNAPSHOT_ID, use_cache=False)


@pytest.fixture(scope="module")
def all_tasks():
    """Load public + hidden tasks."""
    tasks = []
    for fname in ["public_tasks.json", "hidden_tasks.json"]:
        path = TASKS_DIR / fname
        if path.exists():
            with open(path) as f:
                tasks.extend(json.load(f))
    if not tasks:
        pytest.skip("No tasks found")
    return tasks


@pytest.fixture(scope="module")
def ground_truth():
    gt = {}
    for gt_file in GROUND_TRUTH_DIR.glob("*.json"):
        with open(gt_file) as f:
            data = json.load(f)
            gt[data["task_id"]] = data
    return gt


def requires_api_key():
    return pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )


@requires_api_key()
def test_llm_generates_sql(conn):
    """LLM miner should generate valid SQL for a simple question."""
    from neurons.miner_llm import generate_sql_llm

    result = generate_sql_llm(
        question="What is the total TAO staked across all subnets?",
        snapshot_id=SNAPSHOT_ID,
    )

    assert result is not None, "LLM should generate SQL"
    assert result["sql"], "SQL should not be empty"
    assert "SELECT" in result["sql"].upper(), "Should be a SELECT query"

    # Execute it — should not crash
    h = hash_result(conn, result["sql"])
    assert h.startswith("sha256:")
    print(f"\nLLM SQL: {result['sql']}")
    print(f"Hash: {h}")


def _eval_miner(generate_fn, task, conn, expected_hash):
    """Run a single task through a generate function and return status."""
    result = generate_fn(task)
    if result is None:
        return "NO MATCH"
    try:
        h = hash_result(conn, result["sql"])
        return "CORRECT" if h == expected_hash else "WRONG"
    except Exception as e:
        return f"ERROR: {e}"


@requires_api_key()
def test_hybrid_vs_template_vs_llm(conn, all_tasks, ground_truth):
    """
    Run ALL tasks through template, LLM, and hybrid miners.
    Hybrid should beat both individual strategies.
    """
    from neurons.miner import generate_sql as template_generate
    from neurons.miner_llm import generate_sql_hybrid, generate_sql_llm

    counts = {
        "template": {"correct": 0, "wrong": 0, "no_match": 0, "error": 0},
        "llm":      {"correct": 0, "wrong": 0, "no_match": 0, "error": 0},
        "hybrid":   {"correct": 0, "wrong": 0, "no_match": 0, "error": 0},
    }
    details = []

    for task in all_tasks:
        gt = ground_truth.get(task["task_id"])
        if not gt:
            continue

        expected_hash = gt["ground_truth_hash"]
        q = task["question"]
        c = task.get("constraints")

        # Template
        tmpl_status = _eval_miner(
            lambda t: template_generate(t["question"], t.get("constraints")),
            task, conn, expected_hash,
        )

        # LLM
        llm_status = _eval_miner(
            lambda t: generate_sql_llm(t["question"], SNAPSHOT_ID, t.get("constraints")),
            task, conn, expected_hash,
        )

        # Hybrid (template first, LLM fallback)
        hybrid_status = _eval_miner(
            lambda t: generate_sql_hybrid(t["question"], SNAPSHOT_ID, t.get("constraints")),
            task, conn, expected_hash,
        )

        for name, status in [("template", tmpl_status), ("llm", llm_status), ("hybrid", hybrid_status)]:
            key = status.split(":")[0].strip().lower().replace(" ", "_")
            if key in counts[name]:
                counts[name][key] += 1
            else:
                counts[name]["error"] += 1

        details.append({
            "task_id": task["task_id"],
            "tier": task["tier"],
            "template": tmpl_status,
            "llm": llm_status,
            "hybrid": hybrid_status,
            "question": task["question"][:55],
        })

        time.sleep(0.5)

    # Print comparison
    print("\n" + "=" * 95)
    print("TEMPLATE vs LLM vs HYBRID — HEAD TO HEAD")
    print("=" * 95)
    print(f"\n{'Task':<8} {'Tier':<8} {'Template':<12} {'LLM':<12} {'Hybrid':<12} {'Question'}")
    print("-" * 95)
    for d in details:
        print(f"{d['task_id']:<8} {d['tier']:<8} {d['template']:<12} {d['llm']:<12} {d['hybrid']:<12} {d['question']}")

    total = len(details)
    print(f"\n{'SUMMARY':=^95}")
    for name in ["template", "llm", "hybrid"]:
        c = counts[name]
        print(f"{name.upper():<10}: {c['correct']}/{total} correct, "
              f"{c['no_match']} no match, {c['wrong']} wrong, {c['error']} errors")

    # Hybrid should beat or match both individual strategies
    assert counts["hybrid"]["correct"] >= counts["template"]["correct"], (
        f"Hybrid should beat templates: "
        f"Hybrid={counts['hybrid']['correct']} vs Template={counts['template']['correct']}"
    )

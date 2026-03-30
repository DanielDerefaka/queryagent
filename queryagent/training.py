"""
Training data collector — persists scored miner responses to JSONL.

Every validation round produces training examples:
- score > 0.80 → "positive" (good SQL, correct answer)
- score < 0.50 → "negative" (bad SQL, wrong answer)
- 0.50–0.80   → skipped (ambiguous quality)

This is Layer 2 of the three-layer architecture:
  Subnet (Layer 1) → Training Pipeline (Layer 2) → Product AI (Layer 3)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from queryagent.config import SNAPSHOT_DIR

logger = logging.getLogger(__name__)

TRAINING_DIR = Path(os.environ.get(
    "QA_TRAINING_DIR",
    str(SNAPSHOT_DIR.parent / "training_data"),
))

POSITIVE_THRESHOLD = 0.80
NEGATIVE_THRESHOLD = 0.50


def _ensure_dir():
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)


def save_training_example(
    task_id: str,
    snapshot_id: str,
    question: str,
    constraints: Optional[dict],
    miner_uid: int,
    miner_sql: Optional[str],
    miner_hash: Optional[str],
    ground_truth_hash: str,
    score: float,
    exec_ms: Optional[float] = None,
    response_ms: Optional[float] = None,
    block: Optional[int] = None,
    tier: Optional[str] = None,
    is_hidden: bool = False,
    tables_used: Optional[list] = None,
    explanation: Optional[str] = None,
) -> Optional[str]:
    """
    Save a single scored miner response as a training example.

    Returns the label ("positive", "negative") or None if skipped.
    """
    if miner_sql is None:
        return None

    # Quality gate
    if score >= POSITIVE_THRESHOLD:
        label = "positive"
    elif score < NEGATIVE_THRESHOLD:
        label = "negative"
    else:
        return None  # Ambiguous — skip

    _ensure_dir()

    example = {
        "task_id": task_id,
        "snapshot_id": snapshot_id,
        "question": question,
        "constraints": constraints,
        "sql": miner_sql,
        "result_hash": miner_hash,
        "ground_truth_hash": ground_truth_hash,
        "score": round(score, 4),
        "label": label,
        "miner_uid": miner_uid,
        "exec_ms": round(exec_ms, 2) if exec_ms is not None else None,
        "response_ms": round(response_ms, 2) if response_ms is not None else None,
        "block": block,
        "tier": tier,
        "is_hidden": is_hidden,
        "tables_used": tables_used,
        "explanation": explanation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Append to date-partitioned JSONL file
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = TRAINING_DIR / f"training_{date_str}.jsonl"

    with open(filepath, "a") as f:
        f.write(json.dumps(example) + "\n")

    return label


def save_round_training_data(
    task,
    ground_truth_hash: str,
    responses: list,
    round_scores: list,
    exec_results: list,
    response_times_ms: list,
    block: Optional[int] = None,
):
    """
    Save training data for an entire validation round.

    Called from validator after scoring. Iterates all miner responses
    and persists those that pass the quality gate.
    """
    saved = {"positive": 0, "negative": 0, "skipped": 0}

    for i, response in enumerate(responses):
        if response is None:
            saved["skipped"] += 1
            continue

        miner_sql = getattr(response, "sql", None)
        miner_hash = getattr(response, "result_hash", None)
        tables_used = getattr(response, "tables_used", None)
        explanation = getattr(response, "explanation", None)

        # round_scores is a tensor indexed by UID; exec_results/response_times_ms are dicts keyed by UID
        score = float(round_scores[i]) if i < len(round_scores) else 0.0

        exec_ms = None
        if isinstance(exec_results, dict) and i in exec_results:
            exec_ms = exec_results[i].get("exec_ms")
        elif isinstance(exec_results, (list, tuple)) and i < len(exec_results) and exec_results[i] is not None:
            exec_ms = exec_results[i]

        resp_ms = None
        if isinstance(response_times_ms, dict) and i in response_times_ms:
            resp_ms = response_times_ms[i]
        elif isinstance(response_times_ms, (list, tuple)) and i < len(response_times_ms):
            resp_ms = response_times_ms[i]

        label = save_training_example(
            task_id=task.task_id,
            snapshot_id=task.snapshot_id,
            question=task.question,
            constraints=task.constraints,
            miner_uid=i,
            miner_sql=miner_sql,
            miner_hash=miner_hash,
            ground_truth_hash=ground_truth_hash,
            score=score,
            exec_ms=exec_ms,
            response_ms=resp_ms,
            block=block,
            tier=task.tier,
            is_hidden=task.is_hidden,
            tables_used=tables_used,
            explanation=explanation,
        )

        if label == "positive":
            saved["positive"] += 1
        elif label == "negative":
            saved["negative"] += 1
        else:
            saved["skipped"] += 1

    logger.info(
        f"Training data: {saved['positive']} positive, "
        f"{saved['negative']} negative, {saved['skipped']} skipped"
    )
    return saved


def get_training_stats() -> dict:
    """Get stats about accumulated training data."""
    _ensure_dir()

    stats = {
        "total_examples": 0,
        "positive": 0,
        "negative": 0,
        "files": 0,
        "earliest": None,
        "latest": None,
    }

    for f in sorted(TRAINING_DIR.glob("training_*.jsonl")):
        stats["files"] += 1
        with open(f) as fh:
            for line in fh:
                try:
                    ex = json.loads(line.strip())
                    stats["total_examples"] += 1
                    if ex.get("label") == "positive":
                        stats["positive"] += 1
                    elif ex.get("label") == "negative":
                        stats["negative"] += 1

                    ts = ex.get("timestamp")
                    if ts:
                        if stats["earliest"] is None or ts < stats["earliest"]:
                            stats["earliest"] = ts
                        if stats["latest"] is None or ts > stats["latest"]:
                            stats["latest"] = ts
                except json.JSONDecodeError:
                    continue

    return stats


def load_training_dataset(label_filter: Optional[str] = None) -> list:
    """
    Load all training examples, optionally filtered by label.

    Returns list of dicts ready for fine-tuning pipelines.
    """
    _ensure_dir()
    examples = []

    for f in sorted(TRAINING_DIR.glob("training_*.jsonl")):
        with open(f) as fh:
            for line in fh:
                try:
                    ex = json.loads(line.strip())
                    if label_filter is None or ex.get("label") == label_filter:
                        examples.append(ex)
                except json.JSONDecodeError:
                    continue

    return examples

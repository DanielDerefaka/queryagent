"""
QueryAgent Scoring — computes miner scores, EMA smoothing, and weight normalization.

Scoring formula:
    IF hash mismatch or error → score = 0.0
    IF hash matches:
        score = 0.75 + 0.15 × efficiency + 0.10 × latency

    efficiency = max(0.0, 1 - exec_ms / budget_ms)
    latency    = max(0.0, 1 - response_ms / latency_ms)

EMA smoothing:
    EMA[uid] = α × new_score + (1 - α) × EMA[uid]
    α = 0.1

Weight normalization:
    weight[uid] = EMA[uid] / Σ(EMA)
"""

import logging
from typing import Optional

import numpy as np
import torch

from queryagent.config import (
    CORRECTNESS_WEIGHT,
    EFFICIENCY_WEIGHT,
    EMA_ALPHA,
    LATENCY_WEIGHT,
)

logger = logging.getLogger(__name__)


def compute_score(
    hash_matches: bool,
    exec_ms: float,
    budget_ms: float,
    response_ms: float,
    latency_ms: float,
) -> float:
    """
    Compute a single miner's score for one round.

    Args:
        hash_matches: Whether the miner's result hash matches ground truth
        exec_ms: SQL execution time on validator's DuckDB (milliseconds)
        budget_ms: Maximum allowed execution time for this task
        response_ms: End-to-end response time from miner (milliseconds)
        latency_ms: Maximum allowed response time for this task

    Returns:
        Score in [0.0, 1.0]. Zero if hash doesn't match.
    """
    if not hash_matches:
        return 0.0

    efficiency = max(0.0, 1.0 - exec_ms / budget_ms) if budget_ms > 0 else 0.0
    latency = max(0.0, 1.0 - response_ms / latency_ms) if latency_ms > 0 else 0.0

    score = CORRECTNESS_WEIGHT + EFFICIENCY_WEIGHT * efficiency + LATENCY_WEIGHT * latency
    return min(score, 1.0)


def update_ema(
    scores: torch.Tensor,
    new_scores: list[float],
    alpha: float = EMA_ALPHA,
) -> torch.Tensor:
    """
    Apply EMA smoothing to scores across rounds.

    Args:
        scores: Current EMA scores tensor (one per UID)
        new_scores: New scores from this round (one per UID)
        alpha: Smoothing factor (default 0.1)

    Returns:
        Updated EMA scores tensor.
    """
    new = torch.tensor(new_scores, dtype=torch.float32)
    return alpha * new + (1.0 - alpha) * scores


def normalize_weights(scores: torch.Tensor) -> torch.Tensor:
    """
    Normalize EMA scores to weights that sum to 1.0.

    Miners with zero scores get zero weight.
    If all scores are zero, returns uniform zero weights.
    """
    total = scores.sum()
    if total == 0:
        return torch.zeros_like(scores)
    return scores / total


def score_responses(
    responses: list,
    ground_truth_hash: str,
    exec_results: list[Optional[tuple]],
    budget_ms: float,
    latency_ms: float,
    response_times_ms: list[float],
) -> list[float]:
    """
    Score a batch of miner responses for a single task.

    Args:
        responses: List of QuerySynapse responses from miners
        ground_truth_hash: Expected hash for this task
        exec_results: List of (validator_hash, exec_ms) tuples from re-execution.
                      None if re-execution failed.
        budget_ms: Task execution budget
        latency_ms: Task latency budget
        response_times_ms: End-to-end response times per miner

    Returns:
        List of scores (one per miner).
    """
    scores = []

    for i, response in enumerate(responses):
        # No response or missing SQL
        if response is None or response.sql is None or response.result_hash is None:
            scores.append(0.0)
            continue

        # Re-execution failed
        if exec_results[i] is None:
            scores.append(0.0)
            continue

        validator_hash, exec_ms = exec_results[i]

        # Hash comparison — the hard gate
        hash_matches = validator_hash == ground_truth_hash

        if not hash_matches:
            logger.debug(
                f"UID {i}: hash mismatch "
                f"(validator={validator_hash[:20]}... vs truth={ground_truth_hash[:20]}...)"
            )

        score = compute_score(
            hash_matches=hash_matches,
            exec_ms=exec_ms,
            budget_ms=budget_ms,
            response_ms=response_times_ms[i],
            latency_ms=latency_ms,
        )
        scores.append(score)

    return scores

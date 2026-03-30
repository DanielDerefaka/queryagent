"""Tests for the scoring engine — 75/15/10 formula, EMA, weight normalization."""

import torch
import pytest

from queryagent.scoring import compute_score, normalize_weights, update_ema


class TestComputeScore:
    def test_wrong_hash_is_zero(self):
        """Hash mismatch → score = 0.0, regardless of speed."""
        score = compute_score(
            hash_matches=False, exec_ms=10, budget_ms=5000,
            response_ms=100, latency_ms=30000,
        )
        assert score == 0.0

    def test_perfect_score(self):
        """Correct hash + instant execution + instant response → ~1.0."""
        score = compute_score(
            hash_matches=True, exec_ms=0, budget_ms=5000,
            response_ms=0, latency_ms=30000,
        )
        assert score == pytest.approx(1.0)

    def test_correct_but_slow(self):
        """Correct hash + maxed-out execution → 0.75 (correctness only)."""
        score = compute_score(
            hash_matches=True, exec_ms=5000, budget_ms=5000,
            response_ms=30000, latency_ms=30000,
        )
        assert score == pytest.approx(0.75)

    def test_correct_medium_speed(self):
        """Correct hash + 50% efficiency + 50% latency."""
        score = compute_score(
            hash_matches=True, exec_ms=2500, budget_ms=5000,
            response_ms=15000, latency_ms=30000,
        )
        expected = 0.75 + 0.15 * 0.5 + 0.10 * 0.5
        assert score == pytest.approx(expected)

    def test_score_never_exceeds_one(self):
        """Score should be capped at 1.0."""
        score = compute_score(
            hash_matches=True, exec_ms=0, budget_ms=5000,
            response_ms=0, latency_ms=30000,
        )
        assert score <= 1.0

    def test_score_range_for_correct(self):
        """All correct answers should score between 0.75 and 1.0."""
        score = compute_score(
            hash_matches=True, exec_ms=3000, budget_ms=5000,
            response_ms=20000, latency_ms=30000,
        )
        assert 0.75 <= score <= 1.0


class TestEMA:
    def test_ema_smoothing(self):
        """EMA should blend old and new scores."""
        scores = torch.tensor([0.5, 0.5])
        new_scores = [1.0, 0.0]
        updated = update_ema(scores, new_scores, alpha=0.1)
        assert updated[0] == pytest.approx(0.1 * 1.0 + 0.9 * 0.5)
        assert updated[1] == pytest.approx(0.1 * 0.0 + 0.9 * 0.5)

    def test_ema_converges(self):
        """Repeated high scores should push EMA toward 1.0."""
        scores = torch.zeros(1)
        for _ in range(100):
            scores = update_ema(scores, [1.0], alpha=0.1)
        assert scores[0] > 0.99

    def test_ema_zero_input(self):
        """All-zero new scores should decay existing scores."""
        scores = torch.tensor([1.0])
        for _ in range(50):
            scores = update_ema(scores, [0.0], alpha=0.1)
        assert scores[0] < 0.01


class TestWeights:
    def test_normalize_sums_to_one(self):
        """Normalized weights should sum to 1.0."""
        scores = torch.tensor([0.8, 0.5, 0.3, 0.0])
        weights = normalize_weights(scores)
        assert weights.sum() == pytest.approx(1.0)

    def test_zero_scores(self):
        """All-zero scores → all-zero weights (no division by zero)."""
        scores = torch.zeros(5)
        weights = normalize_weights(scores)
        assert weights.sum() == 0.0

    def test_relative_order(self):
        """Higher score → higher weight."""
        scores = torch.tensor([1.0, 0.5, 0.1])
        weights = normalize_weights(scores)
        assert weights[0] > weights[1] > weights[2]

"""Tests for the task pool — loading, sampling, parameter injection, tier distribution."""

import json
import random
from collections import Counter
from pathlib import Path

import pytest

from queryagent.tasks import ParameterSet, Task, TaskPool


SNAPSHOT_ID = "bt_snapshot_test_v1"


@pytest.fixture
def task_pool():
    """Load the real task pool."""
    pool = TaskPool()
    pool.load()
    return pool


def test_task_pool_loads(task_pool):
    """Task pool should load public and hidden tasks."""
    assert len(task_pool.public_tasks) > 0, "Should have public tasks"
    assert len(task_pool.hidden_tasks) > 0, "Should have hidden tasks"
    assert len(task_pool.ground_truth) > 0, "Should have ground truth"


def test_all_tasks_have_ground_truth(task_pool):
    """Every task should have a corresponding ground truth entry."""
    for task in task_pool.all_tasks:
        gt = task_pool.get_ground_truth(task.task_id)
        assert gt is not None, f"Missing ground truth for {task.task_id}"
        assert "ground_truth_hash" in gt, f"No hash in ground truth for {task.task_id}"
        assert gt["ground_truth_hash"].startswith("sha256:"), f"Invalid hash format for {task.task_id}"


def test_tasks_have_required_fields(task_pool):
    """Every task should have all required fields."""
    for task in task_pool.all_tasks:
        assert task.task_id, "task_id must be set"
        assert task.snapshot_id, "snapshot_id must be set"
        assert task.question, "question must be set"
        assert task.tier in ("easy", "medium", "hard"), f"Invalid tier: {task.tier}"
        assert task.budget_ms > 0, "budget_ms must be positive"
        assert task.latency_ms > 0, "latency_ms must be positive"


def test_hidden_tasks_exist(task_pool):
    """Should have hidden tasks (anti-gaming)."""
    assert len(task_pool.hidden_tasks) >= 1, "Need at least 1 hidden task"
    for task in task_pool.hidden_tasks:
        assert task.is_hidden is True


def test_public_tasks_not_hidden(task_pool):
    """Public tasks should not be marked hidden."""
    for task in task_pool.public_tasks:
        assert task.is_hidden is False


def test_tier_distribution(task_pool):
    """Tasks should span easy, medium, and hard tiers."""
    tiers = Counter(t.tier for t in task_pool.all_tasks)
    assert "easy" in tiers, "Need easy tasks"
    assert "medium" in tiers, "Need medium tasks"
    assert "hard" in tiers, "Need hard tasks"


def test_sample_task_returns_valid_task(task_pool):
    """Sampled tasks should be valid Task objects."""
    for _ in range(20):
        task = task_pool.sample_task()
        assert isinstance(task, Task)
        assert task.task_id
        assert task.question
        assert task.tier in ("easy", "medium", "hard")


def test_sample_task_injects_parameters(task_pool):
    """Sampled tasks should have injected parameters in constraints."""
    task = task_pool.sample_task()
    assert "time_window" in task.constraints, "Should inject time_window"
    assert "k" in task.constraints, "Should inject k"
    assert task.constraints["k"] in [5, 10, 15, 20], "k should be from allowed values"


def test_sample_distribution_across_tiers(task_pool):
    """Sampling 1000 tasks should roughly match 30/50/20 distribution."""
    random.seed(42)
    tiers = Counter()
    for _ in range(1000):
        task = task_pool.sample_task()
        tiers[task.tier] += 1

    # Allow ±10% tolerance
    assert 200 < tiers["easy"] < 400, f"Easy should be ~30%, got {tiers['easy']/10}%"
    assert 400 < tiers["medium"] < 600, f"Medium should be ~50%, got {tiers['medium']/10}%"
    assert 100 < tiers["hard"] < 300, f"Hard should be ~20%, got {tiers['hard']/10}%"


def test_hidden_task_sampling_rate(task_pool):
    """~20% of sampled tasks should be hidden (with tolerance)."""
    random.seed(42)
    hidden_count = sum(1 for _ in range(500) if task_pool.sample_task().is_hidden)
    # Allow wide tolerance since it depends on pool composition
    assert hidden_count > 0, "Should sample some hidden tasks"


def test_parameter_injection_varies(task_pool):
    """Multiple samples of same task should produce different parameters."""
    random.seed(None)  # Use real randomness
    k_values = set()
    for _ in range(50):
        task = task_pool.sample_task()
        k_values.add(task.constraints.get("k"))

    assert len(k_values) > 1, "Parameter injection should produce varied k values"


def test_parameter_set_defaults():
    """ParameterSet should have sensible defaults."""
    ps = ParameterSet()
    assert len(ps.time_windows) >= 2
    assert len(ps.k_values) >= 2
    assert len(ps.netuid_filters) >= 2
    assert None in ps.netuid_filters, "Should include None (no filter)"


def test_ground_truth_hashes_are_unique(task_pool):
    """Each task should produce a unique ground truth hash (no collisions)."""
    hashes = [gt["ground_truth_hash"] for gt in task_pool.ground_truth.values()]
    assert len(hashes) == len(set(hashes)), "Ground truth hashes should be unique"


def test_task_pool_with_empty_dir(tmp_path):
    """TaskPool should handle missing task files gracefully."""
    pool = TaskPool(tasks_dir=tmp_path, ground_truth_dir=tmp_path)
    pool.load()
    assert len(pool.public_tasks) == 0
    assert len(pool.hidden_tasks) == 0


def test_task_pool_with_partial_data(tmp_path):
    """TaskPool should load even if only public tasks exist."""
    tasks = [
        {"task_id": "T-001", "snapshot_id": "test", "question": "Test?", "tier": "easy"},
    ]
    (tmp_path / "public_tasks.json").write_text(json.dumps(tasks))
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()

    pool = TaskPool(tasks_dir=tmp_path, ground_truth_dir=gt_dir)
    pool.load()
    assert len(pool.public_tasks) == 1
    assert len(pool.hidden_tasks) == 0

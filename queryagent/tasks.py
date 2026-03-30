"""
QueryAgent Task Pool — manages tasks, ground truth, sampling, and parameter injection.

The task pool contains public tasks (visible to everyone) and hidden tasks
(validator-only, never published). Tasks are sampled by difficulty tier with
randomized parameters to prevent memorization.
"""

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from queryagent.config import (
    EASY_SHARE,
    GROUND_TRUTH_DIR,
    HARD_SHARE,
    HIDDEN_RATIO,
    MEDIUM_SHARE,
    TASKS_DIR,
    TIERS,
)

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """A single benchmark task with ground truth."""

    task_id: str
    snapshot_id: str
    question: str
    tier: str  # "easy" | "medium" | "hard"
    is_hidden: bool = False
    constraints: dict = field(default_factory=dict)
    reference_sql: str = ""
    ground_truth_hash: str = ""
    budget_ms: int = 5000
    latency_ms: int = 30000


@dataclass
class ParameterSet:
    """Randomizable parameters injected into tasks at query time."""

    time_windows: list[str] = field(
        default_factory=lambda: ["7 days", "14 days", "30 days", "90 days"]
    )
    k_values: list[int] = field(default_factory=lambda: [5, 10, 15, 20])
    netuid_filters: list[Optional[int]] = field(
        default_factory=lambda: [None, 1, 8, 18, 32]
    )


class TaskPool:
    """
    Manages the full task pool: public + hidden tasks + ground truth.

    Usage:
        pool = TaskPool()
        pool.load()
        task = pool.sample_task()
    """

    def __init__(
        self,
        tasks_dir: Optional[Path] = None,
        ground_truth_dir: Optional[Path] = None,
    ):
        self.tasks_dir = tasks_dir or TASKS_DIR
        self.ground_truth_dir = ground_truth_dir or GROUND_TRUTH_DIR

        self.public_tasks: list[Task] = []
        self.hidden_tasks: list[Task] = []
        self.ground_truth: dict[str, dict] = {}  # task_id → ground truth data
        self.params = ParameterSet()

        # Indexed by tier for weighted sampling
        self._by_tier: dict[str, list[Task]] = {"easy": [], "medium": [], "hard": []}

    def load(self) -> None:
        """Load all tasks and ground truth from disk."""
        self._load_tasks(self.tasks_dir / "public_tasks.json", is_hidden=False)
        self._load_tasks(self.tasks_dir / "hidden_tasks.json", is_hidden=True)
        self._load_ground_truth()
        self._index_by_tier()

        logger.info(
            f"TaskPool loaded: {len(self.public_tasks)} public, "
            f"{len(self.hidden_tasks)} hidden, "
            f"{len(self.ground_truth)} ground truth entries"
        )

    def _load_tasks(self, path: Path, is_hidden: bool) -> None:
        """Load tasks from a JSON file."""
        if not path.exists():
            logger.warning(f"Task file not found: {path}")
            return

        with open(path) as f:
            data = json.load(f)

        for item in data:
            task = Task(
                task_id=item["task_id"],
                snapshot_id=item["snapshot_id"],
                question=item["question"],
                tier=item.get("tier", "medium"),
                is_hidden=is_hidden,
                constraints=item.get("constraints", {}),
                budget_ms=item.get("budget_ms", TIERS.get(item.get("tier", "medium"), {}).get("budget_ms", 5000)),
                latency_ms=item.get("latency_ms", 30000),
            )

            if is_hidden:
                self.hidden_tasks.append(task)
            else:
                self.public_tasks.append(task)

    def _load_ground_truth(self) -> None:
        """Load ground truth files (one per task)."""
        if not self.ground_truth_dir.exists():
            logger.warning(f"Ground truth dir not found: {self.ground_truth_dir}")
            return

        for gt_file in sorted(self.ground_truth_dir.glob("*.json")):
            with open(gt_file) as f:
                data = json.load(f)
            task_id = data.get("task_id", gt_file.stem)
            self.ground_truth[task_id] = data

            # Attach ground truth to matching tasks
            for task in self.public_tasks + self.hidden_tasks:
                if task.task_id == task_id:
                    task.reference_sql = data.get("reference_sql", "")
                    task.ground_truth_hash = data.get("ground_truth_hash", "")

    def _index_by_tier(self) -> None:
        """Build tier index for weighted sampling."""
        self._by_tier = {"easy": [], "medium": [], "hard": []}
        for task in self.public_tasks + self.hidden_tasks:
            if task.tier in self._by_tier:
                self._by_tier[task.tier].append(task)

    @property
    def all_tasks(self) -> list[Task]:
        """Return all tasks (public + hidden)."""
        return self.public_tasks + self.hidden_tasks

    def sample_task(self) -> Task:
        """
        Sample a single task using weighted difficulty distribution.

        - 30% easy, 50% medium, 20% hard
        - ~20% chance of sampling a hidden task
        - Parameters randomized (time window, k, netuid)
        """
        # Decide if hidden
        use_hidden = random.random() < HIDDEN_RATIO

        # Pick tier by weight
        tier = random.choices(
            population=["easy", "medium", "hard"],
            weights=[EASY_SHARE, MEDIUM_SHARE, HARD_SHARE],
            k=1,
        )[0]

        # Get candidates from the chosen tier
        if use_hidden:
            candidates = [t for t in self._by_tier.get(tier, []) if t.is_hidden]
            if not candidates:
                candidates = [t for t in self.hidden_tasks]
        else:
            candidates = [t for t in self._by_tier.get(tier, []) if not t.is_hidden]
            if not candidates:
                candidates = [t for t in self.public_tasks]

        if not candidates:
            raise RuntimeError(f"No tasks available for tier={tier}, hidden={use_hidden}")

        task = random.choice(candidates)
        return self._inject_parameters(task)

    def _inject_parameters(self, task: Task) -> Task:
        """
        Create a copy of the task with randomized parameters injected.
        This prevents miners from memorizing exact parameter combinations.
        """
        injected = Task(
            task_id=task.task_id,
            snapshot_id=task.snapshot_id,
            question=task.question,
            tier=task.tier,
            is_hidden=task.is_hidden,
            constraints=dict(task.constraints),
            reference_sql=task.reference_sql,
            ground_truth_hash=task.ground_truth_hash,
            budget_ms=task.budget_ms,
            latency_ms=task.latency_ms,
        )

        # Inject random parameters into constraints
        injected.constraints["time_window"] = random.choice(self.params.time_windows)
        injected.constraints["k"] = random.choice(self.params.k_values)

        netuid = random.choice(self.params.netuid_filters)
        if netuid is not None:
            injected.constraints["netuid_filter"] = netuid

        return injected

    def get_ground_truth(self, task_id: str) -> Optional[dict]:
        """Get ground truth data for a task."""
        return self.ground_truth.get(task_id)

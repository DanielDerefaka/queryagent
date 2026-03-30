"""
QueryAgent Configuration — shared constants and defaults.

All tunable parameters in one place. Import from here, not hardcoded values.
"""

from pathlib import Path

# ── Project root ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Scoring weights ──
CORRECTNESS_WEIGHT = 0.75
EFFICIENCY_WEIGHT = 0.15
LATENCY_WEIGHT = 0.10

# ── EMA smoothing ──
EMA_ALPHA = 0.1

# ── Task distribution ──
EASY_SHARE = 0.30
MEDIUM_SHARE = 0.50
HARD_SHARE = 0.20
HIDDEN_RATIO = 0.20  # fraction of sampled tasks that are hidden

# ── Timeouts ──
DEFAULT_TIMEOUT_S = 30        # seconds — miner must respond within this
DEFAULT_BUDGET_MS = 5000      # milliseconds — max SQL execution time on validator
DEFAULT_LATENCY_MS = 30000    # milliseconds — max end-to-end response time

# ── Paths ──
SNAPSHOT_DIR = PROJECT_ROOT / "benchmark" / "snapshots"
TASKS_DIR = PROJECT_ROOT / "benchmark" / "tasks"
GROUND_TRUTH_DIR = PROJECT_ROOT / "benchmark" / "ground_truth"

# ── Hashing ──
FLOAT_PRECISION = 6           # decimal places for float rounding in canonical form
NULL_REPR = "\x00NULL\x00"    # canonical NULL representation (sentinel, can't appear in real data)
HASH_ALGORITHM = "sha256"

# ── Snapshot tables (expected in every snapshot) ──
EXPECTED_TABLES = [
    "subnets",
    "validators",
    "miners",
    "stakes",
    "emissions",
    "metagraph",
]

# ── Difficulty tiers ──
TIERS = {
    "easy": {"share": EASY_SHARE, "budget_ms": 5000, "latency_ms": 30000},
    "medium": {"share": MEDIUM_SHARE, "budget_ms": 8000, "latency_ms": 30000},
    "hard": {"share": HARD_SHARE, "budget_ms": 15000, "latency_ms": 30000},
}

# ── Validator ──
WEIGHTS_RATE_LIMIT_BLOCKS = 20    # min blocks between set_weights() calls
METAGRAPH_SYNC_INTERVAL_S = 120   # seconds between metagraph syncs

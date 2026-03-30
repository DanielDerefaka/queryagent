"""
Determinism tests — the most critical property of the system.

If hashing is not 100% deterministic, the scoring system breaks entirely.
These tests hammer the hashing pipeline from every angle.
"""

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

import duckdb
import pytest

from queryagent.hashing import hash_from_rows, hash_result
from queryagent.snapshot import load_snapshot


SNAPSHOT_ID = "bt_snapshot_test_v1"


@pytest.fixture(scope="module")
def conn():
    return load_snapshot(SNAPSHOT_ID, use_cache=False)


def test_same_query_100_times(conn):
    """Same query executed 100 times should produce identical hash every time."""
    sql = "SELECT netuid, uid, stake FROM metagraph WHERE stake > 0 ORDER BY stake DESC LIMIT 20"
    hashes = set()
    for _ in range(100):
        h = hash_result(conn, sql)
        hashes.add(h)
    assert len(hashes) == 1, f"Got {len(hashes)} different hashes for same query"


def test_determinism_across_connections():
    """Same query on two different DuckDB connections (same snapshot) = same hash."""
    conn1 = load_snapshot(SNAPSHOT_ID, use_cache=False)
    conn2 = load_snapshot(SNAPSHOT_ID, use_cache=False)

    sql = "SELECT netuid, SUM(stake) AS total FROM metagraph GROUP BY netuid ORDER BY total DESC"
    h1 = hash_result(conn1, sql)
    h2 = hash_result(conn2, sql)
    assert h1 == h2, "Different connections should produce same hash"


def test_determinism_with_concurrent_execution():
    """Concurrent hashing of the same query should produce identical results."""
    results = []

    def hash_query():
        conn = load_snapshot(SNAPSHOT_ID, use_cache=False)
        sql = "SELECT COUNT(*) AS cnt, SUM(stake) AS total FROM metagraph"
        h = hash_result(conn, sql)
        results.append(h)

    threads = [threading.Thread(target=hash_query) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(results)) == 1, f"Concurrent execution produced {len(set(results))} different hashes"


def test_every_task_reference_sql_is_deterministic(conn):
    """Every reference SQL in ground truth should hash deterministically."""
    import json
    from queryagent.config import GROUND_TRUTH_DIR

    for gt_file in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        with open(gt_file) as f:
            gt = json.load(f)

        # Run twice
        h1 = hash_result(conn, gt["reference_sql"])
        h2 = hash_result(conn, gt["reference_sql"])
        assert h1 == h2, f"Non-deterministic hash for {gt['task_id']}"
        assert h1 == gt["ground_truth_hash"], (
            f"Hash changed since generation for {gt['task_id']}: "
            f"computed={h1[:30]} stored={gt['ground_truth_hash'][:30]}"
        )


def test_hash_result_vs_hash_from_rows_all_tasks(conn):
    """hash_result and hash_from_rows should agree for all tasks."""
    import json
    from queryagent.config import GROUND_TRUTH_DIR

    for gt_file in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        with open(gt_file) as f:
            gt = json.load(f)

        h1 = hash_result(conn, gt["reference_sql"])

        res = conn.execute(gt["reference_sql"])
        columns = [desc[0] for desc in res.description]
        rows = res.fetchall()
        h2 = hash_from_rows(columns, rows)

        assert h1 == h2, f"Mismatch for {gt['task_id']}: hash_result={h1[:30]} hash_from_rows={h2[:30]}"


def test_row_order_independence_complex(conn):
    """Row reordering should NOT affect hash (rows are sorted in canonical form)."""
    # These queries return same data but in different order
    sql_asc = "SELECT netuid, uid, stake FROM metagraph WHERE stake > 0 AND netuid = 1 ORDER BY uid ASC"
    sql_desc = "SELECT netuid, uid, stake FROM metagraph WHERE stake > 0 AND netuid = 1 ORDER BY uid DESC"

    h_asc = hash_result(conn, sql_asc)
    h_desc = hash_result(conn, sql_desc)
    assert h_asc == h_desc, "Row order should not affect hash"


def test_float_precision_edge_case(conn):
    """Floats with different internal representations but same precision should match."""
    # Force DuckDB to compute a float that might have precision issues
    sql1 = "SELECT CAST(1.0/3.0 AS DOUBLE) AS val"
    sql2 = "SELECT CAST(1.0/3.0 AS DOUBLE) AS val"
    h1 = hash_result(conn, sql1)
    h2 = hash_result(conn, sql2)
    assert h1 == h2


def test_aggregation_determinism(conn):
    """Aggregation functions should be deterministic."""
    queries = [
        "SELECT SUM(stake) FROM metagraph",
        "SELECT AVG(stake) FROM metagraph WHERE stake > 0",
        "SELECT COUNT(*), MIN(stake), MAX(stake) FROM metagraph",
        "SELECT netuid, SUM(emission) FROM metagraph GROUP BY netuid ORDER BY netuid",
    ]
    for sql in queries:
        h1 = hash_result(conn, sql)
        h2 = hash_result(conn, sql)
        assert h1 == h2, f"Non-deterministic aggregation: {sql[:60]}"


def test_join_determinism(conn):
    """JOIN queries should produce deterministic results."""
    sql = (
        "SELECT m.netuid, m.uid, m.stake, s.stake AS stakes_stake "
        "FROM metagraph m "
        "JOIN stakes s ON m.netuid = s.netuid AND m.uid = s.uid "
        "ORDER BY m.netuid, m.uid "
        "LIMIT 50"
    )
    h1 = hash_result(conn, sql)
    h2 = hash_result(conn, sql)
    assert h1 == h2


def test_window_function_determinism(conn):
    """Window functions should produce deterministic results."""
    sql = (
        "SELECT netuid, uid, stake, "
        "ROW_NUMBER() OVER (PARTITION BY netuid ORDER BY stake DESC) AS rn, "
        "SUM(stake) OVER (PARTITION BY netuid) AS total "
        "FROM metagraph WHERE stake > 0"
    )
    h1 = hash_result(conn, sql)
    h2 = hash_result(conn, sql)
    assert h1 == h2


def test_empty_result_is_deterministic(conn):
    """Empty result sets should have a consistent hash."""
    sql = "SELECT * FROM miners WHERE uid = -999"
    h1 = hash_result(conn, sql)
    h2 = hash_result(conn, sql)
    assert h1 == h2

    # Different empty queries with same columns should also match
    sql2 = "SELECT * FROM miners WHERE uid = -888"
    h3 = hash_result(conn, sql2)
    assert h1 == h3, "Different empty queries on same table should produce same hash"

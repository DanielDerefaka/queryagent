"""Tests for snapshot loading and SQL execution safety."""

import json
import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from queryagent.snapshot import execute_sql_safe, load_snapshot


@pytest.fixture
def mock_snapshot(tmp_path):
    """Create a minimal mock snapshot for testing."""
    snapshot_dir = tmp_path / "test_snapshot"
    tables_dir = snapshot_dir / "tables"
    tables_dir.mkdir(parents=True)

    # Create a simple test table
    df = pd.DataFrame({
        "netuid": [1, 1, 2, 2],
        "uid": [0, 1, 0, 1],
        "stake": [100.0, 200.0, 50.0, 150.0],
        "active": [True, True, False, True],
    })
    pq.write_table(pa.Table.from_pandas(df), tables_dir / "miners.parquet")

    # Write schema.json
    schema = {
        "snapshot_id": "test_snapshot",
        "tables": [
            {
                "name": "miners",
                "columns": [
                    {"name": "netuid", "type": "INTEGER"},
                    {"name": "uid", "type": "INTEGER"},
                    {"name": "stake", "type": "DOUBLE"},
                    {"name": "active", "type": "BOOLEAN"},
                ],
            }
        ],
    }
    with open(snapshot_dir / "schema.json", "w") as f:
        json.dump(schema, f)

    # Write metadata.json
    metadata = {
        "snapshot_id": "test_snapshot",
        "build_time": "2026-03-01T00:00:00Z",
        "block_number": 100,
        "network": "test",
        "row_counts": {"miners": 4},
    }
    with open(snapshot_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    return snapshot_dir


def test_load_snapshot(mock_snapshot, monkeypatch):
    """Snapshot loads into DuckDB with correct data."""
    from queryagent import config, snapshot

    monkeypatch.setattr(config, "SNAPSHOT_DIR", mock_snapshot.parent)
    snapshot.clear_cache()

    conn = load_snapshot("test_snapshot", use_cache=False)
    result = conn.execute("SELECT COUNT(*) FROM miners").fetchone()
    assert result[0] == 4


def test_query_snapshot(mock_snapshot, monkeypatch):
    """Can run queries against loaded snapshot."""
    from queryagent import config, snapshot

    monkeypatch.setattr(config, "SNAPSHOT_DIR", mock_snapshot.parent)
    snapshot.clear_cache()

    conn = load_snapshot("test_snapshot", use_cache=False)
    result = conn.execute("SELECT SUM(stake) FROM miners").fetchone()
    assert result[0] == 500.0


def test_execute_sql_safe_blocks_writes(mock_snapshot, monkeypatch):
    """execute_sql_safe should reject write operations."""
    from queryagent import config, snapshot

    monkeypatch.setattr(config, "SNAPSHOT_DIR", mock_snapshot.parent)
    snapshot.clear_cache()

    conn = load_snapshot("test_snapshot", use_cache=False)

    with pytest.raises(ValueError, match="Forbidden"):
        execute_sql_safe(conn, "DROP TABLE miners")

    with pytest.raises(ValueError, match="Forbidden"):
        execute_sql_safe(conn, "INSERT INTO miners VALUES (3, 2, 999.0, true)")


def test_execute_sql_safe_returns_timing(mock_snapshot, monkeypatch):
    """execute_sql_safe should return columns, rows, and execution time."""
    from queryagent import config, snapshot

    monkeypatch.setattr(config, "SNAPSHOT_DIR", mock_snapshot.parent)
    snapshot.clear_cache()

    conn = load_snapshot("test_snapshot", use_cache=False)
    columns, rows, exec_ms = execute_sql_safe(conn, "SELECT COUNT(*) AS cnt FROM miners")

    assert columns == ["cnt"]
    assert rows[0][0] == 4
    assert exec_ms >= 0

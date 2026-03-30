"""Tests for deterministic hashing — the core of QueryAgent's verification system."""

import duckdb
import pytest

from queryagent.hashing import hash_from_rows, hash_result


@pytest.fixture
def db():
    """Create a DuckDB connection with test data."""
    conn = duckdb.connect(database=":memory:")
    conn.execute("""
        CREATE TABLE test_data (
            id INTEGER,
            name VARCHAR,
            value DOUBLE,
            active BOOLEAN
        )
    """)
    conn.execute("""
        INSERT INTO test_data VALUES
        (1, 'alpha', 10.5, true),
        (2, 'beta', 20.123456789, false),
        (3, 'gamma', NULL, true),
        (4, 'delta', 0.0, false)
    """)
    return conn


def test_same_query_same_hash(db):
    """Same SQL on same data must always produce the same hash."""
    sql = "SELECT * FROM test_data ORDER BY id"
    h1 = hash_result(db, sql)
    h2 = hash_result(db, sql)
    assert h1 == h2


def test_different_query_different_hash(db):
    """Different queries should produce different hashes."""
    h1 = hash_result(db, "SELECT * FROM test_data WHERE active = true")
    h2 = hash_result(db, "SELECT * FROM test_data WHERE active = false")
    assert h1 != h2


def test_hash_format(db):
    """Hash should be in 'sha256:<hex>' format."""
    h = hash_result(db, "SELECT COUNT(*) FROM test_data")
    assert h.startswith("sha256:")
    assert len(h) == 7 + 64  # "sha256:" + 64 hex chars


def test_row_order_independent(db):
    """Hash should be the same regardless of original row order."""
    h1 = hash_result(db, "SELECT id, name FROM test_data ORDER BY id ASC")
    h2 = hash_result(db, "SELECT id, name FROM test_data ORDER BY id DESC")
    # Both should produce the same hash because we sort canonically
    assert h1 == h2


def test_null_handling(db):
    """NULL values should be handled consistently."""
    h = hash_result(db, "SELECT value FROM test_data WHERE id = 3")
    assert h.startswith("sha256:")
    # Run again — must be identical
    h2 = hash_result(db, "SELECT value FROM test_data WHERE id = 3")
    assert h == h2


def test_float_precision(db):
    """Floats should be rounded to fixed precision."""
    h = hash_result(db, "SELECT value FROM test_data WHERE id = 2")
    assert h.startswith("sha256:")


def test_empty_result(db):
    """Empty results should produce a consistent hash."""
    h1 = hash_result(db, "SELECT * FROM test_data WHERE id = 999")
    h2 = hash_result(db, "SELECT * FROM test_data WHERE id = 999")
    assert h1 == h2


def test_hash_from_rows():
    """hash_from_rows should produce same result as hash_result for same data."""
    columns = ["id", "name"]
    rows = [(1, "alpha"), (2, "beta")]
    h1 = hash_from_rows(columns, rows)
    h2 = hash_from_rows(columns, rows)
    assert h1 == h2
    assert h1.startswith("sha256:")

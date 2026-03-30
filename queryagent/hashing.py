"""
QueryAgent Hashing — deterministic SHA-256 of DuckDB query results.

This is the core of the verification system. If this is not 100% deterministic,
miners and validators will compute different hashes for the same data and the
entire scoring system breaks.

Guarantees:
- Same SQL on same snapshot = same hash, always
- Float precision fixed to N decimal places
- NULLs have canonical string representation
- Rows sorted deterministically before hashing
- Dates formatted as ISO 8601
- Empty results produce a consistent hash
"""

import hashlib
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import duckdb

from queryagent.config import FLOAT_PRECISION, HASH_ALGORITHM, NULL_REPR


def _canonicalize_value(value: Any) -> str:
    """Convert a single value to its canonical string form."""
    if value is None:
        return NULL_REPR
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.{FLOAT_PRECISION}f}"
    if isinstance(value, Decimal):
        return f"{float(value):.{FLOAT_PRECISION}f}"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def _canonicalize_row(row: tuple) -> str:
    """Convert a row tuple to a canonical pipe-delimited string."""
    return "|".join(_canonicalize_value(v) for v in row)


def hash_result(conn: duckdb.DuckDBPyConnection, sql: str) -> str:
    """
    Execute SQL on a DuckDB connection and return a deterministic SHA-256 hash.

    Steps:
    1. Execute the SQL
    2. Get column names from the result description
    3. Fetch all rows
    4. Sort rows deterministically (lexicographic on canonical form)
    5. Build canonical string: column header + sorted rows
    6. SHA-256 hash the canonical string

    Returns:
        "sha256:<hex_digest>" or raises on execution error.
    """
    result = conn.execute(sql)
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    # Build canonical representation
    header = "|".join(columns)
    canonical_rows = sorted(_canonicalize_row(row) for row in rows)

    canonical = header + "\n" + "\n".join(canonical_rows)

    digest = hashlib.new(HASH_ALGORITHM, canonical.encode("utf-8")).hexdigest()
    return f"{HASH_ALGORITHM}:{digest}"


def hash_from_rows(columns: list[str], rows: list[tuple]) -> str:
    """
    Compute hash from pre-fetched columns and rows (no DB connection needed).
    Useful for ground truth generation where you already have the data.
    """
    header = "|".join(columns)
    canonical_rows = sorted(_canonicalize_row(row) for row in rows)

    canonical = header + "\n" + "\n".join(canonical_rows)

    digest = hashlib.new(HASH_ALGORITHM, canonical.encode("utf-8")).hexdigest()
    return f"{HASH_ALGORITHM}:{digest}"


def verify_hash(conn: duckdb.DuckDBPyConnection, sql: str, expected_hash: str) -> bool:
    """Execute SQL and check if result hash matches expected."""
    try:
        actual = hash_result(conn, sql)
        return actual == expected_hash
    except Exception:
        return False

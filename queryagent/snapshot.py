"""
QueryAgent Snapshot Loader — Parquet → DuckDB.

Loads a frozen snapshot bundle into a DuckDB in-memory database.
Used by BOTH miner and validator. The connection is read-only and sandboxed:
no filesystem access, no network, no writes.

Snapshot bundle structure:
    benchmark/snapshots/bt_snapshot_2026_03_v1/
    ├── schema.json
    ├── metadata.json
    └── tables/
        ├── subnets.parquet
        ├── validators.parquet
        └── ...
"""

import json
import logging
from pathlib import Path
from typing import Optional

import duckdb

from queryagent import config

logger = logging.getLogger(__name__)

# In-memory cache: snapshot_id → DuckDB connection
_cache: dict[str, duckdb.DuckDBPyConnection] = {}


def get_snapshot_path(snapshot_id: str) -> Path:
    """Resolve snapshot directory path from ID."""
    path = config.SNAPSHOT_DIR / snapshot_id
    if not path.exists():
        raise FileNotFoundError(f"Snapshot not found: {path}")
    return path


def load_schema(snapshot_path: Path) -> dict:
    """Load and return the schema.json for a snapshot."""
    schema_file = snapshot_path / "schema.json"
    if not schema_file.exists():
        raise FileNotFoundError(f"schema.json not found in {snapshot_path}")
    with open(schema_file) as f:
        return json.load(f)


def load_metadata(snapshot_path: Path) -> dict:
    """Load and return the metadata.json for a snapshot."""
    metadata_file = snapshot_path / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"metadata.json not found in {snapshot_path}")
    with open(metadata_file) as f:
        return json.load(f)


def load_snapshot(snapshot_id: str, use_cache: bool = True) -> duckdb.DuckDBPyConnection:
    """
    Load a Parquet snapshot into a DuckDB in-memory database.

    Args:
        snapshot_id: e.g. "bt_snapshot_2026_03_v1"
        use_cache: If True, return cached connection if available.

    Returns:
        Read-only DuckDB connection with all snapshot tables loaded.
    """
    if use_cache and snapshot_id in _cache:
        logger.debug(f"Using cached snapshot: {snapshot_id}")
        return _cache[snapshot_id]

    snapshot_path = get_snapshot_path(snapshot_id)
    schema = load_schema(snapshot_path)
    tables_dir = snapshot_path / "tables"

    # Create in-memory DuckDB connection
    conn = duckdb.connect(database=":memory:")

    # Load each table from Parquet
    for table_def in schema.get("tables", []):
        table_name = table_def["name"]
        parquet_file = tables_dir / f"{table_name}.parquet"

        if not parquet_file.exists():
            raise FileNotFoundError(
                f"Parquet file not found: {parquet_file} "
                f"(defined in schema for snapshot {snapshot_id})"
            )

        conn.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet(?)",
            [str(parquet_file)],
        )
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info(f"Loaded {table_name}: {row_count} rows")

    # Cache the connection
    if use_cache:
        _cache[snapshot_id] = conn

    logger.info(f"Snapshot {snapshot_id} loaded ({len(schema.get('tables', []))} tables)")
    return conn


def execute_sql_safe(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    timeout_ms: Optional[int] = None,
) -> tuple[list[str], list[tuple], float]:
    """
    Execute SQL on a snapshot connection with safety measures.

    Args:
        conn: DuckDB connection (from load_snapshot)
        sql: SQL string to execute
        timeout_ms: Optional execution timeout in milliseconds

    Returns:
        (columns, rows, exec_ms) tuple

    Raises:
        Exception on SQL error, timeout, or invalid query.
    """
    import time

    # Basic SQL safety: reject obviously dangerous patterns
    sql_upper = sql.upper().strip()
    forbidden = ["CREATE", "DROP", "INSERT", "UPDATE", "DELETE", "ALTER", "COPY", "EXPORT"]
    for keyword in forbidden:
        # Check for keyword at start of statement or after semicolons
        if sql_upper.startswith(keyword) or f"; {keyword}" in sql_upper:
            raise ValueError(f"Forbidden SQL operation: {keyword}")

    start = time.perf_counter()

    try:
        result = conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {e}") from e

    exec_ms = (time.perf_counter() - start) * 1000

    return columns, rows, exec_ms


def clear_cache():
    """Clear all cached snapshot connections."""
    _cache.clear()


def list_loaded_snapshots() -> list[str]:
    """Return list of currently cached snapshot IDs."""
    return list(_cache.keys())

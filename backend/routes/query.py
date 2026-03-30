"""
SQL query execution endpoint — runs SQL against DuckDB snapshot, returns results + hash.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from queryagent.hashing import hash_result
from queryagent.snapshot import load_snapshot, execute_sql_safe

router = APIRouter()

DEFAULT_SNAPSHOT = "bt_snapshot_test_v1"


class QueryRequest(BaseModel):
    sql: str
    snapshot_id: Optional[str] = None


class QueryResponse(BaseModel):
    columns: list[str]
    rows: list[list]
    row_count: int
    exec_ms: float
    result_hash: str
    snapshot_id: str


@router.post("/query", response_model=QueryResponse)
def run_query(req: QueryRequest):
    """Execute SQL against a DuckDB snapshot and return results with hash."""
    snapshot_id = req.snapshot_id or DEFAULT_SNAPSHOT
    sql = req.sql.strip()

    if not sql:
        raise HTTPException(status_code=400, detail="SQL query is empty")

    try:
        conn = load_snapshot(snapshot_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {snapshot_id}")

    try:
        columns, rows, exec_ms = execute_sql_safe(conn, sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")

    try:
        result_hash = hash_result(conn, sql)
    except Exception:
        result_hash = "sha256:error"

    # Convert rows to JSON-serializable lists
    serializable_rows = []
    for row in rows[:1000]:  # Cap at 1000 rows for API response
        serializable_rows.append([
            str(v) if v is not None else None
            for v in row
        ])

    return QueryResponse(
        columns=columns,
        rows=serializable_rows,
        row_count=len(rows),
        exec_ms=round(exec_ms, 2),
        result_hash=result_hash,
        snapshot_id=snapshot_id,
    )

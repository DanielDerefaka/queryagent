"""
Schema endpoint — returns snapshot table definitions for the data browser.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from queryagent.config import SNAPSHOT_DIR

router = APIRouter()

DEFAULT_SNAPSHOT = "bt_snapshot_test_v1"


@router.get("/schema")
def get_schema(snapshot_id: str = DEFAULT_SNAPSHOT):
    """Return the schema.json for a snapshot."""
    schema_path = SNAPSHOT_DIR / snapshot_id / "schema.json"

    if not schema_path.exists():
        raise HTTPException(status_code=404, detail=f"Schema not found for {snapshot_id}")

    with open(schema_path) as f:
        schema = json.load(f)

    return schema


@router.get("/schema/tables")
def get_tables(snapshot_id: str = DEFAULT_SNAPSHOT):
    """Return table names with row counts from metadata."""
    schema_path = SNAPSHOT_DIR / snapshot_id / "schema.json"
    metadata_path = SNAPSHOT_DIR / snapshot_id / "metadata.json"

    if not schema_path.exists():
        raise HTTPException(status_code=404, detail=f"Schema not found for {snapshot_id}")

    with open(schema_path) as f:
        schema = json.load(f)

    row_counts = {}
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
            row_counts = metadata.get("row_counts", {})

    tables = []
    for table in schema.get("tables", []):
        name = table["name"]
        tables.append({
            "name": name,
            "columns": table["columns"],
            "column_count": len(table["columns"]),
            "row_count": row_counts.get(name, 0),
        })

    return {"snapshot_id": snapshot_id, "tables": tables}

"""
Stats endpoint — returns aggregate subnet statistics from snapshot data.
"""

from fastapi import APIRouter, HTTPException

from queryagent.snapshot import load_snapshot

router = APIRouter()

DEFAULT_SNAPSHOT = "bt_snapshot_test_v1"


@router.get("/stats")
def get_stats(snapshot_id: str = DEFAULT_SNAPSHOT):
    """Return aggregate stats for the dashboard home page."""
    try:
        conn = load_snapshot(snapshot_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {snapshot_id}")

    stats = {}

    queries = {
        "total_subnets": "SELECT COUNT(DISTINCT netuid) as cnt FROM subnets",
        "total_miners": "SELECT COUNT(*) as cnt FROM miners",
        "total_validators": "SELECT COUNT(*) as cnt FROM validators",
        "total_staked": "SELECT COALESCE(SUM(stake), 0) as total FROM stakes",
        "total_emissions": "SELECT COALESCE(SUM(emission), 0) as total FROM emissions",
        "active_miners": "SELECT COUNT(*) as cnt FROM miners WHERE active = true",
        "active_validators": "SELECT COUNT(*) as cnt FROM validators WHERE active = true",
    }

    for key, sql in queries.items():
        try:
            result = conn.execute(sql)
            row = result.fetchone()
            val = row[0] if row else 0
            stats[key] = round(float(val), 4) if isinstance(val, float) else int(val)
        except Exception:
            stats[key] = 0

    # Top subnet by emission
    try:
        result = conn.execute("""
            SELECT netuid, SUM(emission) as total_emission
            FROM emissions
            GROUP BY netuid
            ORDER BY total_emission DESC
            LIMIT 1
        """)
        row = result.fetchone()
        if row:
            stats["top_subnet_netuid"] = int(row[0])
            stats["top_subnet_emission"] = round(float(row[1]), 4)
        else:
            stats["top_subnet_netuid"] = None
            stats["top_subnet_emission"] = 0
    except Exception:
        stats["top_subnet_netuid"] = None
        stats["top_subnet_emission"] = 0

    return {"snapshot_id": snapshot_id, "stats": stats}

"""
Leaderboard endpoint — returns miner/validator data from the snapshot or metagraph.

When running against a live Bittensor chain, this will pull from bt.Metagraph.
For now, it queries the DuckDB snapshot which has real testnet data.
"""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException

from queryagent.snapshot import load_snapshot

router = APIRouter()

DEFAULT_SNAPSHOT = "bt_snapshot_test_v1"


@router.get("/leaderboard")
def get_leaderboard(
    snapshot_id: str = DEFAULT_SNAPSHOT,
    sort_by: str = "incentive",
    limit: int = 50,
):
    """Return miner rankings from snapshot data."""
    try:
        conn = load_snapshot(snapshot_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {snapshot_id}")

    valid_sort = {"incentive", "stake", "emission", "trust", "consensus", "dividends"}
    if sort_by not in valid_sort:
        sort_by = "incentive"

    sql = f"""
        SELECT
            uid,
            hotkey,
            COALESCE(stake, 0) as stake,
            COALESCE(trust, 0) as trust,
            COALESCE(consensus, 0) as consensus,
            COALESCE(incentive, 0) as incentive,
            COALESCE(emission, 0) as emission,
            COALESCE(dividends, 0) as dividends,
            COALESCE(validator_trust, 0) as validator_trust,
            COALESCE(active, false) as active,
            netuid
        FROM metagraph
        ORDER BY {sort_by} DESC
        LIMIT {limit}
    """

    try:
        result = conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

    miners = []
    for i, row in enumerate(rows):
        miner = dict(zip(columns, row))
        miner["rank_position"] = i + 1
        # Convert numeric types for JSON
        for key in miner:
            if isinstance(miner[key], (float,)):
                miner[key] = round(miner[key], 6)
        miners.append(miner)

    return {
        "snapshot_id": snapshot_id,
        "sort_by": sort_by,
        "total": len(miners),
        "miners": miners,
    }


@router.get("/leaderboard/validators")
def get_validators(snapshot_id: str = DEFAULT_SNAPSHOT):
    """Return validator data from snapshot."""
    try:
        conn = load_snapshot(snapshot_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {snapshot_id}")

    sql = """
        SELECT
            uid,
            hotkey,
            COALESCE(stake, 0) as stake,
            COALESCE(validator_trust, 0) as validator_trust,
            COALESCE(dividends, 0) as dividends,
            COALESCE(active, false) as active,
            netuid
        FROM validators
        ORDER BY stake DESC
    """

    try:
        result = conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

    validators = []
    for row in rows:
        v = dict(zip(columns, row))
        for key in v:
            if isinstance(v[key], (float,)):
                v[key] = round(v[key], 6)
        validators.append(v)

    return {"snapshot_id": snapshot_id, "total": len(validators), "validators": validators}

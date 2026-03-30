"""
QueryAgent Protocol — QuerySynapse definition.

This is the wire format for all validator ↔ miner communication.
Validators fill request fields and send to miners via dendrite.
Miners fill response fields and return via axon.
"""

import bittensor as bt
from typing import Optional, List


class QuerySynapse(bt.Synapse):
    """
    Synapse for QueryAgent task assignment and answer submission.

    Request fields (validator → miner):
        task_id: Unique task identifier (e.g. "QB-001")
        snapshot_id: Which frozen dataset to query (e.g. "bt_snapshot_2026_03_v1")
        question: Natural language analytics question
        constraints: Optional parameters (time_window, max_rows, k, netuid_filter)

    Response fields (miner → validator):
        sql: The SQL query the miner generated
        result_hash: SHA-256 hash of the deterministic query result
        result_preview: First N rows of the result (columns + rows)
        tables_used: Which tables the SQL references
        explanation: Short text explaining the query logic
    """

    # ── Request (validator fills before sending) ──
    task_id: str = ""
    snapshot_id: str = ""
    question: str = ""
    constraints: Optional[dict] = None

    # ── Response (miner fills before returning) ──
    sql: Optional[str] = None
    result_hash: Optional[str] = None
    result_preview: Optional[dict] = None
    tables_used: Optional[List[str]] = None
    explanation: Optional[str] = None

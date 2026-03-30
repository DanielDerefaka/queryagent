"""Tests for QuerySynapse protocol definition."""

from queryagent.protocol import QuerySynapse


def test_synapse_creation():
    """QuerySynapse can be created with request fields."""
    synapse = QuerySynapse(
        task_id="QB-001",
        snapshot_id="bt_snapshot_2026_03_v1",
        question="Total TAO staked?",
        constraints={"k": 10},
    )
    assert synapse.task_id == "QB-001"
    assert synapse.snapshot_id == "bt_snapshot_2026_03_v1"
    assert synapse.question == "Total TAO staked?"
    assert synapse.constraints == {"k": 10}


def test_synapse_response_fields_default_none():
    """Response fields should default to None."""
    synapse = QuerySynapse(task_id="QB-001")
    assert synapse.sql is None
    assert synapse.result_hash is None
    assert synapse.result_preview is None
    assert synapse.tables_used is None
    assert synapse.explanation is None


def test_synapse_fill_response():
    """Miner can fill response fields."""
    synapse = QuerySynapse(task_id="QB-001")
    synapse.sql = "SELECT SUM(stake) FROM stakes"
    synapse.result_hash = "sha256:abc123"
    synapse.result_preview = {"columns": ["total"], "rows": [[1000.0]]}
    synapse.tables_used = ["stakes"]
    synapse.explanation = "Sums all stakes."

    assert synapse.sql == "SELECT SUM(stake) FROM stakes"
    assert synapse.result_hash == "sha256:abc123"
    assert synapse.tables_used == ["stakes"]

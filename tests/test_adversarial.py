"""
Adversarial tests — SQL injection, sandbox escapes, malformed inputs,
gaming attempts, and edge cases that a malicious miner might try.
"""

import duckdb
import pytest

from queryagent.hashing import _canonicalize_value, hash_from_rows, hash_result
from queryagent.scoring import compute_score, normalize_weights, update_ema
from queryagent.snapshot import execute_sql_safe, load_snapshot
from neurons.miner import generate_sql

import torch


SNAPSHOT_ID = "bt_snapshot_test_v1"


@pytest.fixture(scope="module")
def conn():
    return load_snapshot(SNAPSHOT_ID, use_cache=False)


# ── SQL Injection & Sandbox Tests ──

class TestSQLSafety:
    def test_drop_table_blocked(self, conn):
        """DROP TABLE should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "DROP TABLE miners")

    def test_create_table_blocked(self, conn):
        """CREATE TABLE should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "CREATE TABLE evil (id INT)")

    def test_insert_blocked(self, conn):
        """INSERT should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "INSERT INTO miners VALUES (999, 999, 'evil', 0, 0, 0, 0, 0, 0, false, 0)")

    def test_update_blocked(self, conn):
        """UPDATE should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "UPDATE miners SET stake = 999999 WHERE uid = 0")

    def test_delete_blocked(self, conn):
        """DELETE should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "DELETE FROM miners WHERE uid = 0")

    def test_alter_blocked(self, conn):
        """ALTER TABLE should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "ALTER TABLE miners ADD COLUMN evil INT")

    def test_copy_blocked(self, conn):
        """COPY should be blocked (filesystem access)."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "COPY miners TO '/tmp/stolen.csv'")

    def test_export_blocked(self, conn):
        """EXPORT should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "EXPORT DATABASE '/tmp/stolen'")

    def test_multistatement_injection(self, conn):
        """Multi-statement injection (SELECT; DROP) should be blocked."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "SELECT 1; DROP TABLE miners")

    def test_case_insensitive_blocking(self, conn):
        """Blocking should work regardless of case."""
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "drop table miners")
        with pytest.raises(ValueError, match="Forbidden"):
            execute_sql_safe(conn, "Drop Table miners")

    def test_valid_select_allowed(self, conn):
        """Normal SELECT queries should work fine."""
        columns, rows, exec_ms = execute_sql_safe(conn, "SELECT COUNT(*) FROM miners")
        assert rows[0][0] > 0

    def test_select_with_subquery_allowed(self, conn):
        """Complex SELECT with subqueries should work."""
        sql = (
            "SELECT netuid, cnt FROM "
            "(SELECT netuid, COUNT(*) AS cnt FROM miners GROUP BY netuid) sub "
            "ORDER BY cnt DESC LIMIT 5"
        )
        columns, rows, exec_ms = execute_sql_safe(conn, sql)
        assert len(rows) > 0

    def test_cte_allowed(self, conn):
        """Common Table Expressions (WITH) should work."""
        sql = (
            "WITH ranked AS ("
            "  SELECT netuid, uid, stake, ROW_NUMBER() OVER (PARTITION BY netuid ORDER BY stake DESC) AS rn "
            "  FROM metagraph WHERE stake > 0"
            ") SELECT * FROM ranked WHERE rn <= 3"
        )
        columns, rows, exec_ms = execute_sql_safe(conn, sql)
        assert len(columns) == 4

    def test_window_functions_allowed(self, conn):
        """Window functions should work."""
        sql = (
            "SELECT netuid, uid, stake, "
            "SUM(stake) OVER (PARTITION BY netuid) AS total_stake "
            "FROM metagraph WHERE stake > 0 LIMIT 10"
        )
        columns, rows, exec_ms = execute_sql_safe(conn, sql)
        assert "total_stake" in columns

    def test_nonexistent_table_raises(self, conn):
        """Query on non-existent table should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="SQL execution failed"):
            execute_sql_safe(conn, "SELECT * FROM nonexistent_table")

    def test_syntax_error_raises(self, conn):
        """Malformed SQL should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="SQL execution failed"):
            execute_sql_safe(conn, "SELECTT * FROMM miners")

    def test_empty_sql_raises(self, conn):
        """Empty SQL should raise."""
        with pytest.raises(RuntimeError):
            execute_sql_safe(conn, "")


# ── Hashing Edge Cases ──

class TestHashingEdgeCases:
    def test_very_long_strings(self, conn):
        """Hashing should handle very long string values."""
        sql = "SELECT REPEAT('x', 10000) AS long_val"
        result = hash_result(conn, sql)
        assert result.startswith("sha256:")

    def test_unicode_values(self, conn):
        """Hashing should handle unicode correctly."""
        # DuckDB supports unicode in string literals
        sql = "SELECT 'émojis: 🎯🔥' AS unicode_val"
        result = hash_result(conn, sql)
        assert result.startswith("sha256:")

    def test_special_characters_in_values(self, conn):
        """Pipe and newline characters shouldn't break canonical format."""
        sql = "SELECT 'pipe|char' AS val1, 'new\nline' AS val2"
        result = hash_result(conn, sql)
        assert result.startswith("sha256:")

    def test_null_vs_string_null(self, conn):
        """NULL and the string 'NULL' should produce different hashes (sentinel-based)."""
        hash_null = hash_result(conn, "SELECT NULL AS val")
        hash_string = hash_result(conn, "SELECT 'NULL' AS val")
        assert hash_null != hash_string, "NULL and 'NULL' should hash differently via sentinel"

    def test_zero_vs_null(self, conn):
        """0 and NULL should produce different hashes."""
        hash_zero = hash_result(conn, "SELECT 0 AS val")
        hash_null = hash_result(conn, "SELECT NULL AS val")
        assert hash_zero != hash_null

    def test_float_precision_consistency(self):
        """Float canonicalization should be consistent at precision boundary."""
        assert _canonicalize_value(1.0000001) == _canonicalize_value(1.0000001)
        assert _canonicalize_value(1.0) == "1.000000"
        assert _canonicalize_value(0.1 + 0.2) == _canonicalize_value(0.30000000000000004)

    def test_boolean_canonicalization(self):
        """Booleans should be lowercase."""
        assert _canonicalize_value(True) == "true"
        assert _canonicalize_value(False) == "false"

    def test_empty_string_vs_null(self):
        """Empty string and NULL should canonicalize differently."""
        assert _canonicalize_value("") != _canonicalize_value(None)

    def test_integer_vs_float(self):
        """Integer 1 and float 1.0 should canonicalize differently (int stays as int)."""
        int_canon = _canonicalize_value(1)
        float_canon = _canonicalize_value(1.0)
        assert int_canon != float_canon, "int(1) and float(1.0) should differ in canonical form"

    def test_large_result_set_hashing(self, conn):
        """Hashing should work on full table scans."""
        result = hash_result(conn, "SELECT * FROM metagraph")
        assert result.startswith("sha256:")

    def test_hash_from_rows_matches_hash_result(self, conn):
        """hash_from_rows should produce same result as hash_result for same data."""
        sql = "SELECT netuid, uid, stake FROM metagraph ORDER BY netuid, uid LIMIT 50"
        h1 = hash_result(conn, sql)

        res = conn.execute(sql)
        columns = [desc[0] for desc in res.description]
        rows = res.fetchall()
        h2 = hash_from_rows(columns, rows)

        assert h1 == h2, "Both hash functions should produce identical results"

    def test_column_order_matters(self, conn):
        """Swapping column order should produce different hashes."""
        h1 = hash_result(conn, "SELECT netuid, uid FROM metagraph LIMIT 5")
        h2 = hash_result(conn, "SELECT uid, netuid FROM metagraph LIMIT 5")
        assert h1 != h2, "Column order should affect the hash"


# ── Scoring Edge Cases ──

class TestScoringEdgeCases:
    def test_negative_exec_time(self):
        """Negative execution time should be handled gracefully."""
        score = compute_score(hash_matches=True, exec_ms=-1, budget_ms=5000,
                              response_ms=100, latency_ms=30000)
        assert 0.75 <= score <= 1.0

    def test_zero_budget(self):
        """Zero budget should not cause division by zero."""
        score = compute_score(hash_matches=True, exec_ms=100, budget_ms=0,
                              response_ms=100, latency_ms=30000)
        assert 0.0 <= score <= 1.0

    def test_zero_latency_budget(self):
        """Zero latency budget should not cause division by zero."""
        score = compute_score(hash_matches=True, exec_ms=100, budget_ms=5000,
                              response_ms=100, latency_ms=0)
        assert 0.0 <= score <= 1.0

    def test_very_fast_execution(self):
        """Sub-microsecond execution should score near 1.0."""
        score = compute_score(hash_matches=True, exec_ms=0.001, budget_ms=5000,
                              response_ms=1, latency_ms=30000)
        assert score > 0.99

    def test_execution_over_budget(self):
        """Execution exceeding budget should score 0.75 (correctness only)."""
        score = compute_score(hash_matches=True, exec_ms=10000, budget_ms=5000,
                              response_ms=60000, latency_ms=30000)
        assert score == pytest.approx(0.75)

    def test_weights_with_single_miner(self):
        """Single miner should get weight 1.0."""
        scores = torch.tensor([0.8])
        weights = normalize_weights(scores)
        assert weights[0] == pytest.approx(1.0)

    def test_weights_with_256_miners(self):
        """Should handle 256 miners (typical subnet size)."""
        scores = torch.rand(256)
        weights = normalize_weights(scores)
        assert weights.sum() == pytest.approx(1.0, abs=1e-5)
        assert (weights >= 0).all()

    def test_ema_with_256_miners(self):
        """EMA should work with large miner pools."""
        scores = torch.rand(256)
        new_scores = [random.random() for _ in range(256)]
        updated = update_ema(scores, new_scores, alpha=0.1)
        assert len(updated) == 256
        assert (updated >= 0).all()

    def test_ema_preserves_zeros(self):
        """Miners with no responses should decay toward zero."""
        scores = torch.tensor([1.0, 0.0, 0.5])
        new_scores = [0.0, 0.0, 0.0]
        updated = update_ema(scores, new_scores, alpha=0.1)
        assert updated[0] < 1.0  # Decayed
        assert updated[1] == 0.0  # Stayed zero
        assert updated[2] < 0.5  # Decayed

    def test_scoring_weights_sum(self):
        """Correctness + efficiency + latency weights should sum to 1.0."""
        from queryagent.config import CORRECTNESS_WEIGHT, EFFICIENCY_WEIGHT, LATENCY_WEIGHT
        assert CORRECTNESS_WEIGHT + EFFICIENCY_WEIGHT + LATENCY_WEIGHT == pytest.approx(1.0)


# ── Miner SQL Generation Edge Cases ──

class TestMinerEdgeCases:
    def test_empty_question(self):
        """Empty question should return None (no match)."""
        assert generate_sql("") is None

    def test_random_garbage_question(self):
        """Random text should not match any template."""
        assert generate_sql("asdfghjkl zxcvbnm") is None
        assert generate_sql("12345 !@#$%") is None

    def test_question_case_insensitive(self):
        """Template matching should be case-insensitive."""
        result_lower = generate_sql("what is the total tao staked across all subnets?")
        result_upper = generate_sql("WHAT IS THE TOTAL TAO STAKED ACROSS ALL SUBNETS?")
        assert result_lower is not None
        assert result_upper is not None
        assert result_lower["sql"] == result_upper["sql"]

    def test_k_parameter_injection(self):
        """Top-k questions should respect the k value."""
        result = generate_sql("Top 5 validators by stake", {"k": 5})
        assert result is not None
        assert "LIMIT 5" in result["sql"]

    def test_k_from_question(self):
        """k value should be extracted from question text."""
        result = generate_sql("Top 20 validators by stake")
        assert result is not None
        assert "LIMIT 20" in result["sql"]

    def test_netuid_from_question(self):
        """netuid should be extracted from question text."""
        result = generate_sql("How many active miners are on subnet 3?")
        assert result is not None
        assert "netuid = 3" in result["sql"]

    def test_all_templates_produce_valid_sql(self, conn):
        """Every SQL template should produce executable SQL."""
        from neurons.miner import SQL_TEMPLATES
        for template in SQL_TEMPLATES:
            sql = template["sql"]
            # Replace placeholders with defaults
            sql = sql.replace("{k}", "10").replace("{netuid}", "1")
            try:
                execute_sql_safe(conn, sql)
            except RuntimeError as e:
                pytest.fail(f"Template SQL failed: {sql[:60]}... — {e}")

    def test_sql_output_has_required_fields(self):
        """generate_sql should return sql, tables, and explanation."""
        result = generate_sql("How many active subnets are there?")
        assert result is not None
        assert "sql" in result
        assert "tables" in result
        assert "explanation" in result
        assert isinstance(result["tables"], list)
        assert len(result["tables"]) > 0


# ── Snapshot Integrity Tests ──

class TestSnapshotIntegrity:
    def test_all_expected_tables_exist(self, conn):
        """Snapshot should contain all expected tables."""
        from queryagent.config import EXPECTED_TABLES
        for table in EXPECTED_TABLES:
            result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            assert result[0] >= 0, f"Table {table} should exist"

    def test_metagraph_has_rows(self, conn):
        """Metagraph should have data from testnet."""
        count = conn.execute("SELECT COUNT(*) FROM metagraph").fetchone()[0]
        assert count > 100, f"Metagraph should have >100 rows, got {count}"

    def test_subnets_have_valid_netuids(self, conn):
        """Subnet netuids should be non-negative integers."""
        rows = conn.execute("SELECT netuid FROM subnets").fetchall()
        for row in rows:
            assert row[0] >= 0, f"netuid should be >= 0, got {row[0]}"

    def test_stakes_are_non_negative(self, conn):
        """All stake values should be non-negative."""
        result = conn.execute("SELECT MIN(stake) FROM stakes").fetchone()
        assert result[0] >= 0, "Stakes should be non-negative"

    def test_emissions_are_non_negative(self, conn):
        """All emission values should be non-negative."""
        result = conn.execute("SELECT MIN(emission) FROM emissions").fetchone()
        assert result[0] >= 0, "Emissions should be non-negative"

    def test_hotkeys_are_valid_format(self, conn):
        """Hotkeys should be valid ss58 format (start with 5)."""
        rows = conn.execute(
            "SELECT DISTINCT hotkey FROM metagraph WHERE hotkey != '' LIMIT 10"
        ).fetchall()
        for row in rows:
            assert row[0].startswith("5"), f"Hotkey should start with 5: {row[0][:10]}"
            assert len(row[0]) == 48, f"Hotkey should be 48 chars: {len(row[0])}"

    def test_cross_table_consistency(self, conn):
        """Miners + validators should equal metagraph count per subnet."""
        result = conn.execute("""
            SELECT m.netuid, m.total,
                   COALESCE(v.cnt, 0) + COALESCE(mi.cnt, 0) AS split_total
            FROM (SELECT netuid, COUNT(*) AS total FROM metagraph GROUP BY netuid) m
            LEFT JOIN (SELECT netuid, COUNT(*) AS cnt FROM validators GROUP BY netuid) v
                ON m.netuid = v.netuid
            LEFT JOIN (SELECT netuid, COUNT(*) AS cnt FROM miners GROUP BY netuid) mi
                ON m.netuid = mi.netuid
        """).fetchall()
        for row in result:
            netuid, total, split_total = row
            assert total == split_total, (
                f"Subnet {netuid}: metagraph({total}) != validators+miners({split_total})"
            )

    def test_schema_json_exists(self):
        """Snapshot should have schema.json."""
        from queryagent.config import SNAPSHOT_DIR
        schema_path = SNAPSHOT_DIR / SNAPSHOT_ID / "schema.json"
        assert schema_path.exists(), f"schema.json missing at {schema_path}"
        with open(schema_path) as f:
            schema = json.load(f)
        assert "tables" in schema
        assert len(schema["tables"]) > 0

    def test_metadata_json_exists(self):
        """Snapshot should have metadata.json with block number."""
        import json
        from queryagent.config import SNAPSHOT_DIR
        metadata_path = SNAPSHOT_DIR / SNAPSHOT_ID / "metadata.json"
        assert metadata_path.exists()
        with open(metadata_path) as f:
            metadata = json.load(f)
        assert "block_number" in metadata
        assert metadata["block_number"] > 0
        assert "network" in metadata


# ── Validator Re-execution Tests ──

class TestValidatorReexecution:
    def test_reexecute_correct_sql(self, conn):
        """Validator re-execution of correct SQL should match ground truth."""
        from neurons.validator import reexecute_miner_sql
        import json
        from queryagent.config import GROUND_TRUTH_DIR

        gt_files = list(GROUND_TRUTH_DIR.glob("*.json"))
        assert len(gt_files) > 0

        for gt_file in gt_files[:5]:  # Test first 5
            with open(gt_file) as f:
                gt = json.load(f)

            result = reexecute_miner_sql(conn, gt["reference_sql"], gt["budget_ms"])
            assert result is not None, f"Re-execution should succeed for {gt['task_id']}"

            validator_hash, exec_ms = result
            assert validator_hash == gt["ground_truth_hash"], (
                f"Hash mismatch for {gt['task_id']}: "
                f"got {validator_hash[:30]} expected {gt['ground_truth_hash'][:30]}"
            )
            assert exec_ms >= 0

    def test_reexecute_bad_sql_returns_none(self, conn):
        """Invalid SQL should return None (not crash)."""
        from neurons.validator import reexecute_miner_sql
        result = reexecute_miner_sql(conn, "SELECTT WRONG SYNTAX", 5000)
        assert result is None

    def test_reexecute_write_sql_returns_none(self, conn):
        """Write SQL should return None (blocked by safety)."""
        from neurons.validator import reexecute_miner_sql
        result = reexecute_miner_sql(conn, "DROP TABLE miners", 5000)
        assert result is None

    def test_reexecute_empty_result(self, conn):
        """Query returning 0 rows should still produce a hash."""
        from neurons.validator import reexecute_miner_sql
        result = reexecute_miner_sql(conn, "SELECT * FROM miners WHERE uid = -999", 5000)
        assert result is not None
        validator_hash, exec_ms = result
        assert validator_hash.startswith("sha256:")


import json
import random

# Running Environment — QueryAgent

Evidence that QueryAgent runs successfully with all dependencies, modules, and tests passing.

---

## System Info

```
Platform: macOS Darwin 25.4.0
Python:   3.9.6
```

## Installed Dependencies

```
bittensor    9.12.2    Subnet framework (axon, dendrite, metagraph, wallets)
duckdb       1.4.4     In-memory SQL engine for query execution
pyarrow      21.0.0    Parquet file I/O for snapshot loading
pandas       2.3.3     DataFrame operations for snapshot building
torch        2.7.1     Tensor operations for EMA scoring
numpy        2.0.2     Numerical operations
pydantic     2.15.2    Data validation
structlog    25.4.0    Structured logging
```

## Module Import Verification

All 7 core modules import successfully:

```
=== All QueryAgent modules imported successfully ===
Scoring weights: correctness=0.75, efficiency=0.15, latency=0.1
EMA alpha: 0.1
```

## Snapshot Loaded

```
Snapshot loaded: 6 tables
  emissions:  24 rows
  metagraph:  1115 rows
  miners:     1106 rows
  stakes:     490 rows
  subnets:    10 rows
  validators: 9 rows
```

## Task Pool Loaded

```
Task pool: 16 public, 4 hidden
Ground truth entries: 20
```

## Hash Determinism Verified

```
Hash determinism test: 100 runs -> 1 unique hash(es)
```

Same SQL, same snapshot, 100 executions = identical SHA-256 hash every time.

## Test Suite Results — 122 passed, 2 skipped

```
tests/test_adversarial.py::TestSQLSafety::test_drop_table_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_create_table_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_insert_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_update_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_delete_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_alter_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_copy_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_export_blocked PASSED
tests/test_adversarial.py::TestSQLSafety::test_multistatement_injection PASSED
tests/test_adversarial.py::TestSQLSafety::test_case_insensitive_blocking PASSED
tests/test_adversarial.py::TestSQLSafety::test_valid_select_allowed PASSED
tests/test_adversarial.py::TestSQLSafety::test_select_with_subquery_allowed PASSED
tests/test_adversarial.py::TestSQLSafety::test_cte_allowed PASSED
tests/test_adversarial.py::TestSQLSafety::test_window_functions_allowed PASSED
tests/test_adversarial.py::TestSQLSafety::test_nonexistent_table_raises PASSED
tests/test_adversarial.py::TestSQLSafety::test_syntax_error_raises PASSED
tests/test_adversarial.py::TestSQLSafety::test_empty_sql_raises PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_very_long_strings PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_unicode_values PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_special_characters_in_values PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_null_vs_string_null PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_zero_vs_null PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_float_precision_consistency PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_boolean_canonicalization PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_empty_string_vs_null PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_integer_vs_float PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_large_result_set_hashing PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_hash_from_rows_matches_hash_result PASSED
tests/test_adversarial.py::TestHashingEdgeCases::test_column_order_matters PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_negative_exec_time PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_zero_budget PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_zero_latency_budget PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_very_fast_execution PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_execution_over_budget PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_weights_with_single_miner PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_weights_with_256_miners PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_ema_with_256_miners PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_ema_preserves_zeros PASSED
tests/test_adversarial.py::TestScoringEdgeCases::test_scoring_weights_sum PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_empty_question PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_random_garbage_question PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_question_case_insensitive PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_k_parameter_injection PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_k_from_question PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_netuid_from_question PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_all_templates_produce_valid_sql PASSED
tests/test_adversarial.py::TestMinerEdgeCases::test_sql_output_has_required_fields PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_all_expected_tables_exist PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_metagraph_has_rows PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_subnets_have_valid_netuids PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_stakes_are_non_negative PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_emissions_are_non_negative PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_hotkeys_are_valid_format PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_cross_table_consistency PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_schema_json_exists PASSED
tests/test_adversarial.py::TestSnapshotIntegrity::test_metadata_json_exists PASSED
tests/test_adversarial.py::TestValidatorReexecution::test_reexecute_correct_sql PASSED
tests/test_adversarial.py::TestValidatorReexecution::test_reexecute_bad_sql_returns_none PASSED
tests/test_adversarial.py::TestValidatorReexecution::test_reexecute_write_sql_returns_none PASSED
tests/test_adversarial.py::TestValidatorReexecution::test_reexecute_empty_result PASSED
tests/test_determinism.py::test_same_query_100_times PASSED
tests/test_determinism.py::test_determinism_across_connections PASSED
tests/test_determinism.py::test_determinism_with_concurrent_execution PASSED
tests/test_determinism.py::test_every_task_reference_sql_is_deterministic PASSED
tests/test_determinism.py::test_hash_result_vs_hash_from_rows_all_tasks PASSED
tests/test_determinism.py::test_row_order_independence_complex PASSED
tests/test_determinism.py::test_float_precision_edge_case PASSED
tests/test_determinism.py::test_aggregation_determinism PASSED
tests/test_determinism.py::test_join_determinism PASSED
tests/test_determinism.py::test_window_function_determinism PASSED
tests/test_determinism.py::test_empty_result_is_deterministic PASSED
tests/test_e2e.py::test_snapshot_loads PASSED
tests/test_e2e.py::test_miner_generates_sql_for_easy_tasks PASSED
tests/test_e2e.py::test_miner_generates_sql_for_medium_tasks PASSED
tests/test_e2e.py::test_full_scoring_loop PASSED
tests/test_e2e.py::test_wrong_answer_scores_zero PASSED
tests/test_hashing.py::test_same_query_same_hash PASSED
tests/test_hashing.py::test_different_query_different_hash PASSED
tests/test_hashing.py::test_hash_format PASSED
tests/test_hashing.py::test_row_order_independent PASSED
tests/test_hashing.py::test_null_handling PASSED
tests/test_hashing.py::test_float_precision PASSED
tests/test_hashing.py::test_empty_result PASSED
tests/test_hashing.py::test_hash_from_rows PASSED
tests/test_llm_miner.py::test_llm_generates_sql SKIPPED (OPENAI_API_KEY not set)
tests/test_llm_miner.py::test_hybrid_vs_template_vs_llm SKIPPED (OPENAI_API_KEY not set)
tests/test_protocol.py::test_synapse_creation PASSED
tests/test_protocol.py::test_synapse_response_fields_default_none PASSED
tests/test_protocol.py::test_synapse_fill_response PASSED
tests/test_scoring.py::TestComputeScore::test_wrong_hash_is_zero PASSED
tests/test_scoring.py::TestComputeScore::test_perfect_score PASSED
tests/test_scoring.py::TestComputeScore::test_correct_but_slow PASSED
tests/test_scoring.py::TestComputeScore::test_correct_medium_speed PASSED
tests/test_scoring.py::TestComputeScore::test_score_never_exceeds_one PASSED
tests/test_scoring.py::TestComputeScore::test_score_range_for_correct PASSED
tests/test_scoring.py::TestEMA::test_ema_smoothing PASSED
tests/test_scoring.py::TestEMA::test_ema_converges PASSED
tests/test_scoring.py::TestEMA::test_ema_zero_input PASSED
tests/test_scoring.py::TestWeights::test_normalize_sums_to_one PASSED
tests/test_scoring.py::TestWeights::test_zero_scores PASSED
tests/test_scoring.py::TestWeights::test_relative_order PASSED
tests/test_snapshot.py::test_load_snapshot PASSED
tests/test_snapshot.py::test_query_snapshot PASSED
tests/test_snapshot.py::test_execute_sql_safe_blocks_writes PASSED
tests/test_snapshot.py::test_execute_sql_safe_returns_timing PASSED
tests/test_tasks.py::test_task_pool_loads PASSED
tests/test_tasks.py::test_all_tasks_have_ground_truth PASSED
tests/test_tasks.py::test_tasks_have_required_fields PASSED
tests/test_tasks.py::test_hidden_tasks_exist PASSED
tests/test_tasks.py::test_public_tasks_not_hidden PASSED
tests/test_tasks.py::test_tier_distribution PASSED
tests/test_tasks.py::test_sample_task_returns_valid_task PASSED
tests/test_tasks.py::test_sample_task_injects_parameters PASSED
tests/test_tasks.py::test_sample_distribution_across_tiers PASSED
tests/test_tasks.py::test_hidden_task_sampling_rate PASSED
tests/test_tasks.py::test_parameter_injection_varies PASSED
tests/test_tasks.py::test_parameter_set_defaults PASSED
tests/test_tasks.py::test_ground_truth_hashes_are_unique PASSED
tests/test_tasks.py::test_task_pool_with_empty_dir PASSED
tests/test_tasks.py::test_task_pool_with_partial_data PASSED
tests/test_wire.py::test_axon_starts PASSED
tests/test_wire.py::test_dendrite_sends_synapse PASSED
tests/test_wire.py::test_full_wire_loop PASSED
tests/test_wire.py::test_multiple_tasks_over_wire PASSED

======================== 122 passed, 2 skipped in 6.33s ========================
```

The 2 skipped tests (`test_llm_miner.py`) require an `OPENAI_API_KEY` environment variable.
All other 122 tests pass, covering:

| Test File | Count | Coverage |
|-----------|-------|----------|
| test_adversarial.py | 60 | SQL injection, hash edge cases, scoring edge cases, snapshot integrity |
| test_determinism.py | 11 | Same query 100x, concurrent threads, joins, window functions |
| test_e2e.py | 5 | Full miner-to-validator loop |
| test_hashing.py | 8 | Determinism, NULL handling, float precision |
| test_scoring.py | 12 | Score formula, EMA convergence, weight normalization |
| test_snapshot.py | 4 | Parquet loading, SQL sandboxing |
| test_tasks.py | 15 | Task loading, sampling, distribution, parameter injection |
| test_wire.py | 4 | Real axon-to-dendrite communication |
| test_protocol.py | 3 | Synapse creation and serialization |
| test_llm_miner.py | 2 | LLM strategies (skipped without API key) |

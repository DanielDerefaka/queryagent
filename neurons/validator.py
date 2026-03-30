"""
QueryAgent Validator — sends tasks, re-executes SQL, scores miners, sets weights.

The validator:
1. Samples a task from the pool (public + hidden, weighted by difficulty)
2. Builds a QuerySynapse and broadcasts to all miners via dendrite
3. Collects responses within timeout
4. Re-executes each miner's SQL on its own DuckDB (timed)
5. Compares result hash to ground truth
6. Computes scores (75/15/10 formula), applies EMA
7. Calls set_weights() on-chain

Usage:
    python -m neurons.validator --netuid <NETUID> --wallet.name <NAME> --wallet.hotkey <HOTKEY> --subtensor.network test
"""

import argparse
import asyncio
import logging
import time
import traceback

import torch
import bittensor as bt

from queryagent.config import (
    DEFAULT_TIMEOUT_S,
    EMA_ALPHA,
    METAGRAPH_SYNC_INTERVAL_S,
    WEIGHTS_RATE_LIMIT_BLOCKS,
)
from queryagent.hashing import hash_result
from queryagent.protocol import QuerySynapse
from queryagent.scoring import normalize_weights, score_responses, update_ema
from queryagent.snapshot import execute_sql_safe, load_snapshot
from queryagent.tasks import TaskPool
from queryagent.training import save_round_training_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def reexecute_miner_sql(conn, sql: str, budget_ms: float):
    """
    Re-execute a miner's SQL on the validator's DuckDB. Returns (hash, exec_ms) or None.
    """
    try:
        columns, rows, exec_ms = execute_sql_safe(conn, sql, timeout_ms=budget_ms)
        from queryagent.hashing import hash_from_rows
        result_hash = hash_from_rows(columns, rows)
        return result_hash, exec_ms
    except Exception as e:
        logger.debug(f"Re-execution failed: {e}")
        return None


def run_validation_round(
    dendrite: bt.Dendrite,
    metagraph,
    task_pool: TaskPool,
    conn,
    scores: torch.Tensor,
) -> torch.Tensor:
    """
    Run a single validation round:
    1. Sample task
    2. Query miners
    3. Re-execute and score
    4. Update EMA
    """
    # 1. Sample a task
    task = task_pool.sample_task()
    gt = task_pool.get_ground_truth(task.task_id)

    if not gt or not gt.get("ground_truth_hash"):
        logger.warning(f"No ground truth for {task.task_id}, skipping round")
        return scores

    ground_truth_hash = gt["ground_truth_hash"]

    logger.info(
        f"Round: task={task.task_id} tier={task.tier} "
        f"hidden={task.is_hidden} question={task.question[:60]}..."
    )

    # 2. Build synapse and query all miners
    synapse = QuerySynapse(
        task_id=task.task_id,
        snapshot_id=task.snapshot_id,
        question=task.question,
        constraints=task.constraints,
    )

    start_time = time.perf_counter()

    responses = asyncio.get_event_loop().run_until_complete(
        dendrite(
            axons=metagraph.axons,
            synapse=synapse,
            timeout=DEFAULT_TIMEOUT_S,
        )
    )

    # Ensure responses is a list
    if not isinstance(responses, list):
        responses = [responses]

    total_time_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"Received {len(responses)} responses in {total_time_ms:.0f}ms")

    # 3. Re-execute each miner's SQL and compute scores
    exec_results = []
    response_times_ms = []

    for i, response in enumerate(responses):
        if response is None or response.sql is None:
            exec_results.append(None)
            response_times_ms.append(DEFAULT_TIMEOUT_S * 1000)
            continue

        # Compute response time from dendrite timing
        resp_time = getattr(response.dendrite, "process_time", None)
        response_times_ms.append(
            (resp_time * 1000) if resp_time else (DEFAULT_TIMEOUT_S * 1000)
        )

        # Re-execute miner's SQL on validator's DuckDB
        result = reexecute_miner_sql(conn, response.sql, task.budget_ms)
        exec_results.append(result)

    # 4. Compute scores
    round_scores = score_responses(
        responses=responses,
        ground_truth_hash=ground_truth_hash,
        exec_results=exec_results,
        budget_ms=task.budget_ms,
        latency_ms=task.latency_ms,
        response_times_ms=response_times_ms,
    )

    # 5. Save training data (Layer 2 pipeline)
    try:
        save_round_training_data(
            task=task,
            ground_truth_hash=ground_truth_hash,
            responses=responses,
            round_scores=round_scores,
            exec_results=exec_results,
            response_times_ms=response_times_ms,
            block=getattr(dendrite, "_current_block", None),
        )
    except Exception as e:
        logger.warning(f"Training data save failed (non-fatal): {e}")

    # 6. Update EMA
    scores = update_ema(scores, round_scores)

    # Log round results
    nonzero = sum(1 for s in round_scores if s > 0)
    max_score = max(round_scores) if round_scores else 0
    for i, s in enumerate(round_scores):
        if s > 0:
            logger.info(f"  UID {i}: score={s:.4f} hash_match=True")
    logger.info(
        f"Scored: {nonzero}/{len(round_scores)} miners correct, "
        f"max_score={max_score:.3f}"
    )

    return scores


def main():
    parser = argparse.ArgumentParser(description="QueryAgent Validator")
    parser.add_argument("--netuid", type=int, required=True, help="Subnet network ID")
    bt.Wallet.add_args(parser)
    bt.Subtensor.add_args(parser)

    config = bt.Config(parser)
    wallet = bt.Wallet(config=config)
    subtensor = bt.Subtensor(config=config)
    metagraph = bt.Metagraph(netuid=config.netuid, network=config.subtensor.network, sync=True)
    dendrite = bt.Dendrite(wallet=wallet)

    logger.info(f"Wallet: {wallet}")
    logger.info(f"Metagraph: {metagraph.n} neurons on subnet {config.netuid}")

    # Load task pool
    task_pool = TaskPool()
    task_pool.load()
    logger.info(
        f"Task pool: {len(task_pool.public_tasks)} public, "
        f"{len(task_pool.hidden_tasks)} hidden"
    )

    # Load snapshot (use first task's snapshot_id)
    first_task = task_pool.all_tasks[0] if task_pool.all_tasks else None
    if not first_task:
        logger.error("No tasks loaded. Run generate_tasks.py first.")
        return

    snapshot_id = first_task.snapshot_id
    logger.info(f"Loading snapshot: {snapshot_id}")
    conn = load_snapshot(snapshot_id)

    # Initialize EMA scores
    scores = torch.zeros(metagraph.n)

    # Track weight-setting
    last_weights_block = 0
    last_sync_time = 0

    logger.info("Validator started. Entering main loop...")

    try:
        while True:
            current_block = subtensor.block

            # Sync metagraph periodically
            if time.time() - last_sync_time > METAGRAPH_SYNC_INTERVAL_S:
                try:
                    metagraph = bt.Metagraph(netuid=config.netuid, network=config.subtensor.network, sync=True)
                except Exception as e:
                    logger.warning(f"Metagraph sync failed (fast-blocks pruning): {e}")
                last_sync_time = time.time()

                # Resize scores if metagraph changed
                if len(scores) != metagraph.n:
                    new_scores = torch.zeros(metagraph.n)
                    copy_len = min(len(scores), metagraph.n)
                    new_scores[:copy_len] = scores[:copy_len]
                    scores = new_scores
                    logger.info(f"Resized scores to {metagraph.n}")

            # Run a validation round
            try:
                scores = run_validation_round(
                    dendrite=dendrite,
                    metagraph=metagraph,
                    task_pool=task_pool,
                    conn=conn,
                    scores=scores,
                )
            except Exception as e:
                logger.error(f"Validation round failed: {e}")
                logger.debug(traceback.format_exc())

            # Set weights (rate-limited)
            blocks_since_last = current_block - last_weights_block
            if blocks_since_last >= WEIGHTS_RATE_LIMIT_BLOCKS:
                weights = normalize_weights(scores)

                if weights.sum() > 0:
                    try:
                        uids = list(range(metagraph.n))
                        logger.info(f"Setting weights: UIDs={uids}, scores={scores.tolist()}, weights={weights.tolist()}")
                        subtensor.set_weights(
                            wallet=wallet,
                            netuid=config.netuid,
                            uids=uids,
                            weights=weights.tolist(),
                            wait_for_inclusion=False,
                        )
                        last_weights_block = current_block
                        logger.info(
                            f"Weights set at block {current_block} "
                            f"({(weights > 0).sum()} non-zero weights)"
                        )
                    except Exception as e:
                        logger.error(f"Failed to set weights: {e}")
                else:
                    logger.info("All weights zero — skipping set_weights")

            # Sleep until next block
            time.sleep(12)

    except KeyboardInterrupt:
        logger.info("Validator shutting down...")


if __name__ == "__main__":
    main()

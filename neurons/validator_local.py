"""
QueryAgent Validator — Local chain compatible version.
Uses direct substrate queries instead of bt.Metagraph (which requires NeuronInfoRuntimeApi).
"""
import argparse
import time
import traceback
import torch
import structlog

import bittensor as bt
from substrateinterface import SubstrateInterface

from queryagent.protocol import QuerySynapse
from queryagent.snapshot import load_snapshot, execute_sql_safe
from queryagent.hashing import hash_result
from queryagent.scoring import score_responses, update_ema, normalize_weights
from queryagent.tasks import TaskPool
from queryagent.training import save_round_training_data
from queryagent.config import (
    WEIGHTS_RATE_LIMIT_BLOCKS,
    VALIDATION_INTERVAL_S,
    DEFAULT_TIMEOUT_S,
)

logger = structlog.get_logger()


def get_neuron_count(substrate, netuid):
    """Get number of neurons on subnet via substrate query."""
    result = substrate.query("SubtensorModule", "SubnetworkN", [netuid])
    return result.value


def get_hotkeys(substrate, netuid, n):
    """Get all hotkeys for a subnet."""
    hotkeys = []
    for uid in range(n):
        result = substrate.query("SubtensorModule", "Keys", [netuid, uid])
        hotkeys.append(result.value)
    return hotkeys


def run_validation_round(dendrite, substrate, netuid, task_pool, conn, scores, wallet):
    """Execute one full validation round."""
    n = get_neuron_count(substrate, netuid)
    hotkeys = get_hotkeys(substrate, netuid, n)

    # Sample a task
    task = task_pool.sample_task()
    gt_data = task_pool.get_ground_truth(task.task_id)
    ground_truth_hash = gt_data.get("ground_truth_hash", "") if gt_data else ""

    logger.info(
        f"=== Validation Round ===\n"
        f"  Task: {task.task_id} ({task.tier})\n"
        f"  Question: {task.question}\n"
        f"  Ground truth: {ground_truth_hash[:30]}...\n"
        f"  Querying {n} neurons"
    )

    # Build synapse
    synapse = QuerySynapse(
        task_id=task.task_id,
        snapshot_id=task.snapshot_id,
        question=task.question,
        constraints=task.constraints or {},
    )

    # Build axon list — miners are on local ports 8091-8100 (uid 3-12)
    # Validators are uid 0-2 (no axon), miners are uid 3-12
    valid_uids = []
    valid_axons = []
    for uid in range(n):
        # Miners registered after validators, so miners are UIDs 3-12, ports 8091-8100
        miner_index = uid - 3  # 0-based miner index
        if 0 <= miner_index < 10:
            port = 8091 + miner_index
            axon = bt.AxonInfo(
                version=0,
                ip="127.0.0.1",
                port=port,
                ip_type=4,
                hotkey=hotkeys[uid],
                coldkey="",
            )
            valid_uids.append(uid)
            valid_axons.append(axon)

    if not valid_axons:
        logger.warning("No neurons with valid axons found")
        return scores

    logger.info(f"Querying {len(valid_axons)} neurons with valid axons")

    # Send queries
    start_time = time.time()
    try:
        responses = dendrite.query(
            axons=valid_axons,
            synapse=synapse,
            timeout=DEFAULT_TIMEOUT_S,
        )
    except Exception as e:
        logger.error(f"Dendrite query failed: {e}")
        return scores
    total_time_ms = (time.time() - start_time) * 1000
    logger.info(f"Dendrite returned {len(responses)} responses in {total_time_ms:.0f}ms")

    # Score responses
    round_scores = torch.zeros(n)
    exec_results = {}
    response_times_ms = {}

    for i, uid in enumerate(valid_uids):
        response = responses[i]
        resp_time = total_time_ms / len(valid_axons)  # approximate per-miner

        if response is None or not getattr(response, 'sql', None):
            status = getattr(getattr(response, 'dendrite', None), 'status_code', 'unknown')
            logger.info(f"  UID {uid}: No response (status={status})")
            round_scores[uid] = 0.0
            continue

        # Re-execute miner's SQL on validator's DuckDB
        try:
            _, _, exec_ms = execute_sql_safe(conn, response.sql)
            miner_hash = hash_result(conn, response.sql)
        except Exception as e:
            logger.warning(f"  UID {uid}: SQL execution failed: {e}")
            round_scores[uid] = 0.0
            continue

        # Compare hashes
        hash_match = (miner_hash == ground_truth_hash)
        exec_results[uid] = {"exec_ms": exec_ms, "hash": miner_hash, "match": hash_match}
        response_times_ms[uid] = resp_time

        if not hash_match:
            round_scores[uid] = 0.0
            logger.info(f"  UID {uid}: HASH MISMATCH (got {miner_hash[:20]}... expected {ground_truth_hash[:20]}...)")
        else:
            # Score: 75% correctness (passed) + 15% efficiency + 10% latency
            budget_ms = task.budget_ms or 5000
            latency_budget = 30000
            efficiency = max(0.0, 1.0 - exec_ms / budget_ms)
            latency = max(0.0, 1.0 - resp_time / latency_budget)
            score = 0.75 + 0.15 * efficiency + 0.10 * latency
            round_scores[uid] = min(score, 1.0)
            logger.info(
                f"  UID {uid}: CORRECT | score={round_scores[uid]:.4f} | "
                f"exec={exec_ms:.1f}ms | hash={miner_hash[:20]}..."
            )

    # Save training data
    try:
        save_round_training_data(
            task=task,
            ground_truth_hash=ground_truth_hash,
            responses=responses,
            round_scores=round_scores,
            exec_results=exec_results,
            response_times_ms=response_times_ms,
            block=None,
        )
    except Exception as e:
        logger.warning(f"Training data save failed (non-fatal): {e}")

    # EMA update
    scores = update_ema(scores, round_scores)
    logger.info(f"EMA scores: {scores.tolist()}")

    return scores


def main():
    parser = argparse.ArgumentParser(description="QueryAgent Validator (Local)")
    parser.add_argument("--netuid", type=int, required=True)
    parser.add_argument("--wallet.name", type=str, required=True)
    parser.add_argument("--wallet.hotkey", type=str, default="default")
    parser.add_argument("--subtensor.network", type=str, default="ws://127.0.0.1:9944")
    args = parser.parse_args()

    wallet = bt.Wallet(name=args.__dict__["wallet.name"], hotkey=args.__dict__["wallet.hotkey"])
    subtensor = bt.Subtensor(network=args.__dict__["subtensor.network"])
    substrate = SubstrateInterface(url=args.__dict__["subtensor.network"])
    dendrite = bt.Dendrite(wallet=wallet)

    logger.info(f"Validator: {wallet.name} | Hotkey: {wallet.hotkey.ss58_address}")
    logger.info(f"Chain block: {subtensor.block}")

    # Load task pool
    task_pool = TaskPool()
    task_pool.load()
    logger.info(f"Tasks: {len(task_pool.public_tasks)} public, {len(task_pool.hidden_tasks)} hidden")

    # Load snapshot
    first_task = task_pool.all_tasks[0]
    snapshot_id = first_task.snapshot_id
    conn = load_snapshot(snapshot_id)
    logger.info(f"Snapshot loaded: {snapshot_id}")

    # Init scores
    n = get_neuron_count(substrate, args.netuid)
    scores = torch.zeros(n)
    last_weights_block = 0

    logger.info(f"Validator started. {n} neurons on netuid {args.netuid}. Entering main loop...")

    try:
        while True:
            current_block = subtensor.block

            # Run validation round
            try:
                n_new = get_neuron_count(substrate, args.netuid)
                if n_new != len(scores):
                    new_scores = torch.zeros(n_new)
                    copy_len = min(len(scores), n_new)
                    new_scores[:copy_len] = scores[:copy_len]
                    scores = new_scores
                    logger.info(f"Resized scores: {len(scores)}")

                scores = run_validation_round(
                    dendrite=dendrite,
                    substrate=substrate,
                    netuid=args.netuid,
                    task_pool=task_pool,
                    conn=conn,
                    scores=scores,
                    wallet=wallet,
                )
            except Exception as e:
                logger.error(f"Validation round failed: {e}")
                logger.debug(traceback.format_exc())

            # Set weights (rate-limited)
            blocks_since = current_block - last_weights_block
            if blocks_since >= WEIGHTS_RATE_LIMIT_BLOCKS or last_weights_block == 0:
                weights = normalize_weights(scores)
                if weights.sum() > 0:
                    try:
                        uids = list(range(len(scores)))
                        logger.info(
                            f">>> SET_WEIGHTS at block {current_block} <<<\n"
                            f"  UIDs: {uids}\n"
                            f"  Scores: {[f'{s:.4f}' for s in scores.tolist()]}\n"
                            f"  Weights: {[f'{w:.4f}' for w in weights.tolist()]}"
                        )
                        # Direct substrate call — bypasses CommitRevealWeights check
                        # Convert weights to u16 (0-65535 range)
                        max_w = max(weights.tolist()) if max(weights.tolist()) > 0 else 1.0
                        w_u16 = [int((w / max_w) * 65535) for w in weights.tolist()]
                        call = substrate.compose_call(
                            call_module="SubtensorModule",
                            call_function="set_weights",
                            call_params={
                                "netuid": args.netuid,
                                "dests": uids,
                                "weights": w_u16,
                                "version_key": 0,
                            },
                        )
                        extrinsic = substrate.create_signed_extrinsic(
                            call=call, keypair=wallet.hotkey
                        )
                        result = substrate.submit_extrinsic(
                            extrinsic, wait_for_inclusion=True
                        )
                        last_weights_block = current_block
                        logger.info(f"Weights set successfully ({(weights > 0).sum()} non-zero) | extrinsic={result}")
                    except Exception as e:
                        logger.error(f"set_weights failed: {e}")
                else:
                    logger.info("All weights zero — skipping set_weights")

            time.sleep(VALIDATION_INTERVAL_S)

    except KeyboardInterrupt:
        logger.info("Validator shutting down...")


if __name__ == "__main__":
    main()

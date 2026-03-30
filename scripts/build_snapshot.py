"""
QueryAgent Snapshot Builder — indexes Bittensor chain data into Parquet.

Connects to a Bittensor subtensor node, pulls metagraph and chain state,
and exports a frozen, versioned Parquet snapshot bundle.

Usage:
    python scripts/build_snapshot.py --network finney --output benchmark/snapshots/bt_snapshot_2026_03_v1
    python scripts/build_snapshot.py --network test --output benchmark/snapshots/bt_snapshot_test_v1
"""

import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import bittensor as bt
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Max subnets to index (testnet has 443+, we don't need all)
MAX_SUBNETS = 50


def get_all_netuids(subtensor: bt.Subtensor, max_subnets: int = MAX_SUBNETS) -> list[int]:
    """Get all active subnet netuids."""
    try:
        netuids = subtensor.get_all_subnets_netuid()
        logger.info(f"Found {len(netuids)} subnets on chain")
        # Sort and limit
        netuids = sorted(netuids)[:max_subnets]
        logger.info(f"Indexing first {len(netuids)} subnets")
        return netuids
    except Exception as e:
        logger.error(f"Failed to get subnets: {e}")
        return []


def build_subnets_table(subtensor: bt.Subtensor, netuids: list[int]) -> pd.DataFrame:
    """Build the subnets table from chain data."""
    rows = []
    for netuid in netuids:
        try:
            hyperparams = subtensor.get_subnet_hyperparameters(netuid)
            if hyperparams is None:
                rows.append({"netuid": netuid})
                continue
            rows.append({
                "netuid": netuid,
                "tempo": getattr(hyperparams, "tempo", 360),
                "max_n": getattr(hyperparams, "max_n", 256),
                "immunity_period": getattr(hyperparams, "immunity_period", 4096),
                "min_difficulty": getattr(hyperparams, "min_difficulty", 0),
                "weights_rate_limit": getattr(hyperparams, "weights_rate_limit", 100),
            })
        except Exception as e:
            logger.warning(f"Failed to get hyperparams for subnet {netuid}: {e}")
            rows.append({"netuid": netuid})

    logger.info(f"Built subnets table: {len(rows)} rows")
    return pd.DataFrame(rows)


def build_metagraph_table(
    netuids: list[int], network: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Build validators, miners, and metagraph tables from chain metagraphs.

    Returns (validators_df, miners_df, metagraph_df)
    """
    validators_rows = []
    miners_rows = []
    metagraph_rows = []

    for netuid in netuids:
        try:
            meta = bt.Metagraph(netuid=netuid, network=network, sync=True)
        except Exception as e:
            logger.warning(f"Failed to get metagraph for subnet {netuid}: {e}")
            continue

        n = meta.n.item() if hasattr(meta.n, "item") else int(meta.n)

        def _safe_get(arr, idx, default=0.0):
            """Safely get value from numpy array or list."""
            try:
                if arr is not None and idx < len(arr):
                    return float(arr[idx])
            except Exception:
                pass
            return default

        for uid in range(n):
            try:
                row = {
                    "netuid": netuid,
                    "uid": uid,
                    "hotkey": str(meta.hotkeys[uid]) if uid < len(meta.hotkeys) else "",
                    "stake": _safe_get(meta.stake, uid),
                    "trust": _safe_get(getattr(meta, "trust", None), uid),
                    "consensus": _safe_get(getattr(meta, "consensus", None), uid),
                    "incentive": _safe_get(getattr(meta, "incentive", None), uid),
                    "emission": _safe_get(getattr(meta, "emission", None), uid),
                    "dividends": _safe_get(getattr(meta, "dividends", None), uid),
                    "active": bool(meta.active[uid]) if hasattr(meta, "active") and uid < len(meta.active) else False,
                    "validator_trust": _safe_get(getattr(meta, "validator_trust", None), uid),
                }

                metagraph_rows.append(row)

                # Classify as validator or miner based on dividends > 0
                if row["dividends"] > 0 or row["validator_trust"] > 0:
                    validators_rows.append(row)
                else:
                    miners_rows.append(row)

            except Exception as e:
                logger.debug(f"Skipping uid {uid} on subnet {netuid}: {e}")
                continue

        logger.info(f"Subnet {netuid}: {n} neurons indexed")

    logger.info(
        f"Built tables: {len(validators_rows)} validators, "
        f"{len(miners_rows)} miners, {len(metagraph_rows)} metagraph rows"
    )

    return (
        pd.DataFrame(validators_rows),
        pd.DataFrame(miners_rows),
        pd.DataFrame(metagraph_rows),
    )


def build_stakes_table(metagraph_df: pd.DataFrame) -> pd.DataFrame:
    """Build stakes table from metagraph data (stake per neuron)."""
    if metagraph_df.empty:
        return pd.DataFrame()

    stakes = metagraph_df[["netuid", "uid", "hotkey", "stake"]].copy()
    stakes = stakes[stakes["stake"] > 0]
    logger.info(f"Built stakes table: {len(stakes)} rows (non-zero stake)")
    return stakes


def build_emissions_table(metagraph_df: pd.DataFrame) -> pd.DataFrame:
    """Build emissions table from metagraph data."""
    if metagraph_df.empty:
        return pd.DataFrame()

    emissions = metagraph_df[["netuid", "uid", "hotkey", "emission", "incentive", "dividends"]].copy()
    emissions = emissions[emissions["emission"] > 0]
    logger.info(f"Built emissions table: {len(emissions)} rows (non-zero emission)")
    return emissions


def compute_file_checksum(filepath: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def save_snapshot(
    output_dir: Path,
    snapshot_id: str,
    tables: dict[str, pd.DataFrame],
    block_number: int,
    network: str,
) -> None:
    """
    Save all tables as a Parquet snapshot bundle.

    Creates:
        output_dir/
        ├── schema.json
        ├── metadata.json
        └── tables/
            ├── subnets.parquet
            └── ...
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(exist_ok=True)

    # Build schema
    schema_tables = []
    checksums = {}
    row_counts = {}

    for name, df in tables.items():
        if df.empty:
            logger.warning(f"Skipping empty table: {name}")
            continue

        # Write Parquet
        parquet_path = tables_dir / f"{name}.parquet"
        table = pa.Table.from_pandas(df)
        pq.write_table(table, parquet_path)

        # Schema entry
        columns = []
        for col_name, dtype in zip(df.columns, df.dtypes):
            col_type = "VARCHAR"
            if "int" in str(dtype):
                col_type = "INTEGER"
            elif "float" in str(dtype):
                col_type = "DOUBLE"
            elif "bool" in str(dtype):
                col_type = "BOOLEAN"
            elif "datetime" in str(dtype):
                col_type = "TIMESTAMP"
            columns.append({"name": col_name, "type": col_type})

        schema_tables.append({"name": name, "columns": columns})
        checksums[f"{name}.parquet"] = compute_file_checksum(parquet_path)
        row_counts[name] = len(df)

        logger.info(f"Saved {name}.parquet: {len(df)} rows")

    # Write schema.json
    schema = {"snapshot_id": snapshot_id, "tables": schema_tables}
    with open(output_dir / "schema.json", "w") as f:
        json.dump(schema, f, indent=2)

    # Write metadata.json
    metadata = {
        "snapshot_id": snapshot_id,
        "build_time": datetime.now(timezone.utc).isoformat(),
        "block_number": block_number,
        "network": network,
        "row_counts": row_counts,
        "checksums": checksums,
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Snapshot saved: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Build a QueryAgent dataset snapshot")
    parser.add_argument(
        "--network",
        type=str,
        default="test",
        help="Bittensor network (finney, test)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for the snapshot bundle",
    )
    parser.add_argument(
        "--snapshot-id",
        type=str,
        default=None,
        help="Snapshot ID (defaults to directory name)",
    )
    parser.add_argument(
        "--max-subnets",
        type=int,
        default=MAX_SUBNETS,
        help=f"Max subnets to index (default {MAX_SUBNETS})",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    snapshot_id = args.snapshot_id or output_dir.name

    logger.info(f"Connecting to {args.network}...")
    subtensor = bt.Subtensor(network=args.network)
    block = subtensor.block
    logger.info(f"Connected. Current block: {block}")

    # Get all subnet netuids
    netuids = get_all_netuids(subtensor, max_subnets=args.max_subnets)
    if not netuids:
        logger.error("No subnets found. Exiting.")
        return

    # Build all tables
    logger.info("Building subnets table...")
    subnets_df = build_subnets_table(subtensor, netuids)

    logger.info("Building metagraph tables...")
    validators_df, miners_df, metagraph_df = build_metagraph_table(netuids, args.network)

    logger.info("Building stakes table...")
    stakes_df = build_stakes_table(metagraph_df)

    logger.info("Building emissions table...")
    emissions_df = build_emissions_table(metagraph_df)

    # Save snapshot
    tables = {
        "subnets": subnets_df,
        "validators": validators_df,
        "miners": miners_df,
        "stakes": stakes_df,
        "emissions": emissions_df,
        "metagraph": metagraph_df,
    }

    save_snapshot(
        output_dir=output_dir,
        snapshot_id=snapshot_id,
        tables=tables,
        block_number=block,
        network=args.network,
    )

    logger.info("Done!")


if __name__ == "__main__":
    main()

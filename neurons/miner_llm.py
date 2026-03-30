"""
QueryAgent LLM Miner — uses OpenAI to generate SQL from natural language questions.

This is the "real" miner. Instead of regex templates, it sends the question
to an LLM with the database schema, and the LLM writes the SQL.

Usage:
    python -m neurons.miner_llm --netuid <NETUID> --wallet.name <NAME> --wallet.hotkey <HOTKEY> --subtensor.network test

Requires OPENAI_API_KEY environment variable.
"""

import argparse
import json
import logging
import os
import re
import time
import traceback
from typing import Optional

import openai
import bittensor as bt

from queryagent.config import DEFAULT_TIMEOUT_S
from queryagent.hashing import hash_result
from queryagent.protocol import QuerySynapse
from queryagent.snapshot import load_snapshot, load_schema

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# LLM SQL Generation
# ──────────────────────────────────────────────

# Initialize OpenAI client
client = None


def get_client() -> openai.OpenAI:
    """Lazy-init the OpenAI client."""
    global client
    if client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        client = openai.OpenAI(api_key=api_key)
    return client


def get_schema_prompt(snapshot_id: str) -> str:
    """Build a schema description for the LLM from the snapshot's schema.json."""
    from queryagent import config
    snapshot_path = config.SNAPSHOT_DIR / snapshot_id
    schema = load_schema(snapshot_path)

    lines = ["You have access to a DuckDB database with these tables:\n"]
    for table in schema["tables"]:
        cols = ", ".join(f'{c["name"]} ({c["type"]})' for c in table["columns"])
        lines.append(f'  {table["name"]}: {cols}')

    lines.append("""
Table descriptions:
- subnets: one row per subnet. Has ONLY hyperparameters (netuid, tempo, max_n, etc). NO neuron data, NO stake, NO emission.
- validators: neurons with dividends > 0 or validator_trust > 0. Each row = one validator on one subnet.
- miners: all non-validator neurons. Each row = one miner on one subnet.
- metagraph: ALL neurons (validators + miners combined). Use this for questions about "all neurons" or cross-type analysis.
- stakes: neurons with stake > 0. Use this for total stake questions.
- emissions: neurons with emission > 0. Use this for total emission questions.

CRITICAL DuckDB rules (violations will cause errors):
1. Every non-aggregated column in SELECT MUST be in GROUP BY
2. ORDER BY columns MUST exist in SELECT or be aggregate expressions
3. For single-row aggregates (SUM, COUNT, AVG with no GROUP BY), do NOT add ORDER BY
4. Use NULLIF(x, 0) to avoid division by zero
5. Use window functions (OVER) only when ranking or computing running totals within groups

Examples of CORRECT queries:
Q: "Total TAO staked?" → SELECT SUM(stake) AS total_staked FROM stakes
Q: "How many subnets?" → SELECT COUNT(*) AS subnet_count FROM subnets
Q: "Miners on subnet 1?" → SELECT COUNT(*) AS miner_count FROM miners WHERE netuid = 1 AND active = true
Q: "Total emission?" → SELECT SUM(emission) AS total_emission FROM emissions
Q: "Validators with non-zero stake?" → SELECT COUNT(*) AS validator_count FROM validators WHERE stake > 0
Q: "Average stake per validator?" → SELECT AVG(stake) AS avg_stake FROM validators WHERE stake > 0
Q: "Top 10 validators by stake?" → SELECT netuid, uid, hotkey, stake FROM validators ORDER BY stake DESC LIMIT 10
Q: "Emission per subnet?" → SELECT netuid, SUM(emission) AS total_emission FROM emissions GROUP BY netuid ORDER BY total_emission DESC
Q: "Avg validator trust per subnet?" → SELECT netuid, AVG(validator_trust) AS avg_vtrust FROM validators GROUP BY netuid ORDER BY avg_vtrust DESC
Q: "Active miners per subnet?" → SELECT netuid, COUNT(*) AS active_miners FROM miners WHERE active = true GROUP BY netuid ORDER BY active_miners DESC""")

    return "\n".join(lines)


# Cache the schema prompt per snapshot
_schema_cache: dict[str, str] = {}


def generate_sql_llm(
    question: str,
    snapshot_id: str,
    constraints: Optional[dict] = None,
) -> Optional[dict]:
    """
    Use an LLM to generate SQL from a natural language question.

    Returns dict with {sql, tables, explanation} or None on failure.
    """
    constraints = constraints or {}

    # Get or cache schema
    if snapshot_id not in _schema_cache:
        _schema_cache[snapshot_id] = get_schema_prompt(snapshot_id)
    schema_prompt = _schema_cache[snapshot_id]

    # Build the prompt
    constraint_text = ""
    if constraints:
        parts = []
        if "k" in constraints:
            parts.append(f"Return top {constraints['k']} results")
        if "netuid_filter" in constraints:
            parts.append(f"Filter to subnet {constraints['netuid_filter']}")
        if "time_window" in constraints:
            parts.append(f"Time window: {constraints['time_window']}")
        if parts:
            constraint_text = "\nConstraints: " + ", ".join(parts)

    prompt = f"""{schema_prompt}

Question: {question}{constraint_text}

Write a single DuckDB SQL query that answers this question.

Rules:
- Return ONLY the SQL, wrapped in ```sql``` code blocks
- Use only SELECT statements
- Use the exact table and column names from the schema above
- If the question asks for "top N", use LIMIT N
- For single-value aggregates (no GROUP BY), do NOT add ORDER BY
- For grouped results, add ORDER BY on a column that is in your SELECT
- Every column in SELECT that is not an aggregate MUST be in GROUP BY"""

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract SQL from response
        text = response.choices[0].message.content
        sql = _extract_sql(text)

        if not sql:
            logger.warning(f"No SQL extracted from LLM response: {text[:200]}")
            return None

        # Detect tables used
        tables_used = _detect_tables(sql)

        return {
            "sql": sql,
            "tables": tables_used,
            "explanation": f"LLM-generated SQL for: {question[:80]}",
        }

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return None


def _extract_sql(text: str) -> Optional[str]:
    """Extract SQL from LLM response (handles code blocks and plain text)."""
    # Try to find ```sql ... ``` block
    match = re.search(r"```sql\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try ``` ... ``` block
    match = re.search(r"```\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If it looks like raw SQL (starts with SELECT/WITH)
    text = text.strip()
    if text.upper().startswith(("SELECT", "WITH")):
        # Take everything up to the first semicolon or end
        return text.split(";")[0].strip()

    return None


def _detect_tables(sql: str) -> list[str]:
    """Detect which tables are referenced in the SQL."""
    known_tables = ["subnets", "validators", "miners", "stakes", "emissions", "metagraph"]
    sql_lower = sql.lower()
    return [t for t in known_tables if t in sql_lower]


# ──────────────────────────────────────────────
# Miner Forward Function
# ──────────────────────────────────────────────

def generate_sql_hybrid(
    question: str,
    snapshot_id: str,
    constraints: Optional[dict] = None,
) -> Optional[dict]:
    """
    Hybrid strategy: try template miner first (fast, deterministic),
    fall back to LLM for questions templates can't match.
    """
    from neurons.miner import generate_sql as template_generate

    # Try template first
    result = template_generate(question, constraints)
    if result is not None:
        logger.info("Template match found — skipping LLM")
        return result

    # Fall back to LLM
    logger.info("No template match — using LLM")
    return generate_sql_llm(question, snapshot_id, constraints)


def forward(synapse: QuerySynapse) -> QuerySynapse:
    """
    Process a QuerySynapse request using hybrid strategy:
    template miner first, LLM fallback.
    """
    start_time = time.perf_counter()

    try:
        logger.info(
            f"Received task {synapse.task_id}: "
            f"{synapse.question[:80]}..."
        )

        # Load snapshot
        conn = load_snapshot(synapse.snapshot_id)

        # Generate SQL: template first, LLM fallback
        result = generate_sql_hybrid(
            synapse.question,
            synapse.snapshot_id,
            synapse.constraints,
        )

        if result is None:
            logger.warning(f"Both template and LLM failed for: {synapse.question[:80]}")
            return synapse

        sql = result["sql"]
        tables_used = result["tables"]
        explanation = result["explanation"]

        # Execute SQL and compute hash
        result_hash = hash_result(conn, sql)

        # Build result preview
        res = conn.execute(sql)
        columns = [desc[0] for desc in res.description]
        rows = res.fetchall()
        preview_rows = [list(row) for row in rows[:10]]

        # Fill synapse response
        synapse.sql = sql
        synapse.result_hash = result_hash
        synapse.result_preview = {"columns": columns, "rows": preview_rows}
        synapse.tables_used = tables_used
        synapse.explanation = explanation

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Task {synapse.task_id} completed in {elapsed:.0f}ms — "
            f"hash={result_hash[:30]}..."
        )

    except Exception as e:
        logger.error(f"Error processing task {synapse.task_id}: {e}")
        logger.debug(traceback.format_exc())

    return synapse


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QueryAgent LLM Miner")
    parser.add_argument("--netuid", type=int, required=True, help="Subnet network ID")
    parser.add_argument("--axon.port", type=int, default=8091, help="Axon port")
    bt.Wallet.add_args(parser)
    bt.Subtensor.add_args(parser)

    config = bt.Config(parser)
    wallet = bt.Wallet(config=config)
    subtensor = bt.Subtensor(config=config)
    metagraph = bt.Metagraph(netuid=config.netuid, network=config.subtensor.network, sync=True)

    logger.info(f"Wallet: {wallet}")
    logger.info(f"Metagraph: {metagraph.n} neurons on subnet {config.netuid}")

    # Create and configure axon
    axon = bt.Axon(wallet=wallet, port=config.axon.port)
    axon.attach(forward_fn=forward)
    axon.serve(netuid=config.netuid, subtensor=subtensor)
    axon.start()

    logger.info(f"LLM Miner axon started on port {config.axon.port}")

    try:
        while True:
            time.sleep(12)
    except KeyboardInterrupt:
        logger.info("Miner shutting down...")
    finally:
        axon.stop()


if __name__ == "__main__":
    main()

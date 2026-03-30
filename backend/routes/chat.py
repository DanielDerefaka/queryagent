"""
AI Chat endpoint — converts natural language questions to SQL via Gemini,
executes on DuckDB, and returns results.
"""

import os
import json
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from queryagent.snapshot import load_snapshot, execute_sql_safe
from queryagent.hashing import hash_result

router = APIRouter()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
DEFAULT_SNAPSHOT = "bt_snapshot_test_v1"

# Full schema injected into every prompt (~500 tokens)
SCHEMA_DDL = """
CREATE TABLE subnets (
  netuid INTEGER,        -- subnet ID
  tempo INTEGER,         -- block tempo
  max_n INTEGER,         -- max neurons allowed
  immunity_period INTEGER,
  min_difficulty INTEGER,
  weights_rate_limit INTEGER
);

CREATE TABLE validators (
  netuid INTEGER,        -- subnet ID
  uid INTEGER,           -- unique neuron ID within subnet
  hotkey VARCHAR,        -- SS58 hotkey address
  stake DOUBLE,          -- TAO staked
  trust DOUBLE,
  consensus DOUBLE,
  incentive DOUBLE,
  emission DOUBLE,       -- TAO emission earned
  dividends DOUBLE,
  active BOOLEAN,
  validator_trust DOUBLE
);

CREATE TABLE miners (
  netuid INTEGER,
  uid INTEGER,
  hotkey VARCHAR,
  stake DOUBLE,
  trust DOUBLE,
  consensus DOUBLE,
  incentive DOUBLE,      -- incentive score (0-1)
  emission DOUBLE,       -- TAO emission earned
  dividends DOUBLE,
  active BOOLEAN,
  validator_trust DOUBLE
);

CREATE TABLE stakes (
  netuid INTEGER,
  uid INTEGER,
  hotkey VARCHAR,
  stake DOUBLE           -- TAO staked amount
);

CREATE TABLE emissions (
  netuid INTEGER,
  uid INTEGER,
  hotkey VARCHAR,
  emission DOUBLE,
  incentive DOUBLE,
  dividends DOUBLE
);

CREATE TABLE metagraph (
  netuid INTEGER,        -- subnet ID
  uid INTEGER,           -- neuron UID
  hotkey VARCHAR,        -- SS58 address
  stake DOUBLE,          -- TAO staked
  trust DOUBLE,          -- trust score (0-1)
  consensus DOUBLE,      -- consensus score (0-1)
  incentive DOUBLE,      -- incentive score (0-1)
  emission DOUBLE,       -- TAO emission
  dividends DOUBLE,      -- validator dividends
  active BOOLEAN,        -- currently active
  validator_trust DOUBLE -- validator trust score
);
"""

# Few-shot examples to guide the model
FEW_SHOT_EXAMPLES = """
Q: How many subnets are there?
SQL: SELECT COUNT(DISTINCT netuid) AS subnet_count FROM subnets;

Q: Top 5 miners by incentive
SQL: SELECT uid, hotkey, incentive, emission, stake, netuid FROM metagraph WHERE incentive > 0 ORDER BY incentive DESC LIMIT 5;

Q: Which subnet has the most miners?
SQL: SELECT netuid, COUNT(*) AS miner_count FROM miners GROUP BY netuid ORDER BY miner_count DESC LIMIT 5;

Q: Total TAO staked
SQL: SELECT ROUND(SUM(stake), 2) AS total_staked FROM stakes;

Q: Top earning miners by emission
SQL: SELECT uid, hotkey, emission, incentive, stake, netuid FROM metagraph WHERE emission > 0 ORDER BY emission DESC LIMIT 10;

Q: Average stake per validator
SQL: SELECT ROUND(AVG(stake), 2) AS avg_stake FROM validators WHERE stake > 0;

Q: Show me the metagraph for subnet 2
SQL: SELECT uid, hotkey, stake, trust, consensus, incentive, emission, active FROM metagraph WHERE netuid = 2 ORDER BY uid;

Q: How many active miners are there?
SQL: SELECT COUNT(*) AS active_miners FROM metagraph WHERE active = true;

Q: Validators with highest trust
SQL: SELECT uid, hotkey, validator_trust, stake, netuid FROM validators WHERE validator_trust > 0 ORDER BY validator_trust DESC LIMIT 10;

Q: Emission distribution by subnet
SQL: SELECT netuid, ROUND(SUM(emission), 4) AS total_emission FROM emissions GROUP BY netuid ORDER BY total_emission DESC;

Q: Who has the most stake?
SQL: SELECT uid, hotkey, stake, netuid FROM metagraph WHERE stake > 0 ORDER BY stake DESC LIMIT 10;

Q: How many miners per subnet?
SQL: SELECT netuid, COUNT(*) AS miner_count FROM miners GROUP BY netuid ORDER BY netuid;

Q: Subnet configuration details
SQL: SELECT * FROM subnets ORDER BY netuid;

Q: Top validators by dividends
SQL: SELECT uid, hotkey, dividends, stake, netuid FROM validators WHERE dividends > 0 ORDER BY dividends DESC LIMIT 10;

Q: What is the consensus distribution?
SQL: SELECT netuid, ROUND(AVG(consensus), 4) AS avg_consensus, COUNT(*) AS neurons FROM metagraph GROUP BY netuid ORDER BY avg_consensus DESC;
"""

SYSTEM_PROMPT = f"""You are a SQL assistant for a Bittensor blockchain analytics database running DuckDB.

Rules:
- Generate ONLY a single SELECT query. No INSERT, UPDATE, DELETE, CREATE, DROP, or ALTER.
- Use ONLY the tables and columns listed in the schema below.
- Return ONLY the raw SQL query, nothing else. No explanation, no markdown, no code fences.
- Use ROUND() for decimal values to keep output readable.
- Always add a LIMIT clause (max 50 rows) unless the user asks for a specific count.
- If the question is ambiguous, make a reasonable assumption and query the most relevant table.
- The metagraph table contains ALL neurons (miners + validators). Use it for general queries.
- Use the miners table for miner-specific queries and validators table for validator-specific queries.

Schema:
{SCHEMA_DDL}

Examples:
{FEW_SHOT_EXAMPLES}"""


class ChatRequest(BaseModel):
    question: str
    snapshot_id: Optional[str] = None


class ChatResponse(BaseModel):
    question: str
    sql: str
    answer: str
    columns: list[str]
    rows: list[list]
    row_count: int
    exec_ms: float
    result_hash: str
    snapshot_id: str


async def call_gemini(question: str, retry_with_error: Optional[str] = None) -> str:
    """Call Gemini API to generate SQL from a natural language question."""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    if retry_with_error:
        user_msg = (
            f"The previous SQL query failed with this error:\n{retry_with_error}\n\n"
            f"Original question: {question}\n\n"
            f"Please fix the SQL query. Return ONLY the corrected SQL."
        )
    else:
        user_msg = question

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\nQ: " + user_msg + "\nSQL:"}]}
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 512,
        },
    }

    url = GEMINI_URL_TEMPLATE.format(GEMINI_MODEL)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{url}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail="Unexpected Gemini response format")

    # Clean up: remove markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()

    # Remove trailing semicolons (DuckDB handles both)
    text = text.rstrip(";").strip()

    return text


def build_answer(question: str, columns: list[str], rows: list, row_count: int) -> str:
    """Build a natural language answer from the query result."""
    if row_count == 0:
        return "No results found for that query."
    if row_count == 1 and len(columns) == 1:
        return f"The answer is **{rows[0][0]}**."
    if row_count == 1:
        parts = [f"{c}: **{rows[0][i]}**" for i, c in enumerate(columns)]
        return ", ".join(parts)
    return f"Found **{row_count}** results:"


import re


def fallback_question_to_sql(question: str) -> Optional[str]:
    """Simple pattern matcher as fallback when Gemini is unavailable."""
    q = question.lower()
    top_m = re.search(r"top\s+(\d+)", q)
    k = top_m.group(1) if top_m else "10"
    sub_m = re.search(r"(?:subnet|netuid)\s+(\d+)", q)
    netuid = sub_m.group(1) if sub_m else "1"

    if "how many subnet" in q:
        return "SELECT COUNT(DISTINCT netuid) AS subnet_count FROM subnets"
    if "top" in q and "miner" in q:
        if "stak" in q:
            return f"SELECT uid, hotkey, stake, incentive, netuid FROM metagraph WHERE stake > 0 ORDER BY stake DESC LIMIT {k}"
        if "earn" in q or "emission" in q:
            return f"SELECT uid, hotkey, emission, incentive, stake, netuid FROM metagraph WHERE emission > 0 ORDER BY emission DESC LIMIT {k}"
        return f"SELECT uid, hotkey, incentive, emission, stake, netuid FROM metagraph WHERE incentive > 0 ORDER BY incentive DESC LIMIT {k}"
    if ("earn" in q or "emission" in q) and "miner" in q:
        return f"SELECT uid, hotkey, emission, incentive, stake, netuid FROM metagraph WHERE emission > 0 ORDER BY emission DESC LIMIT {k}"
    if "top" in q and "validator" in q:
        return f"SELECT uid, hotkey, stake, dividends, validator_trust, netuid FROM validators ORDER BY stake DESC LIMIT {k}"
    if "total" in q and "stak" in q:
        return "SELECT ROUND(SUM(stake), 2) AS total_staked FROM stakes"
    if "most miner" in q or ("which subnet" in q and "miner" in q):
        return "SELECT netuid, COUNT(*) AS miner_count FROM miners GROUP BY netuid ORDER BY miner_count DESC LIMIT 5"
    if "metagraph" in q and ("subnet" in q or "netuid" in q):
        return f"SELECT * FROM metagraph WHERE netuid = {netuid} ORDER BY uid"
    if "validator" in q and ("count" in q or "how many" in q):
        return "SELECT COUNT(*) AS validator_count FROM validators"
    if "miner" in q and ("count" in q or "how many" in q):
        return "SELECT COUNT(*) AS miner_count FROM miners"
    if "emission" in q:
        return "SELECT netuid, ROUND(SUM(emission), 4) AS total_emission FROM emissions GROUP BY netuid ORDER BY total_emission DESC"
    if "active" in q and "miner" in q:
        return "SELECT netuid, COUNT(*) AS active_miners FROM metagraph WHERE active = true GROUP BY netuid ORDER BY active_miners DESC"
    if "subnet" in q and any(w in q for w in ["info", "detail", "list", "all", "show"]):
        return "SELECT * FROM subnets ORDER BY netuid"
    if ("highest" in q or "best" in q or "richest" in q or "top" in q) and "stak" in q:
        return f"SELECT uid, hotkey, stake, netuid FROM metagraph WHERE stake > 0 ORDER BY stake DESC LIMIT {k}"
    if "average stake" in q:
        return "SELECT ROUND(AVG(stake), 2) AS avg_stake FROM metagraph WHERE stake > 0"
    return None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Natural language question → SQL → DuckDB execution → verified answer."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty")

    snapshot_id = req.snapshot_id or DEFAULT_SNAPSHOT

    try:
        conn = load_snapshot(snapshot_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {snapshot_id}")

    # Step 1: Generate SQL via Gemini (with fallback to local mapper)
    used_fallback = False
    try:
        sql = await call_gemini(question)
    except HTTPException:
        # Gemini unavailable (quota, network, etc.) — fall back to local mapper
        sql = fallback_question_to_sql(question)
        if not sql:
            raise HTTPException(
                status_code=400,
                detail="AI is temporarily unavailable and I couldn't match your question to a known pattern. Try asking about subnets, miners, validators, stakes, or emissions.",
            )
        used_fallback = True

    # Step 2: Execute on DuckDB (with 1 retry via Gemini on error)
    try:
        columns, rows, exec_ms = execute_sql_safe(conn, sql)
    except Exception as first_error:
        if used_fallback:
            raise HTTPException(status_code=400, detail=f"Query failed: {str(first_error)}")
        # Retry: feed the error back to Gemini for correction
        try:
            sql = await call_gemini(question, retry_with_error=str(first_error))
            columns, rows, exec_ms = execute_sql_safe(conn, sql)
        except Exception as retry_error:
            raise HTTPException(
                status_code=400,
                detail=f"SQL generation failed after retry. Error: {str(retry_error)}. Generated SQL: {sql}",
            )

    # Step 3: Hash the result
    try:
        result_hash = hash_result(conn, sql)
    except Exception:
        result_hash = "sha256:error"

    # Step 4: Serialize rows
    serializable_rows = []
    for row in rows[:50]:
        serializable_rows.append([str(v) if v is not None else None for v in row])

    # Step 5: Build natural language answer
    answer = build_answer(question, columns, rows, len(rows))

    return ChatResponse(
        question=question,
        sql=sql,
        answer=answer,
        columns=columns,
        rows=serializable_rows,
        row_count=len(rows),
        exec_ms=round(exec_ms, 2),
        result_hash=result_hash,
        snapshot_id=snapshot_id,
    )

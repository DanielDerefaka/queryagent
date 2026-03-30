# Synapse Protocol

## What Is a Synapse
The main data object for validator-miner communication. Extends Pydantic BaseModel.

## Defining a Custom Synapse

```python
import bittensor as bt
from typing import Optional, List

class QuerySynapse(bt.Synapse):
    """Wire format for QueryAgent validator ↔ miner communication."""

    # ── Validator → Miner (request fields) ──
    task_id: str = ""
    snapshot_id: str = ""
    question: str = ""
    constraints: Optional[dict] = None

    # ── Miner → Validator (response fields) ──
    sql: Optional[str] = None
    result_preview: Optional[dict] = None
    result_hash: Optional[str] = None
    tables_used: Optional[List[str]] = None
    explanation: Optional[str] = None
```

## Built-in Fields (inherited from bt.Synapse)
Every Synapse automatically includes:

### Terminal Information
- `version`: Bittensor version running on terminal
- `nonce`: Unique, monotonically increasing number per terminal
- `uuid`: Unique identifier for terminal
- `hotkey`: Encoded hotkey string of terminal wallet
- `signature`: Digital signature verifying (nonce, axon_hotkey, dendrite_hotkey, uuid)

### Network Properties
- `timeout`: Request timeout duration
- `axon`: Axon endpoint details (IP, port, public key)
- `dendrite`: Dendrite client details

### Size Metrics
- Header size and total object size (for bandwidth management)

## Serialization Flow
1. Include synapse name and timeout
2. Serialize axon/dendrite objects to strings
3. Base64 encode non-optional complex objects
4. Calculate header and total object sizes
5. Return HTTP-compatible headers

## Key Rules
- **Must be JSON serializable** — all fields must serialize for HTTP transport
- **Both sides must deserialize correctly** — validators and miners share the same Synapse class
- **Request fields**: Set by validator before sending
- **Response fields**: Set by miner before returning (use `Optional` with `None` default)
- **Pydantic validation**: Type checking enforced automatically

## Request/Response Pattern
```
Validator                          Miner
   │                                 │
   │  QuerySynapse(task_id, ...)    │
   │ ──────────────────────────────→│
   │                                 │ forward(synapse) processes task
   │                                 │ synapse.sql = "SELECT ..."
   │                                 │ synapse.result_hash = "sha256:..."
   │  QuerySynapse(sql, hash, ...)  │
   │ ←──────────────────────────────│
   │                                 │
   │  Validator re-executes SQL      │
   │  Compares hash to ground truth  │
   │  Computes score                 │
```

## Streaming Synapses
For large responses, Bittensor supports streaming:
```python
class StreamingSynapse(bt.StreamingSynapse):
    async def process_streaming_response(self, response):
        async for chunk in response.content.iter_any():
            yield chunk
```
- **Not needed for QueryAgent** — our Answer Packages are small enough for standard Synapse

## For QueryAgent
Our `QuerySynapse` needs exactly these fields:
- **Request**: `task_id`, `snapshot_id`, `question`, `constraints` (optional dict with time_window, max_rows, etc.)
- **Response**: `sql`, `result_hash`, `result_preview` (dict with columns + rows), `tables_used` (list), `explanation`
- All response fields should be `Optional[type] = None` so the synapse is valid even before the miner fills it

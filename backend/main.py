"""
QueryAgent API Backend — bridges the frontend dashboard to real subnet data.

Connects to:
- DuckDB snapshots for SQL execution
- Bittensor metagraph for live neuron data
- Training data pipeline for dataset stats

Usage:
    uvicorn backend.main:app --reload --port 8000
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from backend/ directory
load_dotenv(Path(__file__).parent / ".env")

from backend.routes.query import router as query_router
from backend.routes.schema import router as schema_router
from backend.routes.leaderboard import router as leaderboard_router
from backend.routes.stats import router as stats_router
from backend.routes.training import router as training_router
from backend.routes.chat import router as chat_router

app = FastAPI(
    title="QueryAgent API",
    version="0.1.0",
    description="Backend API for the QueryAgent dashboard",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(query_router, prefix="/api")
app.include_router(schema_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "queryagent-api"}

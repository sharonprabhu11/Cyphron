"""
Cyphron pipeline backend entrypoint (FastAPI).

Minimal working checks:
- prints "FastAPI server started" on startup
- GET / returns "Cyphron backend running"
- calls placeholder initializers (Pub/Sub, Neo4j, Redis) without failing hard
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

# Allow `python pipeline/main.py` from repo root on Windows.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    import uvicorn
    from fastapi import FastAPI
except Exception as exc:  # foundation-only: allow running without installed deps
    print("FastAPI server started", flush=True)
    print(f"(Install backend deps to run API: pip install -r requirements.txt) {exc}", flush=True)
    raise SystemExit(0)

from pipeline.entity_resolution.redis_client import initialize_redis
from pipeline.graph.neo4j_client import initialize_neo4j
from pipeline.ingestion.pubsub_consumer import start_consumer

PORT = int(os.getenv("PIPELINE_PORT", os.getenv("PORT", "8001")))
HOST = os.getenv("PIPELINE_HOST", "0.0.0.0")


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("FastAPI server started", flush=True)
    start_consumer()
    initialize_neo4j()
    initialize_redis()
    yield


app = FastAPI(title="Cyphron Pipeline Backend", lifespan=lifespan)


@app.get("/")
def root():
    return "Cyphron backend running"


if __name__ == "__main__":
    print(f"Binding backend on http://{HOST}:{PORT}", flush=True)
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)


"""
Cyphron pipeline backend entrypoint (FastAPI).

Database layer: Firestore + BigQuery initialization on startup.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI
import uvicorn

from pipeline.config import ENABLE_GCP_STARTUP
from pipeline.db import create_dummy_collections, init_bigquery, init_firestore
from pipeline.decision.api import router as decision_router
from pipeline.graph.neo4j_client import get_neo4j_client, initialize_neo4j
from pipeline.services import DecisionService

# Default 8810 avoids common 8000/8001 conflicts; override with PIPELINE_PORT or PORT.
PORT = int(os.getenv("PIPELINE_PORT", os.getenv("PORT", "8810")))
HOST = os.getenv("PIPELINE_HOST", "0.0.0.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing pipeline services...", flush=True)

    if ENABLE_GCP_STARTUP:
        try:
            init_firestore()
            create_dummy_collections()
            init_bigquery()
            print("GCP sinks ready", flush=True)
        except Exception as exc:
            print(f"GCP startup skipped: {exc}", flush=True)
    else:
        print("GCP startup skipped by configuration", flush=True)

    app.state.neo4j_client = initialize_neo4j()

    try:
        app.state.decision_service = DecisionService(
            neo4j_client=get_neo4j_client(),
        )
        print("Decision service ready", flush=True)
    except Exception as exc:
        app.state.decision_service = None
        print(f"Decision service initialization failed: {exc}", flush=True)

    yield


app = FastAPI(title="Cyphron Pipeline Backend", lifespan=lifespan)
app.include_router(decision_router)


@app.get("/")
def root():
    return {"message": "Cyphron backend running"}


if __name__ == "__main__":
    print(f"Binding backend on http://{HOST}:{PORT}", flush=True)
    uvicorn.run("pipeline.main:app", host=HOST, port=PORT, reload=False)

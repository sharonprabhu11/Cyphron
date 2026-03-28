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

from pipeline.db import create_dummy_collections, init_bigquery, init_firestore

# Default 8810 avoids common 8000/8001 conflicts; override with PIPELINE_PORT or PORT.
PORT = int(os.getenv("PIPELINE_PORT", os.getenv("PORT", "8810")))
HOST = os.getenv("PIPELINE_HOST", "0.0.0.0")


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("Initializing DB...", flush=True)
    init_firestore()
    create_dummy_collections()
    init_bigquery()
    print("DB setup complete", flush=True)
    yield


app = FastAPI(title="Cyphron Pipeline Backend", lifespan=lifespan)


@app.get("/")
def root():
    return "Cyphron backend running"


if __name__ == "__main__":
    print(f"Binding backend on http://{HOST}:{PORT}", flush=True)
    uvicorn.run("pipeline.main:app", host=HOST, port=PORT, reload=False)

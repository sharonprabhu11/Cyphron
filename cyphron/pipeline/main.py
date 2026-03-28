"""
Cyphron pipeline entrypoint.

- serve: FastAPI backend (default when invoked with no subcommand)
- ingestion: Pub/Sub publisher + subscriber
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from contextlib import asynccontextmanager

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from pipeline.config import ENABLE_GCP_STARTUP, FRONTEND_ORIGINS
from pipeline.db import create_dummy_collections, init_bigquery, init_firestore
from pipeline.decision.api import router as decision_router
from pipeline.graph.neo4j_client import get_neo4j_client, initialize_neo4j
from pipeline.services import DecisionService

PORT = int(os.getenv("PIPELINE_PORT", os.getenv("PORT", "8810")))
HOST = os.getenv("PIPELINE_HOST", "0.0.0.0")
CORS_ORIGINS = [origin.strip() for origin in (FRONTEND_ORIGINS or "").split(",") if origin.strip()]


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(decision_router)


@app.get("/")
def root():
    return {"message": "Cyphron backend running"}


def run_ingestion() -> None:
    """Run simulator publisher and Pub/Sub subscriber."""
    import pipeline.ingestion.schema  # noqa: F401

    from pipeline.ingestion import publisher as ingestion_publisher
    from pipeline.ingestion import subscriber as ingestion_subscriber

    print("Starting ingestion: publisher (background) + subscriber (foreground)", flush=True)
    pub_thread = threading.Thread(
        target=ingestion_publisher.run_stream,
        daemon=True,
        name="ingestion-publisher",
    )
    pub_thread.start()
    ingestion_subscriber.listen()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cyphron pipeline")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="Run FastAPI backend (default if no subcommand)")
    sub.add_parser("ingestion", help="Run Pub/Sub ingestion (publisher + subscriber)")
    return parser


def main_cli(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    parser = _build_parser()

    if not argv:
        argv = ["serve"]

    args = parser.parse_args(argv)
    if args.command == "serve":
        print(f"Binding backend on http://{HOST}:{PORT}", flush=True)
        uvicorn.run("pipeline.main:app", host=HOST, port=PORT, reload=False)
        return
    if args.command == "ingestion":
        run_ingestion()
        return

    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main_cli()

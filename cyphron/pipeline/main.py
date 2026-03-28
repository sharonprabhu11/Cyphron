"""
Cyphron pipeline entrypoint.

- serve: FastAPI backend (default when invoked with no subcommand).
- ingestion: Pub/Sub publisher + subscriber (Transaction schema validated on consume).

Graph, features, and other stages can be wired here later.
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
import uvicorn

# Default 8810 avoids common 8000/8001 conflicts; override with PIPELINE_PORT or PORT.
PORT = int(os.getenv("PIPELINE_PORT", os.getenv("PORT", "8810")))
HOST = os.getenv("PIPELINE_HOST", "0.0.0.0")


@asynccontextmanager
async def lifespan(_: FastAPI):
    from pipeline.db import create_dummy_collections, init_bigquery, init_firestore

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


def run_ingestion() -> None:
    """Run simulator publisher and Pub/Sub subscriber (Transaction schema enforced in subscriber)."""
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

    sub.add_parser("serve", help="Run FastAPI + DB init (default if no subcommand)")
    sub.add_parser("ingestion", help="Run Pub/Sub ingestion (publisher + subscriber)")

    return parser


def main_cli(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    parser = _build_parser()

    if not argv:
        argv = ["serve"]

    args = parser.parse_args(argv)
    cmd = args.command

    if cmd == "serve":
        print(f"Binding backend on http://{HOST}:{PORT}", flush=True)
        uvicorn.run("pipeline.main:app", host=HOST, port=PORT, reload=False)
    elif cmd == "ingestion":
        run_ingestion()
    else:
        parser.print_help()
        raise SystemExit(2)


if __name__ == "__main__":
    main_cli()

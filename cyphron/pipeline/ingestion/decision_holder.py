"""Lazy DecisionService for Pub/Sub subscriber (no HTTP server)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.services import DecisionService

_svc: "DecisionService | None" = None
_init_error: str | None = None


def get_ingestion_decision_service() -> "DecisionService | None":
    global _svc, _init_error
    if _svc is not None:
        return _svc
    if _init_error is not None:
        return None
    try:
        from pipeline.graph.neo4j_client import initialize_neo4j
        from pipeline.services import DecisionService

        neo = initialize_neo4j()
        _svc = DecisionService(neo4j_client=neo)
        print("Ingestion: DecisionService initialized", flush=True)
        return _svc
    except Exception as exc:
        _init_error = str(exc)
        print(f"Ingestion: DecisionService unavailable ({exc})", flush=True)
        return None

"""
FastAPI routes for real-time fraud decisioning.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from pipeline.ingestion.schema import Transaction
from pipeline.models import DecisionResponse, HealthResponse


router = APIRouter()


def _get_decision_service(request: Request):
    service = getattr(request.app.state, "decision_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Decision service is not ready.")
    return service


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    service = getattr(request.app.state, "decision_service", None)
    neo4j_client = getattr(request.app.state, "neo4j_client", None)
    return HealthResponse(
        status="ok",
        neo4j_connected=neo4j_client is not None,
        model_loaded=service is not None,
    )


@router.post("/decision", response_model=DecisionResponse)
def decide(transaction: Transaction, request: Request) -> DecisionResponse:
    service = _get_decision_service(request)
    return service.decide(transaction)

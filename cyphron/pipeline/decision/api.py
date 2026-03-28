"""
FastAPI routes for real-time fraud decisioning.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from pipeline.compliance.storage import (
    get_alert,
    get_transaction,
    list_alerts,
    store_decision_result,
)
from pipeline.compliance.pdf_renderer import render_pdf
from pipeline.compliance.str_generator import generate_str
from pipeline.ingestion.schema import Transaction
from pipeline.ml.history import append_training_history
from pipeline.models import DecisionResponse, HealthResponse


router = APIRouter()


def _append_history_safely(transaction: Transaction, decision: DecisionResponse) -> None:
    try:
        path = append_training_history(transaction, decision)
        print(f"Training history appended at {path}", flush=True)
    except Exception as exc:
        print(f"Training history append failed: {exc}", flush=True)


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


@router.get("/alerts")
def alerts(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    try:
        return list_alerts(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to fetch alerts: {exc}") from exc


@router.get("/alerts/{alert_id}")
def alert_detail(alert_id: str) -> dict[str, Any]:
    try:
        alert = get_alert(alert_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to fetch alert: {exc}") from exc
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert


@router.get("/transactions/{transaction_id}")
def transaction_detail(transaction_id: str) -> dict[str, Any]:
    try:
        transaction = get_transaction(transaction_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to fetch transaction: {exc}") from exc
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return transaction


@router.post("/decision", response_model=DecisionResponse)
def decide(transaction: Transaction, request: Request) -> DecisionResponse:
    service = _get_decision_service(request)
    base_response: DecisionResponse = service.decide(transaction)
    if base_response.risk_tier != "CRITICAL":
        _append_history_safely(transaction, base_response)
        store_decision_result(transaction, base_response)
        return base_response

    reasons = [factor.detail for factor in base_response.top_factors if factor.detail]
    if not reasons:
        reasons = ["Composite graph and model signals exceeded the critical risk threshold."]

    str_text = generate_str(
        entity_id=base_response.source_account_id,
        risk_score=base_response.composite_score,
        tier=base_response.risk_tier,
        reasons=reasons,
        transaction_summary=transaction.model_dump(),
    )
    pdf_path = render_pdf(
        entity_id=base_response.source_account_id,
        risk_score=base_response.composite_score,
        tier=base_response.risk_tier,
        reasons=reasons,
        str_text=str_text,
    )

    response = base_response.model_copy(update={
        "str_report": str_text,
        "pdf_path": pdf_path,
    })
    _append_history_safely(transaction, response)
    store_decision_result(transaction, response)
    return response

"""
FastAPI routes for real-time fraud decisioning.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from pipeline.compliance.storage import store_decision_result
from pipeline.compliance.pdf_renderer import render_pdf
from pipeline.compliance.str_generator import generate_str
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
    base_response: DecisionResponse = service.decide(transaction)
    if base_response.risk_tier != "CRITICAL":
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
    store_decision_result(transaction, response)
    return response

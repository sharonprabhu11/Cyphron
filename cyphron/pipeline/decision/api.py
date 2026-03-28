"""
FastAPI routes for real-time fraud decisioning.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from pipeline.ingestion.schema import Transaction
from pipeline.models import DecisionResponse, HealthResponse, DecisionFactor


from pipeline.scoring.composite import compute_risk_score, get_risk_tier
from pipeline.scoring.explainability import generate_explanation
from pipeline.compliance.str_generator import generate_str
from pipeline.compliance.pdf_renderer import render_pdf


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

    # -----------------------------
    # STEP 1: Get base decision (UNCHANGED)
    # -----------------------------
    base_response: DecisionResponse = service.decide(transaction)

    # -----------------------------
    # STEP 2: Extract values
    # -----------------------------
    gnn_score = base_response.gnn_probability
    rule_flags = base_response.rule_flags or []
    rule_matches = base_response.rule_matches or {}

    # Convert rule flags → dict for scoring
    rule_flag_dict = {flag: 1 for flag in rule_flags}

    # -----------------------------
    # STEP 3: Compute improved score
    # -----------------------------
    score = compute_risk_score(gnn_score, rule_flag_dict)
    tier = get_risk_tier(score)

    # -----------------------------
    # STEP 4: Generate explanations
    # -----------------------------
    reasons = generate_explanation(gnn_score, rule_flag_dict)

    # Add to existing top_factors (do NOT overwrite)
    enhanced_factors = list(base_response.top_factors)

    for r in reasons:
        enhanced_factors.append(
            DecisionFactor(
                name="Rule Insight",
                value=True,
                detail=r
            )
        )

    # -----------------------------
    # STEP 5: STR + PDF (CRITICAL only)
    # -----------------------------
    str_text = None
    pdf_path = None

    if tier == "CRITICAL":
        str_text = generate_str(
            entity_id=transaction.source_account_id,
            risk_score=score,
            tier=tier,
            reasons=reasons,
            transaction_summary=transaction.dict()
        )

        pdf_path = render_pdf(
            entity_id=transaction.source_account_id,
            risk_score=score,
            tier=tier,
            reasons=reasons,
            str_text=str_text
        )

    # -----------------------------
    # STEP 6: Recommended action
    # -----------------------------
    if tier == "CRITICAL":
        action = "BLOCK"
    elif tier == "HIGH":
        action = "REVIEW"
    elif tier == "MEDIUM":
        action = "MONITOR"
    else:
        action = "ALLOW"

    # -----------------------------
    # STEP 7: Return UPDATED response
    # -----------------------------
    return DecisionResponse(
        transaction_id=base_response.transaction_id,
        source_account_id=base_response.source_account_id,
        recipient_account_id=base_response.recipient_account_id,

        # ML outputs (keep original)
        gnn_probability=gnn_score,
        source_account_probability=base_response.source_account_probability,
        recipient_account_probability=base_response.recipient_account_probability,
        subgraph_probability=base_response.subgraph_probability,

        # Rule engine
        rule_flags=rule_flags,
        rule_matches=rule_matches,

        # 🔥 Updated scoring
        composite_score=score,
        risk_tier=tier,
        recommended_action=action,

        # Impact
        affected_accounts=base_response.affected_accounts,

        # 🔥 Enhanced explainability
        top_factors=enhanced_factors,

        # 🔥 NEW features
        str_report=str_text,
        pdf_path=pdf_path,
    )
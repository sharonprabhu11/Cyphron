"""Shared STR + PDF generation for CRITICAL decisions (HTTP API + ingestion)."""

from __future__ import annotations

from pipeline.compliance.pdf_renderer import render_pdf
from pipeline.compliance.str_generator import generate_str
from pipeline.ingestion.schema import Transaction
from pipeline.models import DecisionResponse


def build_str_and_pdf(base: DecisionResponse, transaction: Transaction) -> tuple[str, str | None]:
    reasons = [factor.detail for factor in base.top_factors if factor.detail]
    if not reasons:
        reasons = ["Composite graph and model signals exceeded the critical risk threshold."]
    str_text = generate_str(
        entity_id=base.source_account_id,
        risk_score=base.composite_score,
        tier=base.risk_tier,
        reasons=reasons,
        transaction_summary=transaction.model_dump(mode="json"),
    )
    pdf_path = render_pdf(
        entity_id=base.source_account_id,
        risk_score=base.composite_score,
        tier=base.risk_tier,
        reasons=reasons,
        str_text=str_text,
    )
    return str_text, pdf_path


def attach_str_pdf_to_response(base: DecisionResponse, transaction: Transaction) -> DecisionResponse:
    str_text, pdf_path = build_str_and_pdf(base, transaction)
    return base.model_copy(update={"str_report": str_text, "pdf_path": pdf_path})

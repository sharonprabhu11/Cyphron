"""
API models for fraud decisioning.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DecisionFactor(BaseModel):
    name: str
    value: float | bool | str
    detail: str


class DecisionResponse(BaseModel):
    transaction_id: str
    source_account_id: str
    recipient_account_id: str

    # -----------------------------
    # ML outputs
    # -----------------------------
    gnn_probability: float
    source_account_probability: float
    recipient_account_probability: float
    subgraph_probability: float

    # -----------------------------
    # Rule engine
    # -----------------------------
    rule_flags: list[str] = Field(default_factory=list)
    rule_matches: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)

    # -----------------------------
    # Final scoring
    # -----------------------------
    composite_score: float
    risk_tier: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recommended_action: str

    # -----------------------------
    # Impact
    # -----------------------------
    affected_accounts: list[str] = Field(default_factory=list)

    # -----------------------------
    # Explainability
    # -----------------------------
    top_factors: list[DecisionFactor] = Field(default_factory=list)

  
    str_report: Optional[str] = None
    pdf_path: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    neo4j_connected: bool
    model_loaded: bool
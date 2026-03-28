"""
Composite risk scoring for the decision API.
"""

from __future__ import annotations


RULE_WEIGHTS = {
    "fan_out": 0.14,
    "structuring": 0.12,
    "shared_device": 0.10,
    "layering": 0.22,
}

ACTION_BY_TIER = {
    "LOW": "ALLOW_AND_AUDIT",
    "MEDIUM": "STEP_UP_AUTH",
    "HIGH": "SOFT_BLOCK_AND_REVIEW",
    "CRITICAL": "HARD_BLOCK_AND_FREEZE_CLUSTER",
}


def composite_score(*, gnn_probability: float, rule_flags: list[str]) -> dict[str, str | float]:
    """
    Hybrid score aligned with the report: GNN is the primary signal and
    structural graph rules add deterministic boosts.
    """

    gnn_component = 0.65 * max(0.0, min(1.0, float(gnn_probability)))
    rule_component = sum(RULE_WEIGHTS.get(flag, 0.0) for flag in set(rule_flags))
    score = min(1.0, gnn_component + rule_component)

    if score >= 0.85 or ("layering" in rule_flags and "fan_out" in rule_flags):
        risk_tier = "CRITICAL"
    elif score >= 0.60 or gnn_probability >= 0.90:
        risk_tier = "HIGH"
    elif score >= 0.40:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"

    return {
        "score": score,
        "risk_tier": risk_tier,
        "recommended_action": ACTION_BY_TIER[risk_tier],
    }

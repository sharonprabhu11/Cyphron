"""
Lightweight decision explanations for the hackathon backend.
"""

from __future__ import annotations

from pipeline.models import DecisionFactor


RULE_DESCRIPTIONS = {
    "fan_out": "source account distributed funds to many recipients within the live time window",
    "structuring": "source account split value into repeated near-threshold transfers",
    "shared_device": "multiple linked accounts were operated from the same device footprint",
    "layering": "funds moved through a multi-hop chain that matches laundering behavior",
}


def explain_decision(
    *,
    source_account_probability: float,
    recipient_account_probability: float,
    subgraph_probability: float,
    gnn_probability: float,
    rule_flags: list[str],
) -> list[DecisionFactor]:
    factors: list[tuple[float, DecisionFactor]] = [
        (
            float(gnn_probability),
            DecisionFactor(
                name="gnn_cluster_risk",
                value=round(float(gnn_probability), 4),
                detail="GraphSAGE cluster risk derived from the source, recipient, and nearby accounts.",
            ),
        ),
        (
            float(source_account_probability),
            DecisionFactor(
                name="source_account_risk",
                value=round(float(source_account_probability), 4),
                detail="Risk attached to the sender account in the trained account graph.",
            ),
        ),
        (
            float(recipient_account_probability),
            DecisionFactor(
                name="recipient_account_risk",
                value=round(float(recipient_account_probability), 4),
                detail="Risk attached to the recipient account in the trained account graph.",
            ),
        ),
        (
            float(subgraph_probability),
            DecisionFactor(
                name="subgraph_risk",
                value=round(float(subgraph_probability), 4),
                detail="Neighborhood-level risk around the accounts involved in this transaction.",
            ),
        ),
    ]

    for flag in rule_flags:
        factors.append(
            (
                1.0,
                DecisionFactor(
                    name=flag,
                    value=True,
                    detail=RULE_DESCRIPTIONS.get(flag, "Structural graph rule triggered."),
                ),
            )
        )

    factors.sort(key=lambda item: item[0], reverse=True)
    return [factor for _, factor in factors[:3]]

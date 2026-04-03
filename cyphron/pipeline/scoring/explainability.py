"""
Lightweight decision explanations for the hackathon backend.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from pipeline.config import SHAP_BACKGROUND_PATH, SHAP_SURROGATE_PATH
from pipeline.models import DecisionFactor

try:
    import shap
except Exception:  # pragma: no cover - optional dependency
    shap = None  # type: ignore


RULE_DESCRIPTIONS = {
    "fan_out": "source account distributed funds to many recipients within the live time window",
    "structuring": "source account split value into repeated near-threshold transfers",
    "shared_device": "multiple linked accounts were operated from the same device footprint",
    "layering": "funds moved through a multi-hop chain that matches laundering behavior",
}

_SURROGATE_MODEL = None
_SHAP_EXPLAINER = None


def _load_surrogate():
    global _SURROGATE_MODEL, _SHAP_EXPLAINER
    if _SURROGATE_MODEL is not None:
        return _SURROGATE_MODEL, _SHAP_EXPLAINER

    model_path = Path(SHAP_SURROGATE_PATH)
    if not model_path.exists():
        return None, None

    with model_path.open("rb") as handle:
        _SURROGATE_MODEL = pickle.load(handle)

    if shap is not None:
        background_path = Path(SHAP_BACKGROUND_PATH)
        if background_path.exists():
            background = np.load(background_path)
            _SHAP_EXPLAINER = shap.LinearExplainer(_SURROGATE_MODEL, background)
    return _SURROGATE_MODEL, _SHAP_EXPLAINER


def _feature_factors(
    *,
    feature_names: list[str] | None,
    focal_features: np.ndarray | None,
    top_k: int = 3,
) -> list[tuple[float, DecisionFactor]]:
    if feature_names is None or focal_features is None:
        return []

    surrogate, explainer = _load_surrogate()
    if surrogate is None:
        return []

    sample = np.asarray(focal_features, dtype=np.float32).reshape(1, -1)
    contributions: np.ndarray | None = None
    if explainer is not None:
        shap_values = explainer(sample)
        values = np.asarray(shap_values.values)
        if values.ndim == 3:
            contributions = values[0, :, -1]
        elif values.ndim == 2:
            contributions = values[0]
    elif hasattr(surrogate, "coef_"):
        contributions = np.asarray(surrogate.coef_[0]) * sample[0]

    if contributions is None:
        return []

    ranked = np.argsort(np.abs(contributions))[::-1][:top_k]
    factors: list[tuple[float, DecisionFactor]] = []
    for index in ranked:
        impact = float(contributions[index])
        direction = "increased" if impact >= 0 else "reduced"
        factors.append(
            (
                abs(impact),
                DecisionFactor(
                    name=str(feature_names[index]),
                    value=round(float(sample[0, index]), 4),
                    detail=f"SHAP estimated that {feature_names[index]} {direction} the fraud score by {abs(impact):.4f}.",
                ),
            )
        )
    return factors


def explain_decision(
    *,
    source_account_probability: float,
    recipient_account_probability: float,
    subgraph_probability: float,
    gnn_probability: float,
    rule_flags: list[str],
    feature_names: list[str] | None = None,
    focal_features: np.ndarray | None = None,
) -> list[DecisionFactor]:
    score_factors: list[tuple[float, DecisionFactor]] = [
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

    feature_factors = _feature_factors(
        feature_names=feature_names,
        focal_features=focal_features,
        top_k=3,
    )

    rule_factors: list[tuple[float, DecisionFactor]] = []
    for flag in rule_flags:
        rule_factors.append(
            (
                1.0,
                DecisionFactor(
                    name=flag,
                    value=True,
                    detail=RULE_DESCRIPTIONS.get(flag, "Structural graph rule triggered."),
                ),
            )
        )

    score_factors.sort(key=lambda item: item[0], reverse=True)
    rule_factors.sort(key=lambda item: item[0], reverse=True)
    feature_factors.sort(key=lambda item: item[0], reverse=True)

    selected: list[DecisionFactor] = []
    seen_names: set[str] = set()

    def add_factor(item: tuple[float, DecisionFactor] | None) -> None:
        if item is None:
            return
        _, factor = item
        if factor.name in seen_names:
            return
        seen_names.add(factor.name)
        selected.append(factor)

    add_factor(score_factors[0] if score_factors else None)
    for item in rule_factors[:2]:
        add_factor(item)
    add_factor(feature_factors[0] if feature_factors else None)

    remaining = score_factors[1:] + feature_factors[1:] + rule_factors[2:]
    remaining.sort(key=lambda item: item[0], reverse=True)
    for item in remaining:
        if len(selected) >= 5:
            break
        add_factor(item)

    return selected

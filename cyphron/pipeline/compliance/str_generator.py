"""
STR (Suspicious Transaction Report) generator with Gemini fallback behavior.
"""

from __future__ import annotations

import os
from typing import Any


def _fallback_report(
    *,
    entity_id: str,
    risk_score: float,
    tier: str,
    reasons: list[str],
    transaction_summary: dict[str, Any] | None = None,
    mode: str = "Fallback",
) -> str:
    summary_lines = []
    if transaction_summary:
        for key, value in transaction_summary.items():
            summary_lines.append(f"- {key}: {value}")

    reasons_text = "\n".join(f"- {reason}" for reason in reasons) or "- No rule reasons available"
    summary_text = "\n".join(summary_lines) if summary_lines else "- Not available"

    return (
        f"STR Report ({mode})\n\n"
        f"Entity: {entity_id}\n"
        f"Risk Score: {risk_score:.4f}\n"
        f"Tier: {tier}\n\n"
        f"Reasons:\n{reasons_text}\n\n"
        f"Transaction Summary:\n{summary_text}\n\n"
        "Automated system detected suspicious activity and recommends analyst review."
    )


def generate_str(
    entity_id: str,
    risk_score: float,
    tier: str,
    reasons: list[str],
    transaction_summary: dict[str, Any] | None = None,
) -> str:
    """
    Generate a Suspicious Transaction Report narrative.

    If Gemini or its API key is unavailable, return a deterministic fallback
    narrative so the backend can still respond safely.
    """

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return _fallback_report(
            entity_id=entity_id,
            risk_score=risk_score,
            tier=tier,
            reasons=reasons,
            transaction_summary=transaction_summary,
        )

    try:
        import google.generativeai as genai
    except Exception as exc:
        print(f"Gemini SDK unavailable, using fallback STR: {exc}", flush=True)
        return _fallback_report(
            entity_id=entity_id,
            risk_score=risk_score,
            tier=tier,
            reasons=reasons,
            transaction_summary=transaction_summary,
            mode="SDK Fallback",
        )

    try:
        genai.configure(api_key=gemini_api_key)
        prompt = f"""
You are a financial fraud analyst generating a Suspicious Transaction Report (STR).

Write a professional, regulator-ready report.

DETAILS:
- Entity ID: {entity_id}
- Risk Score: {risk_score:.4f}
- Risk Tier: {tier}

RISK FACTORS:
{chr(10).join("- " + reason for reason in reasons)}

TRANSACTION SUMMARY:
{transaction_summary if transaction_summary else "Not available"}

INSTRUCTIONS:
- Explain the suspicious pattern clearly
- Describe the fund movement where possible
- Mention coordination signals such as fan-out, structuring, shared devices, or layering
- Keep the tone formal and compliance-ready
- End with a recommended action
"""
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        if getattr(response, "text", None):
            return response.text
        return _fallback_report(
            entity_id=entity_id,
            risk_score=risk_score,
            tier=tier,
            reasons=reasons,
            transaction_summary=transaction_summary,
            mode="Empty Gemini Response",
        )
    except Exception as exc:
        print(f"Gemini generation failed, using fallback STR: {exc}", flush=True)
        return _fallback_report(
            entity_id=entity_id,
            risk_score=risk_score,
            tier=tier,
            reasons=reasons,
            transaction_summary=transaction_summary,
            mode="Error Fallback",
        )

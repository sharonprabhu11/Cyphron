"""
STR (Suspicious Transaction Report) generator using Gemini API.
"""

from __future__ import annotations

import os
import google.generativeai as genai


# -----------------------------
# Setup Gemini
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def generate_str(
    entity_id: str,
    risk_score: float,
    tier: str,
    reasons: list[str],
    transaction_summary: dict | None = None
) -> str:
    """
    Generate a Suspicious Transaction Report (STR).

    Args:
        entity_id: Account / entity identifier
        risk_score: Final risk score
        tier: Risk tier (LOW/MEDIUM/HIGH/CRITICAL)
        reasons: List of risk factors
        transaction_summary: Optional transaction info

    Returns:
        STR narrative (string)
    """

    # -----------------------------
    # Fallback if API key missing
    # -----------------------------
    if not GEMINI_API_KEY:
        return f"""
        STR Report (Fallback)

        Entity: {entity_id}
        Risk Score: {risk_score}
        Tier: {tier}

        Reasons:
        {", ".join(reasons)}

        This activity is flagged as suspicious due to abnormal transaction behavior.
        """

    try:
        # -----------------------------
        # Build prompt
        # -----------------------------
        prompt = f"""
You are a financial fraud analyst generating a Suspicious Transaction Report (STR).

Write a professional, regulator-ready report.

DETAILS:
- Entity ID: {entity_id}
- Risk Score: {risk_score:.2f}
- Risk Tier: {tier}

RISK FACTORS:
{chr(10).join(["- " + r for r in reasons])}

TRANSACTION SUMMARY:
{transaction_summary if transaction_summary else "Not available"}

INSTRUCTIONS:
- Explain the suspicious pattern clearly
- Describe how funds are moving (if applicable)
- Mention coordination behavior (fan-out, velocity, layering)
- Keep tone formal and compliance-ready
- Recommend action (freeze, investigate, monitor)
"""

        # -----------------------------
        # Call Gemini
        # -----------------------------
        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        print(f"⚠️ Gemini error: {e}")

        # -----------------------------
        # Fallback response
        # -----------------------------
        return f"""
        STR Report (Error Fallback)

        Entity: {entity_id}
        Risk Score: {risk_score}
        Tier: {tier}

        Reasons:
        {", ".join(reasons)}

        Automated system detected suspicious activity.
        Further manual investigation is recommended.
        """
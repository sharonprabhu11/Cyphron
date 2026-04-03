"""
STR (Suspicious Transaction Report) generator with Gemini fallback behavior.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# cyphron/.env — same root as pipeline/ (str_generator lives in pipeline/compliance/)
_CYPHRON_ROOT = Path(__file__).resolve().parents[2]


def _ensure_dotenv() -> None:
    """So GEMINI_API_KEY is visible even if this module imported before pipeline.config."""
    try:
        from dotenv import load_dotenv

        load_dotenv(_CYPHRON_ROOT / ".env", override=False)
    except Exception:
        pass


def _gemini_api_key() -> str | None:
    _ensure_dotenv()
    raw = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not raw:
        print("STR Gemini: GEMINI_API_KEY is missing or empty after loading .env", flush=True)
        return None
    low = raw.lower()
    if low in ("changeme", "xxx", "your-api-key", "your_key_here") or low.startswith("your_"):
        print("STR Gemini: GEMINI_API_KEY looks like a placeholder; set a real key in cyphron/.env", flush=True)
        return None
    return raw


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


def _candidate_debug(response: Any) -> str:
    try:
        c0 = response.candidates[0]
        fr = getattr(c0, "finish_reason", None)
        ratings = getattr(c0, "safety_ratings", None)
        return f"finish_reason={fr!r} safety_ratings={ratings!r}"
    except Exception as exc:
        return f"candidates unavailable ({exc!r})"


def _extract_response_text(response: Any) -> str | None:
    """Avoid relying on response.text alone — blocked outputs raise ValueError."""
    try:
        t = response.text
        if t and str(t).strip():
            return str(t).strip()
    except ValueError as exc:
        print(f"STR Gemini: response.text blocked/empty ({exc!s}); {_candidate_debug(response)}", flush=True)
    except Exception as exc:
        print(f"STR Gemini: response.text error ({exc!s})", flush=True)

    try:
        c0 = response.candidates[0]
        parts = getattr(getattr(c0, "content", None), "parts", None) or []
        chunks: list[str] = []
        for p in parts:
            txt = getattr(p, "text", None)
            if txt:
                chunks.append(txt)
        out = "".join(chunks).strip()
        if out:
            return out
    except Exception as exc:
        print(f"STR Gemini: could not read candidate parts ({exc!s})", flush=True)
    return None


def _default_model_candidates() -> list[str]:
    env_model = (os.getenv("GEMINI_MODEL") or "").strip()
    if env_model:
        return [env_model]
    return [
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash",
        "llama-3.3-70b-versatile"
    ]


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

    gemini_api_key = _gemini_api_key()
    if not gemini_api_key:
        return _fallback_report(
            entity_id=entity_id,
            risk_score=risk_score,
            tier=tier,
            reasons=reasons,
            transaction_summary=transaction_summary,
        )

    print(f"STR Gemini: generate_str() running for entity={entity_id!r} tier={tier!r}", flush=True)

    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmBlockThreshold, HarmCategory
    except Exception as exc:
        print(f"STR Gemini: SDK import failed: {exc!s}", flush=True)
        return _fallback_report(
            entity_id=entity_id,
            risk_score=risk_score,
            tier=tier,
            reasons=reasons,
            transaction_summary=transaction_summary,
            mode="SDK Fallback",
        )

    safety_settings = [
        {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
        {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
        {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
        {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    ]

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

    genai.configure(api_key=gemini_api_key)
    last_error: str | None = None

    for model_name in _default_model_candidates():
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                safety_settings=safety_settings,
            )
            text = _extract_response_text(response)
            if text:
                print(f"STR Gemini: OK model={model_name} chars={len(text)}", flush=True)
                return text
            last_error = f"model={model_name} empty; {_candidate_debug(response)}"
            print(f"STR Gemini: {last_error}", flush=True)
        except Exception as exc:
            last_error = f"model={model_name} error={exc!s}"
            print(f"STR Gemini: {last_error}", flush=True)
            continue

    print(f"STR Gemini: all models failed (last={last_error}); using template fallback.", flush=True)
    return _fallback_report(
        entity_id=entity_id,
        risk_score=risk_score,
        tier=tier,
        reasons=reasons,
        transaction_summary=transaction_summary,
        mode="Error Fallback",
    )

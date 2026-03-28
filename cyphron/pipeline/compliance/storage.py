"""
Firestore-backed storage helpers for decisions and alerts.
"""

from __future__ import annotations

from typing import Any

from firebase_admin import firestore
from google.cloud.firestore import SERVER_TIMESTAMP

from pipeline.db.firestore import init_firestore
from pipeline.ingestion.schema import Transaction
from pipeline.models import DecisionResponse


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def store_decision_result(
    transaction: Transaction,
    decision: DecisionResponse,
) -> dict[str, str] | None:
    """
    Persist the evaluated transaction plus its fraud decision to Firestore.

    Returns Firestore document ids when the write succeeds. Returns ``None`` if
    Firestore is unavailable so decisioning can continue without storage.
    """

    try:
        init_firestore()
        db = firestore.client()
    except Exception as exc:
        print(f"Firestore unavailable, skipping storage: {exc}", flush=True)
        return None

    transaction_doc_id = transaction.transaction_id
    alert_doc_id = f"alert_{transaction.transaction_id}"

    transaction_payload = {
        **transaction.model_dump(),
        "source_account_id": decision.source_account_id,
        "recipient_account_id": decision.recipient_account_id,
        "decision_ref": alert_doc_id,
        "stored_at": SERVER_TIMESTAMP,
    }

    alert_payload = {
        "alert_id": alert_doc_id,
        "transaction_id": transaction.transaction_id,
        "source_account_id": decision.source_account_id,
        "recipient_account_id": decision.recipient_account_id,
        "amount": float(transaction.amount),
        "currency": transaction.currency,
        "channel": transaction.channel,
        "risk_score": float(decision.composite_score),
        "risk_tier": decision.risk_tier,
        "recommended_action": decision.recommended_action,
        "gnn_probability": float(decision.gnn_probability),
        "rule_flags": decision.rule_flags,
        "rule_matches": _json_safe(decision.rule_matches),
        "affected_accounts": decision.affected_accounts,
        "top_factors": [factor.model_dump() for factor in decision.top_factors],
        "str_report": decision.str_report,
        "pdf_path": decision.pdf_path,
        "status": "open" if decision.risk_tier in {"HIGH", "CRITICAL"} else "logged",
        "created_at": SERVER_TIMESTAMP,
        "updated_at": SERVER_TIMESTAMP,
    }

    try:
        db.collection("transactions").document(transaction_doc_id).set(
            _json_safe(transaction_payload),
            merge=True,
        )
        db.collection("alerts").document(alert_doc_id).set(
            _json_safe(alert_payload),
            merge=True,
        )
        print(
            f"Firestore stored transaction={transaction_doc_id} alert={alert_doc_id}",
            flush=True,
        )
        return {
            "transaction_doc_id": transaction_doc_id,
            "alert_doc_id": alert_doc_id,
        }
    except Exception as exc:
        print(f"Firestore write failed, skipping storage: {exc}", flush=True)
        return None

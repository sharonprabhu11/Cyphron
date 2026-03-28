"""
Persist transactions and alerts to Firestore after Pub/Sub ingestion + scoring.

Idempotent on transaction_id. Safe no-op if Firestore is unavailable.
"""

from __future__ import annotations

from typing import Any

from google.cloud.firestore import SERVER_TIMESTAMP

from pipeline import config
from pipeline.compliance.str_attach import build_str_and_pdf
from pipeline.ingestion.schema import Transaction
from pipeline.models import DecisionResponse


def _sanitize_doc_id(transaction_id: str) -> str:
    return transaction_id.replace("/", "_").replace(".", "_")[:800] or "unknown"


def _risk_level_ui(tier: str) -> str:
    return {"LOW": "low", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "high"}.get(tier, "medium")


def _try_init_firestore() -> Any | None:
    try:
        from pipeline.db.firestore import init_firestore

        init_firestore()
        from firebase_admin import firestore

        return firestore.client()
    except Exception as exc:
        print(f"Firestore ingest skip: {exc}", flush=True)
        return None


def write_transaction_snapshot(tx: Transaction) -> None:
    db = _try_init_firestore()
    if db is None:
        return
    tid = _sanitize_doc_id(tx.transaction_id)
    payload = tx.model_dump(mode="json")
    if isinstance(payload.get("timestamp"), str):
        pass
    else:
        payload["timestamp"] = tx.timestamp.isoformat() if tx.timestamp else None
    payload["ingested_at"] = SERVER_TIMESTAMP
    try:
        db.collection("transactions").document(tid).set(payload, merge=True)
    except Exception as exc:
        print(f"Firestore transaction write failed: {exc}", flush=True)


def write_alert_and_enrich_decision(
    tx: Transaction,
    decision: DecisionResponse,
) -> DecisionResponse:
    """
    If HIGH/CRITICAL, upsert alerts/{tid}. For CRITICAL, generate STR/PDF and store on doc.
    Returns decision possibly updated with str_report/pdf_path.
    """
    db = _try_init_firestore()
    if db is None:
        return decision

    tid = _sanitize_doc_id(tx.transaction_id)
    alert_id = f"AL-TX-{tid}"[:120]

    str_report: str | None = None
    pdf_path: str | None = None
    if decision.risk_tier == "CRITICAL":
        try:
            str_report, pdf_path = build_str_and_pdf(decision, tx)
            decision = decision.model_copy(update={"str_report": str_report, "pdf_path": pdf_path})
        except Exception as exc:
            print(f"STR/PDF generation failed (ingestion): {exc}", flush=True)

    alert_tiers = {"HIGH", "CRITICAL"}
    if getattr(config, "INGESTION_ALERT_INCLUDE_MEDIUM", False):
        alert_tiers.add("MEDIUM")
    if decision.risk_tier not in alert_tiers:
        return decision

    rule_flags_str = ", ".join(decision.rule_flags) if decision.rule_flags else ""
    cluster_id = tx.cluster_id or (decision.affected_accounts[0] if decision.affected_accounts else "cluster_unknown")

    doc: dict[str, Any] = {
        "alert_id": alert_id,
        "transaction_id": tx.transaction_id,
        "account_id": tx.account_id,
        "amount": float(tx.amount),
        "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
        "channel": str(tx.channel).lower() if tx.channel else "",
        "risk_score": decision.composite_score,
        "risk_level": _risk_level_ui(decision.risk_tier),
        "pipeline_risk_tier": decision.risk_tier,
        "rule_flags": rule_flags_str,
        "behavior_signature": tx.behavior_signature or rule_flags_str[:64] or "ingestion",
        "status": "open",
        "device_fingerprint": tx.device_fingerprint,
        "ip_address": tx.ip_address,
        "cluster_id": cluster_id,
        "top_factors": [f.model_dump() for f in decision.top_factors],
        "updated_at": SERVER_TIMESTAMP,
    }
    if str_report is not None:
        doc["str_report"] = str_report
    if pdf_path is not None:
        doc["pdf_path"] = pdf_path

    try:
        ref = db.collection("alerts").document(tid)
        snap = ref.get()
        if snap.exists:
            doc.pop("alert_id", None)
            ref.set(doc, merge=True)
        else:
            doc["created_at"] = SERVER_TIMESTAMP
            ref.set(doc, merge=True)
    except Exception as exc:
        print(f"Firestore alert write failed: {exc}", flush=True)

    return decision


def persist_ingestion_outcome(tx: Transaction, decision: DecisionResponse | None) -> None:
    """Write transaction row; write alert if decision indicates HIGH/CRITICAL."""
    if not config.env_bool("ENABLE_FIRESTORE_INGEST", True):
        return
    write_transaction_snapshot(tx)
    if decision is not None:
        write_alert_and_enrich_decision(tx, decision)

"""
Graph upsert helpers for transaction events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pipeline.graph.neo4j_client import Neo4jGraphClient


def _normalize_tx_payload(event: dict[str, Any]) -> dict[str, Any]:
    created_at = event.get("timestamp") or event.get("created_at")
    if hasattr(created_at, "astimezone"):
        created_at = created_at.astimezone(timezone.utc).isoformat()
    elif created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()

    user_id = event.get("account_id") or event.get("user_id") or event.get("source_account_id")
    if not user_id:
        raise ValueError("Transaction event must include account_id, user_id, or source_account_id")

    txn_id = event.get("transaction_id") or event.get("id")
    if not txn_id:
        raise ValueError("Transaction event must include transaction_id or id")

    return {
        "txn_id": txn_id,
        "source_account_id": user_id,
        "destination_account_id": event.get("recipient_id") or event.get("destination_account_id") or event.get("merchant_id") or event.get("merchant") or "EXTERNAL_SINK",
        "amount": float(event["amount"]),
        "channel": event["channel"],
        "currency": event.get("currency", "INR"),
        "merchant": event.get("merchant_id") or event.get("merchant"),
        "created_at": created_at,
        "device_id": event.get("device_fingerprint") or event.get("device_id"),
        "ip_address": event.get("ip_address"),
        "phone_number": event.get("phone_number"),
    }


def upsert_transaction_graph(client: "Neo4jGraphClient", event: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_tx_payload(event)
    return client.upsert_transaction_graph(payload)

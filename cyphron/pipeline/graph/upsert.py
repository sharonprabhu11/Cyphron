"""
Graph upsert helpers for transaction events.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from pipeline.graph.neo4j_client import Neo4jGraphClient


def _normalize_tx_payload(event: dict[str, Any]) -> dict[str, Any]:
    created_at = event.get("created_at")
    if hasattr(created_at, "astimezone"):
        created_at = created_at.astimezone(timezone.utc).isoformat()

    user_id = event.get("user_id") or event.get("source_account_id")

    return {
        "txn_id": event["id"],
        "source_account_id": user_id,
        "destination_account_id": event.get("destination_account_id") or event.get("merchant") or "EXTERNAL_SINK",
        "amount": float(event["amount"]),
        "channel": event["channel"],
        "currency": event.get("currency", "INR"),
        "merchant": event.get("merchant"),
        "created_at": created_at,
        "device_id": event.get("device_id"),
        "ip_address": event.get("ip_address"),
        "phone_number": event.get("phone_number"),
    }


def upsert_transaction_graph(client: Neo4jGraphClient, event: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_tx_payload(event)
    return client.upsert_transaction_graph(payload)

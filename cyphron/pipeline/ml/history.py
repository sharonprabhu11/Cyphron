"""
Append-only transaction history used for offline retraining.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pipeline.config import TRAINING_HISTORY_PATH
from pipeline.ingestion.schema import Transaction
from pipeline.models import DecisionResponse


HISTORY_COLUMNS = [
    "transaction_id",
    "account_id",
    "recipient_id",
    "amount",
    "currency",
    "timestamp",
    "channel",
    "tx_type",
    "device_fingerprint",
    "ip_address",
    "phone_number",
    "session_id",
    "geo_hash",
    "merchant_id",
    "entity_id",
    "cluster_id",
    "velocity_score",
    "hop_count",
    "risk_score",
    "rule_flags",
    "behavior_signature",
    "scenario_id",
    "status",
    "str_generated",
    "is_fraud",
]


def _history_row(transaction: Transaction, decision: DecisionResponse) -> dict[str, object]:
    payload = transaction.model_dump()
    payload["risk_score"] = float(decision.composite_score)
    payload["rule_flags"] = json.dumps(decision.rule_flags)
    payload["str_generated"] = bool(decision.str_report)
    payload["scenario_id"] = ""

    row: dict[str, object] = {}
    for column in HISTORY_COLUMNS:
        value = payload.get(column, "")
        if value is None:
            row[column] = ""
        elif hasattr(value, "isoformat"):
            row[column] = value.isoformat()
        else:
            row[column] = value
    return row


def append_training_history(
    transaction: Transaction,
    decision: DecisionResponse,
    *,
    path: str | Path = TRAINING_HISTORY_PATH,
) -> Path:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not history_path.exists() or history_path.stat().st_size == 0

    row = _history_row(transaction, decision)
    with history_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return history_path

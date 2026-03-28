"""
Evaluate Neo4j-backed structural fraud rules for the current transaction.
"""

from __future__ import annotations

from typing import Any

from pipeline.graph.neo4j_client import Neo4jGraphClient
from pipeline.ingestion.schema import Transaction


def _is_shared_device_match(record: dict[str, Any], transaction: Transaction) -> bool:
    accounts = {str(account_id) for account_id in record.get("account_ids", [])}
    return transaction.account_id in accounts or transaction.recipient_id in accounts


def _is_layering_match(record: dict[str, Any], transaction: Transaction) -> bool:
    hop_accounts = {str(account_id) for account_id in record.get("hop_accounts", [])}
    return (
        transaction.account_id == str(record.get("origin_account_id"))
        or transaction.account_id == str(record.get("beneficiary_account_id"))
        or transaction.recipient_id == str(record.get("origin_account_id"))
        or transaction.recipient_id == str(record.get("beneficiary_account_id"))
        or transaction.account_id in hop_accounts
        or transaction.recipient_id in hop_accounts
    )


def score_rules(
    client: Neo4jGraphClient | None,
    transaction: Transaction,
) -> dict[str, list[str] | dict[str, list[dict[str, Any]]]]:
    if client is None:
        return {"rule_flags": [], "rule_matches": {}}

    rule_matches: dict[str, list[dict[str, Any]]] = {}

    fan_out_matches = [
        record
        for record in client.run_fan_out_query(limit=100)
        if str(record.get("account_id")) == transaction.account_id
    ]
    if fan_out_matches:
        rule_matches["fan_out"] = fan_out_matches

    structuring_matches = [
        record
        for record in client.run_structuring_query(limit=100)
        if str(record.get("account_id")) == transaction.account_id
    ]
    if structuring_matches:
        rule_matches["structuring"] = structuring_matches

    shared_device_matches = [
        record
        for record in client.run_shared_device_query(limit=100)
        if _is_shared_device_match(record, transaction)
    ]
    if shared_device_matches:
        rule_matches["shared_device"] = shared_device_matches

    layering_matches = [
        record
        for record in client.run_layering_query(limit=100)
        if _is_layering_match(record, transaction)
    ]
    if layering_matches:
        rule_matches["layering"] = layering_matches

    return {
        "rule_flags": sorted(rule_matches.keys()),
        "rule_matches": rule_matches,
    }

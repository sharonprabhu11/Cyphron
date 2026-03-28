"""
Synthetic transaction generators for the Cyphron simulator and pipeline publisher.
"""

from __future__ import annotations

import csv
import hashlib
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

CHANNELS = ["UPI", "ATM", "WEB", "MOBILE"]
TX_TYPES = ["TRANSFER", "ATM_WITHDRAWAL", "PAYMENT", "WALLET_LOAD"]


def generate_tx_id():
    return "TXN_" + uuid4().hex[:12].upper()


def generate_account():
    return "ACC_" + uuid4().hex[:8].upper()


def generate_device_fingerprint(seed: str):
    return "DEV_" + hashlib.sha256(seed.encode()).hexdigest()[:12].upper()


def generate_ip():
    return f"192.168.1.{random.randint(1, 255)}"


def generate_phone():
    return "+91" + str(random.randint(6000000000, 9999999999))


def generate_session():
    return "SES_" + uuid4().hex[:8].upper()


def generate_timestamp(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _base_transaction(
    *,
    transaction_id: str,
    account_id: str,
    recipient_id: str,
    amount: float,
    timestamp: str,
    channel: str,
    tx_type: str = "TRANSFER",
    device_fingerprint: str,
    ip_address: str,
    phone_number: str | None,
    session_id: str,
    geo_hash: str | None,
    merchant_id: str | None = None,
    entity_id: str | None = None,
    cluster_id: str | None = None,
    velocity_score: float | None = None,
    hop_count: int | None = None,
    risk_score: float | None = None,
    rule_flags: list[str] | None = None,
    behavior_signature: str | None = None,
    scenario_id: str | None = None,
    status: str = "PENDING",
    str_generated: bool = False,
    is_fraud: bool = False,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "recipient_id": recipient_id,
        "amount": round(float(amount), 2),
        "currency": "INR",
        "timestamp": timestamp,
        "channel": channel,
        "tx_type": tx_type,
        "device_fingerprint": device_fingerprint,
        "ip_address": ip_address,
        "phone_number": phone_number,
        "session_id": session_id,
        "geo_hash": geo_hash,
        "merchant_id": merchant_id,
        "entity_id": entity_id or account_id,
        "cluster_id": cluster_id,
        "velocity_score": velocity_score,
        "hop_count": hop_count,
        "risk_score": risk_score,
        "rule_flags": rule_flags or [],
        "behavior_signature": behavior_signature,
        "scenario_id": scenario_id,
        "status": status,
        "str_generated": str_generated,
        "is_fraud": is_fraud,
    }


def generate_normal_tx():
    account_id = generate_account()
    return _base_transaction(
        transaction_id=generate_tx_id(),
        account_id=account_id,
        recipient_id=generate_account(),
        amount=random.uniform(100, 5000),
        timestamp=generate_timestamp(),
        channel=random.choice(CHANNELS),
        device_fingerprint=generate_device_fingerprint(str(random.random())),
        ip_address=generate_ip(),
        phone_number=generate_phone(),
        session_id=generate_session(),
        geo_hash=random.choice(["dr5ru", "dr5rv", "dr5rw"]),
        entity_id=account_id,
        risk_score=0.05,
        behavior_signature="normal",
        scenario_id=f"NORMAL-LIVE-{uuid4().hex[:8].upper()}",
    )


def generate_normal_batch(batch_index: int, *, tx_count: int = 10) -> list[dict[str, object]]:
    scenario_id = f"NORMAL-BATCH-{batch_index:03d}"
    accounts = [generate_account() for _ in range(5)]
    primary_device = generate_device_fingerprint(f"{scenario_id}-device")
    backup_device = generate_device_fingerprint(f"{scenario_id}-backup")
    ip_block = random.randint(10, 200)

    txs: list[dict[str, object]] = []
    for i in range(tx_count):
        src = random.choice(accounts)
        dst_choices = [account for account in accounts if account != src]
        dst = random.choice(dst_choices)
        txs.append(
            _base_transaction(
                transaction_id=generate_tx_id(),
                account_id=src,
                recipient_id=dst,
                amount=random.uniform(500, 18_000),
                timestamp=generate_timestamp((batch_index * 120) + (i * 15)),
                channel=random.choice(CHANNELS),
                device_fingerprint=primary_device if i < (tx_count * 0.7) else backup_device,
                ip_address=f"10.0.{ip_block}.{random.randint(2, 40)}",
                phone_number=generate_phone(),
                session_id=f"SES_{scenario_id}_{i:02d}",
                geo_hash=random.choice(["dr5ru", "dr5rv", "dr5rw"]),
                entity_id=src,
                risk_score=random.choice([0.04, 0.05, 0.06]),
                behavior_signature=random.choice(["salary_flow", "family_transfer", "merchant_payment"]),
                scenario_id=scenario_id,
            )
        )
    return txs


def generate_fanout_fraud(batch_index: int):
    scenario_id = f"FRAUD-FANOUT-{batch_index:03d}"
    base_account = generate_account()
    shared_device = generate_device_fingerprint(f"{scenario_id}-device")
    shared_session = f"SES_{scenario_id}"
    cluster_id = scenario_id

    txs = []
    for i in range(6):
        txs.append(
            _base_transaction(
                transaction_id=generate_tx_id(),
                account_id=base_account,
                recipient_id=generate_account(),
                amount=60_000,
                timestamp=generate_timestamp(i),
                channel=random.choice(CHANNELS),
                device_fingerprint=shared_device,
                ip_address="192.168.1.100",
                phone_number=generate_phone(),
                session_id=shared_session,
                geo_hash="dr5ru",
                entity_id=base_account,
                cluster_id=cluster_id,
                velocity_score=9.5,
                hop_count=1,
                risk_score=random.choice([0.88, 0.91, 0.95]),
                rule_flags=["fan_out"],
                behavior_signature="fanout_ring",
                scenario_id=scenario_id,
                is_fraud=True,
            )
        )
    return txs


def generate_structuring_fraud(batch_index: int):
    scenario_id = f"FRAUD-STRUCT-{batch_index:03d}"
    account = generate_account()
    device = generate_device_fingerprint(f"{scenario_id}-device")
    cluster_id = scenario_id

    txs = []
    for i in range(5):
        txs.append(
            _base_transaction(
                transaction_id=generate_tx_id(),
                account_id=account,
                recipient_id=generate_account(),
                amount=random.choice([49_800, 49_900, 49_750]),
                timestamp=generate_timestamp(i * 10),
                channel="UPI",
                device_fingerprint=device,
                ip_address="192.168.1.200",
                phone_number=generate_phone(),
                session_id="SES_STRUCT01",
                geo_hash="dr5rv",
                entity_id=account,
                cluster_id=cluster_id,
                velocity_score=6.0,
                hop_count=1,
                risk_score=random.choice([0.82, 0.86, 0.9]),
                rule_flags=["structuring"],
                behavior_signature="structuring_pattern",
                scenario_id=scenario_id,
                is_fraud=True,
            )
        )
    return txs


def generate_layering_fraud(batch_index: int):
    scenario_id = f"FRAUD-LAYER-{batch_index:03d}"
    accounts = [generate_account() for _ in range(4)]
    cluster_id = scenario_id
    txs = []
    for index in range(3):
        txs.append(
            _base_transaction(
                transaction_id=generate_tx_id(),
                account_id=accounts[index],
                recipient_id=accounts[index + 1],
                amount=75_000 - (index * 500),
                timestamp=generate_timestamp(index * 15),
                channel=random.choice(["WEB", "MOBILE", "UPI"]),
                device_fingerprint=generate_device_fingerprint(f"layer-{index}"),
                ip_address=f"192.168.2.{100 + index}",
                phone_number=generate_phone(),
                session_id=f"SES_LAYER_{index}",
                geo_hash="dr5rw",
                entity_id=accounts[index],
                cluster_id=cluster_id,
                velocity_score=4.0,
                hop_count=index + 1,
                risk_score=random.choice([0.84, 0.89, 0.93]),
                rule_flags=["layering"],
                behavior_signature="layering_chain",
                scenario_id=scenario_id,
                is_fraud=True,
            )
        )
    return txs


def generate_dataset(
    *,
    normal_count: int = 300,
    fanout_batches: int = 5,
    structuring_batches: int = 5,
    layering_batches: int = 5,
) -> list[dict[str, object]]:
    normal_batches = max(1, normal_count // 10)
    rows: list[dict[str, object]] = []
    for batch_index in range(normal_batches):
        rows.extend(generate_normal_batch(batch_index, tx_count=10))
    for batch_index in range(fanout_batches):
        rows.extend(generate_fanout_fraud(batch_index))
    for batch_index in range(structuring_batches):
        rows.extend(generate_structuring_fraud(batch_index))
    for batch_index in range(layering_batches):
        rows.extend(generate_layering_fraud(batch_index))
    rows.sort(key=lambda row: str(row["timestamp"]))
    return rows


def export_dataset_csv(path: str | Path, **kwargs: int) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_dataset(**kwargs)
    fieldnames = list(rows[0].keys()) if rows else []
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path

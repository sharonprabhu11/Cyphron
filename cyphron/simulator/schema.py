"""
Canonical simulator transaction schema used by ingestion, graphing, and training.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Channel = Literal["UPI", "ATM", "WEB", "MOBILE"]
TxType = Literal["TRANSFER", "ATM_WITHDRAWAL", "PAYMENT", "WALLET_LOAD"]


class Transaction(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier")
    account_id: str
    recipient_id: str
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    timestamp: datetime
    channel: Channel
    tx_type: TxType = "TRANSFER"
    device_fingerprint: str
    ip_address: str
    phone_number: str | None = None
    session_id: str
    geo_hash: str | None = None
    merchant_id: str | None = None
    entity_id: str | None = None
    cluster_id: str | None = None
    velocity_score: float | None = None
    hop_count: int | None = None
    risk_score: float | None = None
    rule_flags: list[str] = Field(default_factory=list)
    behavior_signature: str | None = None
    status: str = "PENDING"
    str_generated: bool = False
    is_fraud: bool = False

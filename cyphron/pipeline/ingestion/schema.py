"""
Ingestion-layer schemas.


"""

from datetime import datetime
from math import isnan
from typing import List, Literal, Optional

from pydantic import BaseModel
from pydantic import field_validator


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    recipient_id: str

    amount: float
    currency: str

    timestamp: datetime
    channel: Literal["UPI", "ATM", "WEB", "MOBILE"]
    tx_type: Literal["TRANSFER", "ATM_WITHDRAWAL", "PAYMENT", "WALLET_LOAD"]

    device_fingerprint: str
    ip_address: str
    phone_number: Optional[str]

    session_id: str
    geo_hash: Optional[str]
    merchant_id: Optional[str]

    entity_id: Optional[str]
    cluster_id: Optional[str]

    velocity_score: Optional[float]
    hop_count: Optional[int]

    risk_score: Optional[float]
    rule_flags: Optional[List[str]]
    behavior_signature: Optional[str]

    status: str
    str_generated: bool
    is_fraud: bool = False

    @field_validator("phone_number", "geo_hash", "merchant_id", "entity_id", "cluster_id", "behavior_signature", mode="before")
    @classmethod
    def _normalize_optional_strings(cls, value):
        if value is None:
            return None
        if value == "":
            return None
        if isinstance(value, float) and isnan(value):
            return None
        return str(value)

    @field_validator("velocity_score", "risk_score", mode="before")
    @classmethod
    def _normalize_optional_floats(cls, value):
        if value is None:
            return None
        if value == "":
            return None
        if isinstance(value, float) and isnan(value):
            return None
        return float(value)

    @field_validator("hop_count", mode="before")
    @classmethod
    def _normalize_optional_int(cls, value):
        if value is None:
            return None
        if value == "":
            return None
        if isinstance(value, float) and isnan(value):
            return None
        return int(value)

    @field_validator("rule_flags", mode="before")
    @classmethod
    def _normalize_rule_flags(cls, value):
        if value is None:
            return []
        if value == "":
            return []
        if isinstance(value, float) and isnan(value):
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped or stripped == "[]":
                return []
            return [flag.strip().strip("'\"") for flag in stripped.strip("[]").split(",") if flag.strip()]
        return [str(value)]

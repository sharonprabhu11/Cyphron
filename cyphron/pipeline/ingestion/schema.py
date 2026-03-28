"""
Ingestion-layer schemas.


"""

from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

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
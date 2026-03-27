"""
Ingestion-layer schemas.

These are placeholders for messages consumed from Pub/Sub.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class IngestedTransaction(BaseModel):
    id: str
    channel: str
    amount: float
    created_at: datetime


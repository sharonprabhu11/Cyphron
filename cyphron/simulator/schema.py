"""
Simulator schema definitions.

This module defines the minimal transaction object shape emitted by the simulator.
No business logic is implemented here yet.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Channel = Literal["upi", "atm", "mobile", "web"]


class Transaction(BaseModel):
    id: str = Field(..., description="Unique transaction identifier")
    channel: Channel
    amount: float
    currency: str = "INR"
    merchant: str
    user_id: str
    created_at: datetime


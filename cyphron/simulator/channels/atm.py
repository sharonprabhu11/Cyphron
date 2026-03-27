"""ATM channel generator placeholder."""

from __future__ import annotations

from datetime import datetime, timezone

from faker import Faker

from simulator.schema import Transaction


fake = Faker()


def generate_transaction() -> Transaction:
    return Transaction(
        id=fake.uuid4(),
        channel="atm",
        amount=round(fake.pyfloat(min_value=100, max_value=20000, right_digits=2), 2),
        merchant=f"ATM-{fake.city()}",
        user_id=fake.uuid4(),
        created_at=datetime.now(timezone.utc),
    )


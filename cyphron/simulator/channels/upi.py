"""UPI channel generator placeholder."""

from __future__ import annotations

from datetime import datetime, timezone

from faker import Faker

from simulator.schema import Transaction


fake = Faker()


def generate_transaction() -> Transaction:
    return Transaction(
        id=fake.uuid4(),
        channel="upi",
        amount=round(fake.pyfloat(min_value=10, max_value=50000, right_digits=2), 2),
        merchant=fake.company(),
        user_id=fake.uuid4(),
        created_at=datetime.now(timezone.utc),
    )


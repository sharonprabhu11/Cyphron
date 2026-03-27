"""
Cyphron Simulator entrypoint.

Minimal working check:
- prints "Simulator started"
- generates and prints one dummy transaction
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
except Exception:  # foundation-only: allow running without installed deps
    def load_dotenv() -> None:  # type: ignore
        return None

# Allow `python simulator/main.py` from repo root on Windows.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from simulator.channels.upi import generate_transaction  # type: ignore # noqa: E402
except Exception:
    generate_transaction = None  # type: ignore


def main() -> None:
    load_dotenv()
    print("Simulator started")

    if generate_transaction is None:
        tx = {
            "id": str(uuid.uuid4()),
            "channel": "upi",
            "amount": 123.45,
            "currency": "INR",
            "merchant": "PLACEHOLDER",
            "user_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        print("Dummy transaction:")
        print(tx)
        print("(Install deps to enable Faker/Pydantic generator: pip install -r requirements.txt)")
        return

    tx = generate_transaction()
    print("Dummy transaction:")
    print(tx.model_dump())


if __name__ == "__main__":
    main()


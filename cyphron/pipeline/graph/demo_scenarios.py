"""
Seedable demo transactions for Neo4j smoke testing.
"""

from __future__ import annotations   
from datetime import datetime, timedelta, timezone

def _iso_at(base_time: datetime, seconds_ago: int) -> str:
    return (base_time - timedelta(seconds=seconds_ago)).astimezone(timezone.utc).isoformat()


def build_demo_transactions(prefix: str) -> list[dict[str, object]]:
    """
    Build a deterministic mule-ring scenario that triggers the current graph queries.

    The scenario includes:
    - one inbound funding event into a hub account
    - one fan-out burst from the hub to six recipients
    - three near-threshold structuring transactions
    - three accounts reusing the same device
    - one 3-hop layering chain
    """

    now = datetime.now(timezone.utc)
    hub = f"{prefix}MULE-HUB-01"
    leaves = [f"{prefix}MULE-LEAF-0{i}" for i in range(1, 7)]
    device = f"{prefix}shared-device"
    ip_address = f"{prefix}shared-ip"

    events: list[dict[str, object]] = [
        {
            "id": f"{prefix}tx-fund-hub",
            "source_account_id": f"{prefix}EXTERNAL-SOURCE-01",
            "destination_account_id": hub,
            "amount": 480000.0,
            "channel": "web",
            "currency": "INR",
            "merchant": "external-fund",
            "created_at": _iso_at(now, 50),
            "device_id": f"{prefix}source-device",
            "ip_address": f"{prefix}source-ip",
            "phone_number": f"{prefix}source-phone",
        },
    ]

    for index, leaf in enumerate(leaves, start=1):
        events.append(
            {
                "id": f"{prefix}tx-fanout-{index:02d}",
                "source_account_id": hub,
                "destination_account_id": leaf,
                "amount": 49_000.0 + index,
                "channel": ["upi", "mobile", "web", "atm", "upi", "web"][index - 1],
                "currency": "INR",
                "merchant": "fanout-demo",
                "created_at": _iso_at(now, 45 - index),
                "device_id": f"{prefix}hub-device",
                "ip_address": f"{prefix}hub-ip",
                "phone_number": f"{prefix}hub-phone",
            }
        )

    for index, leaf in enumerate(leaves[:3], start=1):
        events.append(
            {
                "id": f"{prefix}tx-cashout-{index:02d}",
                "source_account_id": leaf,
                "destination_account_id": f"{prefix}CASHOUT-{index:02d}",
                "amount": 48_500.0 + index,
                "channel": "atm",
                "currency": "INR",
                "merchant": "cashout-demo",
                "created_at": _iso_at(now, 20 - index),
                "device_id": device,
                "ip_address": ip_address,
                "phone_number": f"{prefix}leaf-phone-{index:02d}",
            }
        )

    events.extend(
        [
            {
                "id": f"{prefix}tx-layer-01",
                "source_account_id": f"{prefix}LAYER-ORIGIN-01",
                "destination_account_id": f"{prefix}LAYER-MID-01",
                "amount": 75_000.0,
                "channel": "web",
                "currency": "INR",
                "merchant": "layering-demo",
                "created_at": _iso_at(now, 16),
                "device_id": f"{prefix}layer-origin-device",
                "ip_address": f"{prefix}layer-origin-ip",
                "phone_number": f"{prefix}layer-origin-phone",
            },
            {
                "id": f"{prefix}tx-layer-02",
                "source_account_id": f"{prefix}LAYER-MID-01",
                "destination_account_id": f"{prefix}LAYER-MID-02",
                "amount": 74_500.0,
                "channel": "upi",
                "currency": "INR",
                "merchant": "layering-demo",
                "created_at": _iso_at(now, 12),
                "device_id": f"{prefix}layer-mid-device",
                "ip_address": f"{prefix}layer-mid-ip",
                "phone_number": f"{prefix}layer-mid-phone-1",
            },
            {
                "id": f"{prefix}tx-layer-03",
                "source_account_id": f"{prefix}LAYER-MID-02",
                "destination_account_id": f"{prefix}LAYER-BENEFICIARY-01",
                "amount": 74_000.0,
                "channel": "mobile",
                "currency": "INR",
                "merchant": "layering-demo",
                "created_at": _iso_at(now, 8),
                "device_id": f"{prefix}layer-mid-device-2",
                "ip_address": f"{prefix}layer-mid-ip-2",
                "phone_number": f"{prefix}layer-mid-phone-2",
            },
        ]
    )

    return events

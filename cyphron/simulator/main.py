"""
Cyphron Simulator entrypoint.

Minimal working check:
- prints "Simulator started"
- generates and prints one dummy transaction
"""

import random
import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

# -------------------- CONFIG --------------------
CHANNELS = ["UPI", "ATM", "WEB", "MOBILE"]
TX_TYPES = ["TRANSFER", "ATM_WITHDRAWAL", "PAYMENT", "WALLET_LOAD"]

# -------------------- HELPERS --------------------

def generate_tx_id():
    return "TXN_" + uuid4().hex[:12].upper()

def generate_account():
    return "ACC_" + str(random.randint(100, 999))

def generate_device_fingerprint(seed: str):
    return "DEV_" + hashlib.sha256(seed.encode()).hexdigest()[:12].upper()

def generate_ip():
    return f"192.168.1.{random.randint(1,255)}"

def generate_phone():
    return "+91" + str(random.randint(6000000000, 9999999999))

def generate_session():
    return "SES_" + uuid4().hex[:8].upper()

def generate_timestamp(offset_seconds=0):
    return (datetime.utcnow() + timedelta(seconds=offset_seconds)).isoformat()

# -------------------- NORMAL TRANSACTION --------------------

def generate_normal_tx():
    return {
        "transaction_id": generate_tx_id(),
        "account_id": generate_account(),
        "recipient_id": generate_account(),
        "amount": round(random.uniform(100, 5000), 2),
        "currency": "INR",
        "timestamp": generate_timestamp(),
        "channel": random.choice(CHANNELS),
        "tx_type": "TRANSFER",
        "device_fingerprint": generate_device_fingerprint(str(random.random())),
        "ip_address": generate_ip(),
        "phone_number": generate_phone(),
        "session_id": generate_session(),
        "geo_hash": random.choice(["dr5ru", "dr5rv", "dr5rw"]),
        "merchant_id": None,

        # --- Empty (filled later in pipeline) ---
        "entity_id": None,
        "cluster_id": None,
        "velocity_score": None,
        "hop_count": None,
        "risk_score": None,
        "rule_flags": None,
        "behavior_signature": None,
        "status": "PENDING",
        "str_generated": False
    }

# -------------------- FRAUD: FAN-OUT --------------------

def generate_fanout_fraud():
    base_account = generate_account()
    shared_device = generate_device_fingerprint("fraud_device")
    shared_session = "SES_FRAUD01"

    txs = []
    for i in range(6):
        txs.append({
            "transaction_id": generate_tx_id(),
            "account_id": base_account,
            "recipient_id": generate_account(),
            "amount": 60000,
            "currency": "INR",
            "timestamp": generate_timestamp(i),  # burst pattern
            "channel": random.choice(CHANNELS),
            "tx_type": "TRANSFER",
            "device_fingerprint": shared_device,
            "ip_address": "192.168.1.100",
            "phone_number": generate_phone(),
            "session_id": shared_session,
            "geo_hash": "dr5ru",
            "merchant_id": None,

            "entity_id": None,
            "cluster_id": None,
            "velocity_score": None,
            "hop_count": None,
            "risk_score": None,
            "rule_flags": None,
            "behavior_signature": None,
            "status": "PENDING",
            "str_generated": False
        })
    return txs

# -------------------- FRAUD: STRUCTURING --------------------

def generate_structuring_fraud():
    account = generate_account()
    device = generate_device_fingerprint("struct_device")

    txs = []
    for i in range(5):
        txs.append({
            "transaction_id": generate_tx_id(),
            "account_id": account,
            "recipient_id": generate_account(),
            "amount": random.choice([49800, 49900, 49750]),
            "currency": "INR",
            "timestamp": generate_timestamp(i * 10),
            "channel": "UPI",
            "tx_type": "TRANSFER",
            "device_fingerprint": device,
            "ip_address": "192.168.1.200",
            "phone_number": generate_phone(),
            "session_id": "SES_STRUCT01",
            "geo_hash": "dr5rv",
            "merchant_id": None,

            "entity_id": None,
            "cluster_id": None,
            "velocity_score": None,
            "hop_count": None,
            "risk_score": None,
            "rule_flags": None,
            "behavior_signature": None,
            "status": "PENDING",
            "str_generated": False
        })
    return txs

# -------------------- MAIN --------------------

if __name__ == "__main__":
    print("---- NORMAL ----")
    for _ in range(3):
        print(generate_normal_tx())

    print("\n---- FANOUT FRAUD ----")
    for tx in generate_fanout_fraud():
        print(tx)

    print("\n---- STRUCTURING FRAUD ----")
    for tx in generate_structuring_fraud():
        print(tx)
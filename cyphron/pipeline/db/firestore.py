"""Firestore initialization and seed documents."""

from __future__ import annotations

import os

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import SERVER_TIMESTAMP

from pipeline import config

_DUMMY_DOC_ID = "cyphron_db_seed"


def init_firestore() -> None:
    if config.GOOGLE_APPLICATION_CREDENTIALS:
        os.environ.setdefault(
            "GOOGLE_APPLICATION_CREDENTIALS",
            config.GOOGLE_APPLICATION_CREDENTIALS,
        )
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        project = config.GCP_PROJECT_ID
        if project:
            firebase_admin.initialize_app(cred, {"projectId": project})
        else:
            firebase_admin.initialize_app(cred)
    print("Firestore initialized", flush=True)


def create_dummy_collections() -> None:
    db = firestore.client()

    alerts_data = {
        "alert_id": "alert_seed_001",
        "account_id": "acct_seed_001",
        "amount": 1250.50,
        "timestamp": SERVER_TIMESTAMP,
        "channel": "online",
        "risk_score": 0.72,
        "risk_level": "medium",
        "rule_flags": "velocity,geo",
        "behavior_signature": "sig_seed_abc",
        "status": "open",
        "device_fingerprint": "fp_seed_xyz",
        "ip_address": "203.0.113.10",
        "cluster_id": "cluster_seed_01",
        "created_at": SERVER_TIMESTAMP,
        "updated_at": SERVER_TIMESTAMP,
    }

    cases_data = {
        "case_id": "case_seed_001",
        "alert_ids": ["alert_seed_001"],
        "cluster_id": "cluster_seed_01",
        "status": "investigating",
        "analyst_notes": "seed document",
        "created_at": SERVER_TIMESTAMP,
    }

    transactions_data = {
        "transaction_id": "tx_seed_001",
        "account_id": "acct_seed_001",
        "amount": 499.99,
        "timestamp": SERVER_TIMESTAMP,
        "channel": "card",
    }

    seeds = [
        ("alerts", alerts_data),
        ("cases", cases_data),
        ("transactions", transactions_data),
    ]

    for collection_name, payload in seeds:
        doc_ref = db.collection(collection_name).document(_DUMMY_DOC_ID)
        if doc_ref.get().exists:
            continue
        doc_ref.set(payload)

    print("Firestore collections ready", flush=True)

"""
Central configuration for the pipeline backend.

Loads environment variables (no validation-heavy logic yet).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_CYPHRON_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_CYPHRON_ROOT / ".env")


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


GOOGLE_APPLICATION_CREDENTIALS = env("GOOGLE_APPLICATION_CREDENTIALS", "")
BIGQUERY_DATASET = env("BIGQUERY_DATASET", "cyphron_dw")

NEO4J_URI = env("NEO4J_URI")
NEO4J_USER = env("NEO4J_USER")
NEO4J_PASSWORD = env("NEO4J_PASSWORD")

REDIS_URL = env("REDIS_URL", "redis://localhost:6379")

GCP_PROJECT_ID = env("GCP_PROJECT_ID")
PUBSUB_TOPIC = env("PUBSUB_TOPIC")
PUBSUB_SUBSCRIPTION = env("PUBSUB_SUBSCRIPTION")

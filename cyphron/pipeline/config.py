"""
Central configuration for the pipeline backend.

Loads environment variables (no validation-heavy logic yet).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


NEO4J_URI = env("NEO4J_URI")
NEO4J_USER = env("NEO4J_USER")
NEO4J_PASSWORD = env("NEO4J_PASSWORD")
NEO4J_DATABASE = env("NEO4J_DATABASE")

REDIS_URL = env("REDIS_URL", "redis://localhost:6379")

GCP_PROJECT_ID = env("GCP_PROJECT_ID")
PUBSUB_TOPIC = env("PUBSUB_TOPIC")
PUBSUB_SUBSCRIPTION = env("PUBSUB_SUBSCRIPTION")

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


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


GOOGLE_APPLICATION_CREDENTIALS = env("GOOGLE_APPLICATION_CREDENTIALS", "")
BIGQUERY_DATASET = env("BIGQUERY_DATASET", "cyphron_dw")

NEO4J_URI = env("NEO4J_URI")
NEO4J_USER = env("NEO4J_USER")
NEO4J_PASSWORD = env("NEO4J_PASSWORD")
NEO4J_DATABASE = env("NEO4J_DATABASE")

REDIS_URL = env("REDIS_URL", "redis://localhost:6379")

GCP_PROJECT_ID = env("GCP_PROJECT_ID")
PUBSUB_TOPIC = env("PUBSUB_TOPIC")
PUBSUB_SUBSCRIPTION = env("PUBSUB_SUBSCRIPTION")
FRONTEND_ORIGINS = env(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

MODEL_ARTIFACT_PATH = env(
    "GRAPH_MODEL_PATH",
    str(_CYPHRON_ROOT / "pipeline" / "ml" / "artifacts" / "graphsage_model.pt"),
)
SHAP_SURROGATE_PATH = env(
    "SHAP_SURROGATE_PATH",
    str(_CYPHRON_ROOT / "pipeline" / "ml" / "artifacts" / "shap_surrogate.pkl"),
)
SHAP_BACKGROUND_PATH = env(
    "SHAP_BACKGROUND_PATH",
    str(_CYPHRON_ROOT / "pipeline" / "ml" / "artifacts" / "shap_background.npy"),
)
PROCESSED_GRAPH_PATH = env(
    "PROCESSED_GRAPH_PATH",
    str(_CYPHRON_ROOT / "ml_training" / "data" / "processed_graph.npz"),
)
TRAINING_HISTORY_PATH = env(
    "TRAINING_HISTORY_PATH",
    str(_CYPHRON_ROOT / "ml_training" / "data" / "transactions.csv"),
)
ENABLE_GCP_STARTUP = env_bool("ENABLE_GCP_STARTUP", True)

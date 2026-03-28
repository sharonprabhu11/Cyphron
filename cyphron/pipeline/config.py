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

# When true, ingestion also writes `alerts` for MEDIUM tier (noisier; useful for local demos).
INGESTION_ALERT_INCLUDE_MEDIUM = env_bool("INGESTION_ALERT_INCLUDE_MEDIUM", False)


def cors_origins() -> list[str]:
    raw = env("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000") or ""
    return [part.strip() for part in raw.split(",") if part.strip()]


def firestore_analytics_doc_cap() -> int:
    """Max documents read per collection scan in dashboard analytics (saves quota)."""
    raw = env("FIRESTORE_ANALYTICS_DOC_CAP", "400")
    try:
        return max(50, min(2000, int(raw or "400")))
    except ValueError:
        return 400


def firestore_list_alerts_fetch_cap() -> int:
    """Max alert documents loaded when listing (before filter/sort in memory)."""
    raw = env("FIRESTORE_LIST_ALERTS_FETCH_CAP", "280")
    try:
        return max(50, min(500, int(raw or "280")))
    except ValueError:
        return 280


def dashboard_firestore_cache_seconds() -> float:
    """TTL for identical dashboard REST responses (0 = disable)."""
    raw = env("DASHBOARD_FIRESTORE_CACHE_SECONDS", "20")
    try:
        return max(0.0, float(raw or "20"))
    except ValueError:
        return 20.0


def enable_firestore_realtime() -> bool:
    """Firestore snapshot listeners + WebSocket push (single API instance)."""
    return env_bool("ENABLE_FIRESTORE_REALTIME", True)


def firestore_listener_alert_limit() -> int:
    raw = env("FIRESTORE_LISTENER_ALERT_LIMIT", "180")
    try:
        return max(20, min(500, int(raw or "180")))
    except ValueError:
        return 180


def firestore_listener_transaction_limit() -> int:
    raw = env("FIRESTORE_LISTENER_TRANSACTION_LIMIT", "120")
    try:
        return max(20, min(500, int(raw or "120")))
    except ValueError:
        return 120


def ws_broadcast_debounce_ms() -> int:
    raw = env("WS_BROADCAST_DEBOUNCE_MS", "400")
    try:
        return max(50, min(5000, int(raw or "400")))
    except ValueError:
        return 400


def ws_max_connections() -> int:
    raw = env("WS_MAX_CONNECTIONS", "80")
    try:
        return max(1, min(500, int(raw or "80")))
    except ValueError:
        return 80

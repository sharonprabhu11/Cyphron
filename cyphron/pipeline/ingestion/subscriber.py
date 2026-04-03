from __future__ import annotations

import json
import os

from google.cloud import pubsub_v1

from pipeline import config
from pipeline.db.ingestion_store import persist_ingestion_outcome
from pipeline.graph.neo4j_client import initialize_neo4j
from pipeline.graph.upsert import upsert_transaction_graph
from pipeline.ingestion.decision_holder import get_ingestion_decision_service
from pipeline.ingestion.schema import Transaction

# Use .env path even if the shell already had GOOGLE_APPLICATION_CREDENTIALS (setdefault would skip).
if config.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID = config.GCP_PROJECT_ID or "cyphron"
SUBSCRIPTION_ID = config.PUBSUB_SUBSCRIPTION or "transactions-sub"


def _gcp_project_from_service_account_email(email: str) -> str | None:
    if ".iam.gserviceaccount.com" not in email or "@" not in email:
        return None
    host = email.split("@", 1)[1]
    return host.removesuffix(".iam.gserviceaccount.com") or None

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)


def process_transaction(tx: Transaction) -> None:
    print(f"\nReceived TX: {tx.transaction_id}")
    print(f"From {tx.account_id} -> {tx.recipient_id} | {tx.amount} {tx.currency}")
    client = initialize_neo4j()
    if client is not None:
        upsert_transaction_graph(client, tx.model_dump())

    decision = None
    svc = get_ingestion_decision_service()
    if svc is not None:
        try:
            decision = svc.decide(tx)
        except Exception as exc:
            print(f"Scoring failed (ingestion): {exc}", flush=True)

    persist_ingestion_outcome(tx, decision)


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    raw = message.data.decode("utf-8").strip()
    if not raw:
        print("Skipping message with empty body (ack)", flush=True)
        message.ack()
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        preview = raw[:120] + ("..." if len(raw) > 120 else "")
        print(f"Skipping non-JSON message ({e!s}; first bytes: {preview!r})", flush=True)
        message.ack()
        return

    try:
        tx = Transaction.model_validate(payload)
        process_transaction(tx)
        message.ack()
    except Exception as e:
        print(f"Validation/processing error: {e}", flush=True)
        message.nack()


def listen() -> None:
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if cred_path and os.path.isfile(cred_path):
        try:
            with open(cred_path, encoding="utf-8") as f:
                sa = json.load(f).get("client_email", "?")
            print(f"Pub/Sub credentials: {sa} (project={PROJECT_ID})", flush=True)
            sa_proj = _gcp_project_from_service_account_email(sa) if isinstance(sa, str) else None
            if sa_proj and sa_proj != PROJECT_ID:
                print(
                    f"WARNING: This key belongs to GCP project `{sa_proj}` but "
                    f"GCP_PROJECT_ID is `{PROJECT_ID}`. Pub/Sub IAM on `{sa_proj}` does not apply to "
                    f"subscriptions in `{PROJECT_ID}`. Either set GCP_PROJECT_ID={sa_proj} and use Pub/Sub there, "
                    f"or add `{sa}` to IAM on project `{PROJECT_ID}` with roles/pubsub.subscriber (and publisher).",
                    flush=True,
                )
        except (OSError, json.JSONDecodeError):
            pass
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(
        f"Listening on projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_ID} ...",
        flush=True,
    )

    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        streaming_pull_future.result()


if __name__ == "__main__":
    listen()

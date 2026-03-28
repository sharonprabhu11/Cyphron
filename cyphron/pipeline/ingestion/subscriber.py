from __future__ import annotations

import json
import os

from google.cloud import pubsub_v1

from pipeline import config
from pipeline.ingestion.schema import Transaction

if config.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ.setdefault(
        "GOOGLE_APPLICATION_CREDENTIALS",
        config.GOOGLE_APPLICATION_CREDENTIALS,
    )

PROJECT_ID = config.GCP_PROJECT_ID or "cyphron"
SUBSCRIPTION_ID = config.PUBSUB_SUBSCRIPTION or "transactions-sub"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)


def process_transaction(tx: Transaction) -> None:
    print(f"\nReceived TX: {tx.transaction_id}")
    print(f"From {tx.account_id} -> {tx.recipient_id} | {tx.amount} {tx.currency}")


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

from __future__ import annotations

import json
import os
import time

from google.cloud import pubsub_v1

from pipeline import config
from simulator.tx_simulator import (
    generate_fanout_fraud,
    generate_normal_tx,
    generate_structuring_fraud,
)

if config.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID = config.GCP_PROJECT_ID or "cyphron"
TOPIC_ID = config.PUBSUB_TOPIC or "transactions"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def publish_message(data):
    message_json = json.dumps(data)
    message_bytes = message_json.encode("utf-8")

    future = publisher.publish(topic_path, message_bytes)
    future.result(timeout=30)
    print(f"Published: {data['transaction_id']}", flush=True)

def run_stream():
    while True:
        # Mix normal + fraud
        tx = generate_normal_tx()
        publish_message(tx)

        # Occasionally inject fraud
        if int(time.time()) % 15 == 0:
            print("\n[INJECT] FANOUT FRAUD\n", flush=True)
            for tx in generate_fanout_fraud():
                publish_message(tx)

        if int(time.time()) % 25 == 0:
            print("\n[INJECT] STRUCTURING FRAUD\n", flush=True)
            for tx in generate_structuring_fraud():
                publish_message(tx)

        time.sleep(1)

if __name__ == "__main__":
    run_stream()
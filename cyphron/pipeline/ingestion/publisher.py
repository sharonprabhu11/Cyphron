from google.cloud import pubsub_v1
import json
import time

# Import your simulator functions
from tx_simulator import generate_normal_tx, generate_fanout_fraud, generate_structuring_fraud

PROJECT_ID = "cyphron"
TOPIC_ID = "transactions"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def publish_message(data):
    message_json = json.dumps(data)
    message_bytes = message_json.encode("utf-8")

    future = publisher.publish(topic_path, message_bytes)
    print(f"Published: {data['transaction_id']}")

def run_stream():
    while True:
        # Mix normal + fraud
        tx = generate_normal_tx()
        publish_message(tx)

        # Occasionally inject fraud
        if int(time.time()) % 15 == 0:
            print("\n🚨 Injecting FANOUT FRAUD\n")
            for tx in generate_fanout_fraud():
                publish_message(tx)

        if int(time.time()) % 25 == 0:
            print("\n🚨 Injecting STRUCTURING FRAUD\n")
            for tx in generate_structuring_fraud():
                publish_message(tx)

        time.sleep(1)

if __name__ == "__main__":
    run_stream()
from google.cloud import pubsub_v1
import json
from schema import Transaction  # your schema file

PROJECT_ID = "your-project-id"
SUBSCRIPTION_ID = "transactions-sub"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

# --- Placeholder processing (later stages) ---
def process_transaction(tx: Transaction):
    print(f"\n📥 Received TX: {tx.transaction_id}")
    print(f"From {tx.account_id} → {tx.recipient_id} | ₹{tx.amount}")

    # 👉 NEXT STAGES (to be added later)
    # entity_resolution(tx)
    # update_graph(tx)
    # feature_engineering(tx)
    # gnn_score(tx)

def callback(message):
    try:
        data = json.loads(message.data.decode("utf-8"))

        tx = Transaction(**data)  # validation step
        process_transaction(tx)

        message.ack()

    except Exception as e:
        print(f"❌ Error: {e}")
        message.nack()

def listen():
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print("Listening for messages...")

    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

if __name__ == "__main__":
    listen()
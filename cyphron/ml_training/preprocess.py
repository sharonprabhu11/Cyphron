"""
Preprocessing for Cyphron:
- Builds PyG graph for training
- Pushes graph to Neo4j for visualization/demo
"""

from __future__ import annotations

import pandas as pd
import torch
from torch_geometric.data import Data
from sklearn.preprocessing import StandardScaler
from neo4j import GraphDatabase

from pipeline.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD





# -----------------------------
# Neo4j helper functions
# -----------------------------
def insert_node(tx, node_id, features, label):
    tx.run("""
        MERGE (n:Entity {id: $id})
        SET n.features = $features,
            n.label = $label
    """, id=node_id, features=features, label=label)


def insert_edge(tx, src, dst):
    tx.run("""
        MATCH (a:Entity {id: $src})
        MATCH (b:Entity {id: $dst})
        MERGE (a)-[:CONNECTED]->(b)
    """, src=src, dst=dst)


# -----------------------------
# MAIN
# -----------------------------
def main() -> None:
    print("🔄 Starting preprocessing...")

    # -----------------------------
    # STEP 1: Load dataset
    # -----------------------------
    df = pd.read_csv("data/transactions.csv")

    print("✅ Data loaded")

    # -----------------------------
    # STEP 2: Clean data
    # -----------------------------
    df = df.fillna(0)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")

    # -----------------------------
    # STEP 3: Create entity nodes
    # -----------------------------
    if "entity_id" not in df.columns or df["entity_id"].isnull().all():
        print("⚠️ Using device_fingerprint as entity_id")
        df["entity_id"] = df["device_fingerprint"]

    entities = df["entity_id"].unique()
    entity_to_id = {e: i for i, e in enumerate(entities)}

    df["node_id"] = df["entity_id"].map(entity_to_id)

    print(f"🧠 Total nodes: {len(entities)}")

    # -----------------------------
    # STEP 4: Create edges
    # -----------------------------
    edges = []

    # Session edges
    for _, group in df.groupby("session_id"):
        nodes = group["node_id"].tolist()
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                edges.append((nodes[i], nodes[j]))

    # Device edges
    for _, group in df.groupby("device_fingerprint"):
        nodes = group["node_id"].tolist()
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                edges.append((nodes[i], nodes[j]))

    # IP edges
    for _, group in df.groupby("ip_address"):
        nodes = group["node_id"].tolist()
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                edges.append((nodes[i], nodes[j]))

    edges = edges[:50000]

    if len(edges) == 0:
        raise ValueError("❌ No edges created")

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    print(f"🔗 Total edges: {edge_index.shape[1]}")

    # -----------------------------
    # STEP 5: Features
    # -----------------------------
    features = []
    labels = []

    for entity in entities:
        user_df = df[df["entity_id"] == entity]

        total_amount = user_df["amount"].sum()
        avg_amount = user_df["amount"].mean()
        tx_count = len(user_df)

        if "timestamp" in df.columns:
            time_diff = (
                user_df["timestamp"].max() - user_df["timestamp"].min()
            ).total_seconds()
            velocity = tx_count / time_diff if time_diff > 0 else 0
        else:
            velocity = 0

        unique_devices = user_df["device_fingerprint"].nunique()
        unique_ips = user_df["ip_address"].nunique()

        channel_counts = user_df["channel"].value_counts(normalize=True)

        features.append([
            total_amount,
            avg_amount,
            tx_count,
            velocity,
            unique_devices,
            unique_ips,
            channel_counts.get("UPI", 0),
            channel_counts.get("ATM", 0),
            channel_counts.get("WEB", 0),
            channel_counts.get("MOBILE", 0),
        ])

        # Label (heuristic)
        if velocity > 5 and tx_count > 5:
            labels.append(1)
        else:
            labels.append(0)

    # Normalize
    x = torch.tensor(features, dtype=torch.float)
    scaler = StandardScaler()
    x = torch.tensor(scaler.fit_transform(x), dtype=torch.float)

    y = torch.tensor(labels, dtype=torch.long)

    print(f"📊 Features: {x.shape}")
    print(f"🚨 Fraud nodes: {y.sum().item()} / {len(y)}")

    # -----------------------------
    # STEP 6: Build graph object
    # -----------------------------
    data = Data(x=x, edge_index=edge_index, y=y)

    # -----------------------------
    # STEP 7: Save .pt file
    # -----------------------------
    torch.save(data, "data/processed_graph.pt")
    print("✅ Saved processed_graph.pt")

    # -----------------------------
    # STEP 8: Push to Neo4j
    # -----------------------------
    print("📡 Pushing graph to Neo4j...")

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    with driver.session() as session:
        # Insert nodes
        for i in range(len(entities)):
            session.write_transaction(
                insert_node,
                int(i),
                x[i].tolist(),
                int(y[i])
            )

        # Insert edges
        for i in range(edge_index.shape[1]):
            src = int(edge_index[0][i])
            dst = int(edge_index[1][i])

            session.write_transaction(insert_edge, src, dst)

    driver.close()

    print("✅ Graph pushed to Neo4j!")
    print("🎉 Preprocessing complete!")


if __name__ == "__main__":
    main()
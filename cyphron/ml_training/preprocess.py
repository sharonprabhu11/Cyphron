"""
Build a training-ready account graph from simulated transactions.

The output is account-centric because the first GNN goal is node-level mule-risk
scoring for accounts, while Neo4j keeps the richer heterogeneous live graph.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "transaction_id",
    "account_id",
    "recipient_id",
    "amount",
    "timestamp",
    "channel",
    "device_fingerprint",
    "ip_address",
    "session_id",
}


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    working = df.copy()
    working["timestamp"] = pd.to_datetime(working["timestamp"], utc=True, errors="coerce")
    working = working.dropna(subset=["timestamp", "account_id", "recipient_id", "transaction_id"])
    working["amount"] = working["amount"].astype(float)
    for column in [
        "device_fingerprint",
        "ip_address",
        "phone_number",
        "session_id",
        "cluster_id",
        "rule_flags",
        "behavior_signature",
    ]:
        if column not in working.columns:
            working[column] = None
    if "is_fraud" not in working.columns:
        working["is_fraud"] = False
    if "risk_score" not in working.columns:
        working["risk_score"] = 0.0
    return working.sort_values("timestamp").reset_index(drop=True)


def _normalize_rule_flags(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            pass
        return [flag.strip() for flag in value.split(",") if flag.strip()]
    return [str(value)]


def _account_label(df: pd.DataFrame, account_id: str) -> int:
    related = df[(df["account_id"] == account_id) | (df["recipient_id"] == account_id)]
    if related.empty:
        return 0

    if related["is_fraud"].fillna(False).astype(bool).any():
        return 1
    if related["risk_score"].fillna(0).astype(float).ge(0.8).any():
        return 1
    if related["cluster_id"].fillna("").astype(str).str.startswith("FRAUD-").any():
        return 1
    if any(_normalize_rule_flags(value) for value in related["rule_flags"]):
        return 1
    return 0


def _shared_neighbors(df: pd.DataFrame, column: str) -> dict[str, int]:
    counts: dict[str, set[str]] = {}
    for _, group in df[df[column].notna() & (df[column] != "")].groupby(column):
        accounts = set(group["account_id"].astype(str).tolist())
        for account in accounts:
            counts.setdefault(account, set()).update(accounts - {account})
    return {account: len(neighbors) for account, neighbors in counts.items()}


def _channel_ratio(outgoing: pd.DataFrame, channel: str) -> float:
    if outgoing.empty:
        return 0.0
    return float((outgoing["channel"] == channel).mean())


def _build_features(df: pd.DataFrame, account_ids: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    feature_names = [
        "out_tx_count",
        "in_tx_count",
        "total_out_amount",
        "total_in_amount",
        "avg_out_amount",
        "avg_in_amount",
        "unique_recipients",
        "unique_senders",
        "fan_out_ratio",
        "fan_in_ratio",
        "near_threshold_out_count",
        "shared_device_accounts",
        "shared_ip_accounts",
        "shared_phone_accounts",
        "shared_session_accounts",
        "burst_tx_per_minute",
        "upi_ratio",
        "atm_ratio",
        "web_ratio",
        "mobile_ratio",
    ]

    shared_device = _shared_neighbors(df, "device_fingerprint")
    shared_ip = _shared_neighbors(df, "ip_address")
    shared_phone = _shared_neighbors(df, "phone_number")
    shared_session = _shared_neighbors(df, "session_id")

    rows: list[list[float]] = []
    labels: list[int] = []

    for account_id in account_ids:
        outgoing = df[df["account_id"] == account_id]
        incoming = df[df["recipient_id"] == account_id]

        out_tx_count = float(len(outgoing))
        in_tx_count = float(len(incoming))
        total_out_amount = float(outgoing["amount"].sum()) if not outgoing.empty else 0.0
        total_in_amount = float(incoming["amount"].sum()) if not incoming.empty else 0.0
        avg_out_amount = float(outgoing["amount"].mean()) if not outgoing.empty else 0.0
        avg_in_amount = float(incoming["amount"].mean()) if not incoming.empty else 0.0
        unique_recipients = float(outgoing["recipient_id"].nunique()) if not outgoing.empty else 0.0
        unique_senders = float(incoming["account_id"].nunique()) if not incoming.empty else 0.0
        fan_out_ratio = unique_recipients / out_tx_count if out_tx_count else 0.0
        fan_in_ratio = unique_senders / in_tx_count if in_tx_count else 0.0
        near_threshold_out_count = float(outgoing["amount"].between(45_000, 49_999.99).sum()) if not outgoing.empty else 0.0

        activity = pd.concat([outgoing["timestamp"], incoming["timestamp"]]).sort_values()
        if len(activity) >= 2:
            minutes = max((activity.iloc[-1] - activity.iloc[0]).total_seconds() / 60.0, 1 / 60)
            burst_tx_per_minute = float((out_tx_count + in_tx_count) / minutes)
        else:
            burst_tx_per_minute = float(out_tx_count + in_tx_count)

        rows.append([
            out_tx_count,
            in_tx_count,
            total_out_amount,
            total_in_amount,
            avg_out_amount,
            avg_in_amount,
            unique_recipients,
            unique_senders,
            fan_out_ratio,
            fan_in_ratio,
            near_threshold_out_count,
            float(shared_device.get(account_id, 0)),
            float(shared_ip.get(account_id, 0)),
            float(shared_phone.get(account_id, 0)),
            float(shared_session.get(account_id, 0)),
            burst_tx_per_minute,
            _channel_ratio(outgoing, "UPI"),
            _channel_ratio(outgoing, "ATM"),
            _channel_ratio(outgoing, "WEB"),
            _channel_ratio(outgoing, "MOBILE"),
        ])
        labels.append(_account_label(df, account_id))

    x = np.asarray(rows, dtype=np.float32)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0] = 1.0
    x = (x - mean) / std

    return x, np.asarray(labels, dtype=np.int64), feature_names


def _add_undirected_edge(edges: set[tuple[int, int]], src: int, dst: int) -> None:
    if src == dst:
        return
    edges.add((src, dst))
    edges.add((dst, src))


def _build_edges(df: pd.DataFrame, account_index: dict[str, int]) -> np.ndarray:
    edges: set[tuple[int, int]] = set()

    for row in df.itertuples(index=False):
        src = account_index[str(row.account_id)]
        dst = account_index[str(row.recipient_id)]
        _add_undirected_edge(edges, src, dst)

    for column in ["device_fingerprint", "ip_address", "phone_number", "session_id"]:
        valid = df[df[column].notna() & (df[column] != "")]
        for _, group in valid.groupby(column):
            accounts = sorted(set(group["account_id"].astype(str).tolist()))
            for index, src_account in enumerate(accounts):
                for dst_account in accounts[index + 1 :]:
                    _add_undirected_edge(edges, account_index[src_account], account_index[dst_account])

    if not edges:
        raise ValueError("No graph edges could be constructed from the dataset.")

    edge_array = np.asarray(sorted(edges), dtype=np.int64)
    return edge_array.T


def preprocess_transactions(input_path: Path, output_dir: Path) -> dict[str, object]:
    df = _ensure_columns(pd.read_csv(input_path))
    account_ids = sorted(set(df["account_id"].astype(str)).union(df["recipient_id"].astype(str)))
    account_index = {account_id: index for index, account_id in enumerate(account_ids)}

    x, y, feature_names = _build_features(df, account_ids)
    edge_index = _build_edges(df, account_index)

    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_dir / "processed_graph.npz",
        x=x,
        y=y,
        edge_index=edge_index,
        account_ids=np.asarray(account_ids),
        feature_names=np.asarray(feature_names),
    )

    metadata = {
        "num_nodes": int(len(account_ids)),
        "num_edges": int(edge_index.shape[1]),
        "num_features": int(x.shape[1]),
        "num_positive_labels": int(y.sum()),
        "feature_names": feature_names,
        "input_path": str(input_path),
    }
    (output_dir / "processed_graph_meta.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess simulated Cyphron transactions into a training graph.")
    parser.add_argument("--input", default="data/transactions.csv", help="CSV file containing transaction records.")
    parser.add_argument("--output-dir", default="data", help="Directory for processed graph artifacts.")
    args = parser.parse_args()

    metadata = preprocess_transactions(Path(args.input), Path(args.output_dir))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

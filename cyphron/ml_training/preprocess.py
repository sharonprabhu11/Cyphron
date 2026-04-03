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


def _account_groups(df: pd.DataFrame, account_ids: list[str]) -> list[str]:
    incident = pd.concat(
        [
            df.loc[:, ["account_id", "scenario_id", "cluster_id"]].rename(columns={"account_id": "node_id"}),
            df.loc[:, ["recipient_id", "scenario_id", "cluster_id"]].rename(columns={"recipient_id": "node_id"}),
        ],
        ignore_index=True,
    )
    incident["scenario_id"] = incident["scenario_id"].fillna("").astype(str).replace("nan", "")
    incident["cluster_id"] = incident["cluster_id"].fillna("").astype(str).replace("nan", "")

    scenario_lookup = (
        incident[incident["scenario_id"] != ""]
        .groupby("node_id")["scenario_id"]
        .first()
    )
    cluster_lookup = (
        incident[incident["cluster_id"] != ""]
        .groupby("node_id")["cluster_id"]
        .first()
    )

    groups: list[str] = []
    for account_id in account_ids:
        scenario_group = scenario_lookup.get(account_id, "")
        if scenario_group:
            groups.append(str(scenario_group))
            continue
        cluster_group = cluster_lookup.get(account_id, "")
        if cluster_group:
            groups.append(str(cluster_group))
            continue
        groups.append(f"ACCOUNT-{account_id}")
    return groups


def _group_split_masks(group_ids: list[str], y: np.ndarray, seed: int = 42) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    unique_groups = sorted(set(group_ids))
    group_to_indices: dict[str, list[int]] = {group: [] for group in unique_groups}
    for index, group in enumerate(group_ids):
        group_to_indices[group].append(index)

    positive_groups = [group for group in unique_groups if y[group_to_indices[group]].max() == 1]
    negative_groups = [group for group in unique_groups if y[group_to_indices[group]].max() == 0]
    rng.shuffle(positive_groups)
    rng.shuffle(negative_groups)

    def split_groups(groups: list[str]) -> tuple[list[str], list[str], list[str]]:
        train_end = max(1, int(len(groups) * 0.7)) if groups else 0
        val_end = max(train_end, int(len(groups) * 0.85)) if groups else 0
        return groups[:train_end], groups[train_end:val_end], groups[val_end:]

    pos_train, pos_val, pos_test = split_groups(positive_groups)
    neg_train, neg_val, neg_test = split_groups(negative_groups)

    train_groups = set(pos_train + neg_train)
    val_groups = set(pos_val + neg_val)
    test_groups = set(pos_test + neg_test)

    for group in unique_groups:
        if group not in train_groups and group not in val_groups and group not in test_groups:
            train_groups.add(group)

    train_mask = np.asarray([group in train_groups for group in group_ids], dtype=bool)
    val_mask = np.asarray([group in val_groups for group in group_ids], dtype=bool)
    test_mask = np.asarray([group in test_groups for group in group_ids], dtype=bool)
    return train_mask, val_mask, test_mask


def _account_labels(df: pd.DataFrame, account_ids: list[str]) -> np.ndarray:
    src = df.loc[:, ["account_id", "is_fraud", "risk_score", "cluster_id", "rule_flags"]].rename(
        columns={"account_id": "node_id"}
    )
    dst = df.loc[:, ["recipient_id", "is_fraud", "risk_score", "cluster_id", "rule_flags"]].rename(
        columns={"recipient_id": "node_id"}
    )
    incident = pd.concat([src, dst], ignore_index=True)
    incident["is_fraud"] = incident["is_fraud"].fillna(False).astype(bool)
    incident["risk_score"] = incident["risk_score"].fillna(0).astype(float)
    incident["cluster_id"] = incident["cluster_id"].fillna("").astype(str)
    incident["has_rule_flag"] = incident["rule_flags"].map(lambda value: bool(_normalize_rule_flags(value)))

    labels = (
        incident.groupby("node_id")
        .agg(
            is_fraud=("is_fraud", "max"),
            risk_score=("risk_score", "max"),
            fraud_cluster=("cluster_id", lambda s: s.str.startswith("FRAUD-").any()),
            has_rule_flag=("has_rule_flag", "max"),
        )
    )
    positive = (
        labels["is_fraud"].astype(bool)
        | labels["risk_score"].ge(0.8)
        | labels["fraud_cluster"].astype(bool)
        | labels["has_rule_flag"].astype(bool)
    )
    return positive.reindex(account_ids, fill_value=False).astype(np.int64).to_numpy()


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

    outgoing = df.groupby("account_id").agg(
        out_tx_count=("transaction_id", "size"),
        total_out_amount=("amount", "sum"),
        avg_out_amount=("amount", "mean"),
        unique_recipients=("recipient_id", "nunique"),
        near_threshold_out_count=("amount", lambda s: s.between(45_000, 49_999.99).sum()),
    )
    incoming = df.groupby("recipient_id").agg(
        in_tx_count=("transaction_id", "size"),
        total_in_amount=("amount", "sum"),
        avg_in_amount=("amount", "mean"),
        unique_senders=("account_id", "nunique"),
    )

    activity = pd.concat(
        [
            df.loc[:, ["account_id", "timestamp"]].rename(columns={"account_id": "node_id"}),
            df.loc[:, ["recipient_id", "timestamp"]].rename(columns={"recipient_id": "node_id"}),
        ],
        ignore_index=True,
    )
    activity_stats = activity.groupby("node_id").agg(
        activity_count=("timestamp", "size"),
        first_seen=("timestamp", "min"),
        last_seen=("timestamp", "max"),
    )
    duration_minutes = (
        (activity_stats["last_seen"] - activity_stats["first_seen"]).dt.total_seconds() / 60.0
    ).clip(lower=(1 / 60))
    activity_stats["burst_tx_per_minute"] = activity_stats["activity_count"] / duration_minutes

    feature_frame = pd.DataFrame(index=account_ids)
    feature_frame = feature_frame.join(outgoing, how="left")
    feature_frame = feature_frame.join(incoming, how="left")
    feature_frame = feature_frame.join(activity_stats[["burst_tx_per_minute"]], how="left")

    for channel_name, feature_name in [
        ("UPI", "upi_ratio"),
        ("ATM", "atm_ratio"),
        ("WEB", "web_ratio"),
        ("MOBILE", "mobile_ratio"),
    ]:
        channel_ratio = (df["channel"].astype(str).str.upper() == channel_name).groupby(df["account_id"]).mean()
        feature_frame[feature_name] = channel_ratio

    feature_frame["fan_out_ratio"] = feature_frame["unique_recipients"] / feature_frame["out_tx_count"]
    feature_frame["fan_in_ratio"] = feature_frame["unique_senders"] / feature_frame["in_tx_count"]
    feature_frame["fan_out_ratio"] = feature_frame["fan_out_ratio"].replace([np.inf, -np.inf], 0.0)
    feature_frame["fan_in_ratio"] = feature_frame["fan_in_ratio"].replace([np.inf, -np.inf], 0.0)
    feature_frame["shared_device_accounts"] = [float(shared_device.get(account_id, 0)) for account_id in account_ids]
    feature_frame["shared_ip_accounts"] = [float(shared_ip.get(account_id, 0)) for account_id in account_ids]
    feature_frame["shared_phone_accounts"] = [float(shared_phone.get(account_id, 0)) for account_id in account_ids]
    feature_frame["shared_session_accounts"] = [float(shared_session.get(account_id, 0)) for account_id in account_ids]
    feature_frame = feature_frame.fillna(0.0)

    x = feature_frame.loc[:, feature_names].to_numpy(dtype=np.float32)
    y = _account_labels(df, account_ids)
    return x, y, feature_names


def _add_undirected_edge(edges: set[tuple[int, int]], src: int, dst: int) -> None:
    if src == dst:
        return
    edges.add((src, dst))
    edges.add((dst, src))


def _build_edges(df: pd.DataFrame, account_index: dict[str, int]) -> np.ndarray:
    src = df["account_id"].astype(str).map(account_index).to_numpy(dtype=np.int64, copy=False)
    dst = df["recipient_id"].astype(str).map(account_index).to_numpy(dtype=np.int64, copy=False)
    valid = src != dst
    forward_edges = np.column_stack([src[valid], dst[valid]])
    reverse_edges = np.column_stack([dst[valid], src[valid]])
    edge_arrays = [forward_edges, reverse_edges]

    for column in ["device_fingerprint", "ip_address", "phone_number", "session_id"]:
        valid = df[df[column].notna() & (df[column] != "")]
        for _, group in valid.groupby(column):
            accounts = sorted(set(group["account_id"].astype(str).tolist()))
            if len(accounts) < 2:
                continue
            shared_edges: list[tuple[int, int]] = []
            for index, src_account in enumerate(accounts):
                for dst_account in accounts[index + 1 :]:
                    src_index = account_index[src_account]
                    dst_index = account_index[dst_account]
                    shared_edges.append((src_index, dst_index))
                    shared_edges.append((dst_index, src_index))
            if shared_edges:
                edge_arrays.append(np.asarray(shared_edges, dtype=np.int64))

    if not edge_arrays:
        raise ValueError("No graph edges could be constructed from the dataset.")

    edge_array = np.concatenate(edge_arrays, axis=0)
    edge_array = np.unique(edge_array, axis=0)
    return edge_array.T


def preprocess_transactions(input_path: Path, output_dir: Path) -> dict[str, object]:
    df = _ensure_columns(pd.read_csv(input_path))
    account_ids = sorted(set(df["account_id"].astype(str)).union(df["recipient_id"].astype(str)))
    account_index = {account_id: index for index, account_id in enumerate(account_ids)}

    x, y, feature_names = _build_features(df, account_ids)
    group_ids = _account_groups(df, account_ids)
    train_mask, val_mask, test_mask = _group_split_masks(group_ids, y)
    mean = x[train_mask].mean(axis=0) if train_mask.any() else x.mean(axis=0)
    std = x[train_mask].std(axis=0) if train_mask.any() else x.std(axis=0)
    std[std == 0] = 1.0
    x = ((x - mean) / std).astype(np.float32)
    edge_index = _build_edges(df, account_index)

    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_dir / "processed_graph.npz",
        x=x,
        y=y,
        edge_index=edge_index,
        account_ids=np.asarray(account_ids),
        feature_names=np.asarray(feature_names),
        group_ids=np.asarray(group_ids),
        train_mask=train_mask,
        val_mask=val_mask,
        test_mask=test_mask,
        scaler_mean=mean.astype(np.float32),
        scaler_std=std.astype(np.float32),
    )

    metadata = {
        "num_nodes": int(len(account_ids)),
        "num_edges": int(edge_index.shape[1]),
        "num_features": int(x.shape[1]),
        "num_positive_labels": int(y.sum()),
        "train_nodes": int(train_mask.sum()),
        "val_nodes": int(val_mask.sum()),
        "test_nodes": int(test_mask.sum()),
        "positive_train_nodes": int(y[train_mask].sum()),
        "positive_val_nodes": int(y[val_mask].sum()),
        "positive_test_nodes": int(y[test_mask].sum()),
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

"""
Offline GraphSAGE training for Cyphron account-risk scoring.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

try:
    import torch
    import torch.nn.functional as F
    from torch import Tensor
    from torch_geometric.data import Data
    from torch_geometric.nn import SAGEConv
    from torch_geometric.utils import subgraph
except Exception:  # pragma: no cover - optional heavy deps
    torch = None  # type: ignore
    F = None  # type: ignore
    Tensor = None  # type: ignore
    Data = None  # type: ignore
    SAGEConv = None  # type: ignore
    subgraph = None  # type: ignore


if torch is not None:
    class GraphSageClassifier(torch.nn.Module):  # type: ignore[misc]
        def __init__(self, input_dim: int, hidden_dim: int = 64, dropout: float = 0.2) -> None:
            super().__init__()
            self.conv1 = SAGEConv(input_dim, hidden_dim)
            self.conv2 = SAGEConv(hidden_dim, hidden_dim)
            self.classifier = torch.nn.Linear(hidden_dim, 2)
            self.dropout = dropout

        def forward(self, x: Tensor, edge_index: Tensor) -> Tensor:
            x = self.conv1(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
            x = self.conv2(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
            return self.classifier(x)


def _require_torch() -> None:
    if torch is None or Data is None or SAGEConv is None or subgraph is None:
        raise SystemExit(
            "GraphSAGE training requires torch and torch-geometric. "
            "Install ml_training/requirements-optional-torch.txt first."
        )


def _load_processed_graph(path: Path) -> tuple["Data", dict[str, object]]:
    raw = np.load(path, allow_pickle=True)
    x = torch.tensor(raw["x"], dtype=torch.float32)
    y = torch.tensor(raw["y"], dtype=torch.long)
    edge_index = torch.tensor(raw["edge_index"], dtype=torch.long)
    graph = Data(x=x, edge_index=edge_index, y=y)
    metadata = {
        "account_ids": raw["account_ids"].tolist(),
        "feature_names": raw["feature_names"].tolist(),
        "train_mask": raw["train_mask"] if "train_mask" in raw.files else None,
        "val_mask": raw["val_mask"] if "val_mask" in raw.files else None,
        "test_mask": raw["test_mask"] if "test_mask" in raw.files else None,
        "group_ids": raw["group_ids"].tolist() if "group_ids" in raw.files else None,
    }
    return graph, metadata


def _train_val_test_masks(num_nodes: int, seed: int = 42) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    indices = np.arange(num_nodes)
    rng.shuffle(indices)

    train_end = int(num_nodes * 0.7)
    val_end = int(num_nodes * 0.85)

    train_mask = np.zeros(num_nodes, dtype=bool)
    val_mask = np.zeros(num_nodes, dtype=bool)
    test_mask = np.zeros(num_nodes, dtype=bool)

    train_mask[indices[:train_end]] = True
    val_mask[indices[train_end:val_end]] = True
    test_mask[indices[val_end:]] = True
    return train_mask, val_mask, test_mask


def _f1_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _precision_recall(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


def _induced_subgraph_data(data: "Data", mask: np.ndarray) -> tuple["Data", np.ndarray]:
    node_indices = np.where(mask)[0]
    subset = torch.tensor(node_indices, dtype=torch.long)
    edge_index, _ = subgraph(subset, data.edge_index, relabel_nodes=True)
    graph = Data(
        x=data.x[subset],
        edge_index=edge_index,
        y=data.y[subset],
    )
    return graph, node_indices


def train_model(
    input_path: Path,
    artifact_dir: Path,
    *,
    epochs: int = 80,
    hidden_dim: int = 64,
    learning_rate: float = 0.01,
    seed: int = 42,
) -> dict[str, object]:
    _require_torch()
    torch.manual_seed(seed)
    np.random.seed(seed)

    data, metadata = _load_processed_graph(input_path)
    if metadata["train_mask"] is not None:
        train_mask = np.asarray(metadata["train_mask"], dtype=bool)
        val_mask = np.asarray(metadata["val_mask"], dtype=bool)
        test_mask = np.asarray(metadata["test_mask"], dtype=bool)
    else:
        train_mask, val_mask, test_mask = _train_val_test_masks(data.num_nodes, seed=seed)

    train_mask_t = torch.tensor(train_mask, dtype=torch.bool)
    train_graph, _ = _induced_subgraph_data(data, train_mask)
    val_graph, _ = _induced_subgraph_data(data, val_mask)
    test_graph, _ = _induced_subgraph_data(data, test_mask)

    model = GraphSageClassifier(input_dim=data.num_node_features, hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    train_labels = train_graph.y.cpu().numpy()
    positive_count = max(int((train_labels == 1).sum()), 1)
    negative_count = max(int((train_labels == 0).sum()), 1)
    class_weights = torch.tensor(
        [1.0, negative_count / positive_count],
        dtype=torch.float32,
    )

    best_val_f1 = -1.0
    best_state: dict[str, object] | None = None

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        logits = model(train_graph.x, train_graph.edge_index)
        loss = F.cross_entropy(logits, train_graph.y, weight=class_weights)
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(val_graph.x, val_graph.edge_index)
            val_pred = val_logits.argmax(dim=1).cpu().numpy()
            val_true = val_graph.y.cpu().numpy()
            val_f1 = _f1_score(val_true, val_pred)
            if val_f1 >= best_val_f1:
                best_val_f1 = val_f1
                best_state = {
                    "model_state_dict": model.state_dict(),
                    "input_dim": data.num_node_features,
                    "hidden_dim": hidden_dim,
                    "feature_names": metadata["feature_names"],
                    "best_epoch": epoch + 1,
                }

    assert best_state is not None
    artifact_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = artifact_dir / "graphsage_model.pt"
    torch.save(best_state, checkpoint_path)

    model.load_state_dict(best_state["model_state_dict"])  # type: ignore[index]
    model.eval()
    with torch.no_grad():
        logits = model(test_graph.x, test_graph.edge_index)
        pred = logits.argmax(dim=1).cpu().numpy()
        true = test_graph.y.cpu().numpy()
        precision, recall = _precision_recall(true, pred)
        metrics = {
            "test_f1": round(_f1_score(true, pred), 4),
            "test_accuracy": round(float((pred == true).mean()) if len(true) else 0.0, 4),
            "test_precision": round(float(precision), 4),
            "test_recall": round(float(recall), 4),
            "positives_in_test": int(true.sum()),
            "best_val_f1": round(float(best_val_f1), 4),
            "best_epoch": int(best_state["best_epoch"]),  # type: ignore[index]
            "checkpoint": str(checkpoint_path),
            "num_nodes": int(data.num_nodes),
            "num_edges": int(data.num_edges),
            "train_nodes": int(train_mask.sum()),
            "val_nodes": int(val_mask.sum()),
            "test_nodes": int(test_mask.sum()),
        }

    surrogate = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    surrogate.fit(train_graph.x.cpu().numpy(), train_graph.y.cpu().numpy())
    baseline_pred = surrogate.predict(test_graph.x.cpu().numpy())
    baseline_precision, baseline_recall = _precision_recall(true, baseline_pred)
    metrics["baseline_logreg_f1"] = round(_f1_score(true, baseline_pred), 4)
    metrics["baseline_logreg_accuracy"] = round(float((baseline_pred == true).mean()) if len(true) else 0.0, 4)
    metrics["baseline_logreg_precision"] = round(float(baseline_precision), 4)
    metrics["baseline_logreg_recall"] = round(float(baseline_recall), 4)
    with (artifact_dir / "shap_surrogate.pkl").open("wb") as handle:
        pickle.dump(surrogate, handle)
    background = train_graph.x.cpu().numpy()
    if len(background) > 128:
        rng = np.random.default_rng(seed)
        background = background[rng.choice(len(background), size=128, replace=False)]
    np.save(artifact_dir / "shap_background.npy", background.astype(np.float32))

    (artifact_dir / "training_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a GraphSAGE fraud model on the processed Cyphron graph.")
    parser.add_argument("--input", default="data/processed_graph.npz", help="Preprocessed graph artifact.")
    parser.add_argument(
        "--artifact-dir",
        default="../pipeline/ml/artifacts",
        help="Directory where the trained model checkpoint and metrics will be saved.",
    )
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.01)
    args = parser.parse_args()

    metrics = train_model(
        Path(args.input),
        Path(args.artifact_dir),
        epochs=args.epochs,
        hidden_dim=args.hidden_dim,
        learning_rate=args.lr,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

"""
Offline GraphSAGE training for Cyphron account-risk scoring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    from torch import Tensor
    from torch_geometric.data import Data
    from torch_geometric.nn import SAGEConv
except Exception:  # pragma: no cover - optional heavy deps
    torch = None  # type: ignore
    F = None  # type: ignore
    Tensor = None  # type: ignore
    Data = None  # type: ignore
    SAGEConv = None  # type: ignore


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
    if torch is None or Data is None or SAGEConv is None:
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
    train_mask, val_mask, test_mask = _train_val_test_masks(data.num_nodes, seed=seed)

    train_mask_t = torch.tensor(train_mask, dtype=torch.bool)
    val_mask_t = torch.tensor(val_mask, dtype=torch.bool)
    test_mask_t = torch.tensor(test_mask, dtype=torch.bool)

    model = GraphSageClassifier(input_dim=data.num_node_features, hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)

    best_val_f1 = -1.0
    best_state: dict[str, object] | None = None

    for _ in range(epochs):
        model.train()
        optimizer.zero_grad()
        logits = model(data.x, data.edge_index)
        loss = F.cross_entropy(logits[train_mask_t], data.y[train_mask_t])
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(data.x, data.edge_index)[val_mask_t]
            val_pred = val_logits.argmax(dim=1).cpu().numpy()
            val_true = data.y[val_mask_t].cpu().numpy()
            val_f1 = _f1_score(val_true, val_pred)
            if val_f1 >= best_val_f1:
                best_val_f1 = val_f1
                best_state = {
                    "model_state_dict": model.state_dict(),
                    "input_dim": data.num_node_features,
                    "hidden_dim": hidden_dim,
                    "feature_names": metadata["feature_names"],
                }

    assert best_state is not None
    artifact_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = artifact_dir / "graphsage_model.pt"
    torch.save(best_state, checkpoint_path)

    model.load_state_dict(best_state["model_state_dict"])  # type: ignore[index]
    model.eval()
    with torch.no_grad():
        logits = model(data.x, data.edge_index)[test_mask_t]
        pred = logits.argmax(dim=1).cpu().numpy()
        true = data.y[test_mask_t].cpu().numpy()
        metrics = {
            "test_f1": round(_f1_score(true, pred), 4),
            "test_accuracy": round(float((pred == true).mean()) if len(true) else 0.0, 4),
            "positives_in_test": int(true.sum()),
            "checkpoint": str(checkpoint_path),
            "num_nodes": int(data.num_nodes),
            "num_edges": int(data.num_edges),
        }

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

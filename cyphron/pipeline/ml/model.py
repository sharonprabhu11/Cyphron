"""
Load and run the offline-trained GraphSAGE account-risk model.
"""

from __future__ import annotations

from pathlib import Path

try:
    import torch
    import torch.nn.functional as F
    from torch import Tensor
    from torch_geometric.nn import SAGEConv
except Exception:  # pragma: no cover - optional heavy deps
    torch = None  # type: ignore
    F = None  # type: ignore
    Tensor = None  # type: ignore
    SAGEConv = None  # type: ignore


if torch is not None:
    class GraphSageClassifier(torch.nn.Module):  # type: ignore[misc]
        def __init__(self, input_dim: int, hidden_dim: int) -> None:
            super().__init__()
            self.conv1 = SAGEConv(input_dim, hidden_dim)
            self.conv2 = SAGEConv(hidden_dim, hidden_dim)
            self.classifier = torch.nn.Linear(hidden_dim, 2)

        def forward(self, x: Tensor, edge_index: Tensor) -> Tensor:
            x = self.conv1(x, edge_index)
            x = F.relu(x)
            x = self.conv2(x, edge_index)
            x = F.relu(x)
            return self.classifier(x)


class FraudModel:
    def __init__(self, checkpoint_path: str | Path) -> None:
        if torch is None or SAGEConv is None:
            raise RuntimeError("torch and torch-geometric are required for GNN inference.")

        checkpoint = torch.load(Path(checkpoint_path), map_location="cpu")
        self.feature_names = checkpoint["feature_names"]
        self.model = GraphSageClassifier(
            input_dim=int(checkpoint["input_dim"]),
            hidden_dim=int(checkpoint["hidden_dim"]),
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

    def predict_proba(self, x: Tensor, edge_index: Tensor) -> Tensor:
        with torch.no_grad():
            logits = self.model(x, edge_index)
            return F.softmax(logits, dim=1)[:, 1]

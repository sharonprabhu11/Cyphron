"""
Thin pipeline wrapper around the offline training entrypoint.
"""

from __future__ import annotations

from pathlib import Path

from ml_training.train import train_model as run_offline_training


def train_model(
    input_path: str | Path = "ml_training/data/processed_graph.npz",
    artifact_dir: str | Path = "pipeline/ml/artifacts",
) -> dict[str, object]:
    return run_offline_training(Path(input_path), Path(artifact_dir))

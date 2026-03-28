"""
Helpers for loading processed graph artifacts inside the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def load_processed_graph_npz(path: str | Path) -> dict[str, np.ndarray]:
    raw = np.load(Path(path), allow_pickle=True)
    return {key: raw[key] for key in raw.files}

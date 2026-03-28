#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${ROOT_DIR}/venv/bin/python"
HISTORY_CSV="${1:-${ROOT_DIR}/ml_training/data/transactions.csv}"
OUTPUT_DIR="${2:-${ROOT_DIR}/ml_training/data/history_processed}"
ARTIFACT_DIR="${3:-${ROOT_DIR}/pipeline/ml/artifacts/history_model}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Missing virtualenv python at ${VENV_PYTHON}" >&2
  exit 1
fi

if [[ ! -f "${HISTORY_CSV}" ]]; then
  echo "History CSV not found at ${HISTORY_CSV}" >&2
  exit 1
fi

echo "Preprocessing training history from ${HISTORY_CSV}"
"${VENV_PYTHON}" "${ROOT_DIR}/ml_training/preprocess.py" --input "${HISTORY_CSV}" --output-dir "${OUTPUT_DIR}"

echo "Training GraphSAGE model from accumulated history"
"${VENV_PYTHON}" "${ROOT_DIR}/ml_training/train.py" --input "${OUTPUT_DIR}/processed_graph.npz" --artifact-dir "${ARTIFACT_DIR}"

echo "History retrain complete"
echo "Processed graph: ${OUTPUT_DIR}/processed_graph.npz"
echo "Artifacts: ${ARTIFACT_DIR}"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${ROOT_DIR}/data/ibm_hismall_raw"
ZIP_PATH="${DATA_DIR}/HI-Small_Trans.csv.zip"
CSV_PATH="${DATA_DIR}/HI-Small_Trans.csv"
DEFAULT_URL="https://huggingface.co/datasets/eexzzm/IBM-Transactions-for-Anti-Money-Laundering-HI-Small-Trans/resolve/main/HI-Small_Trans.csv.zip?download=true"
SOURCE_URL="${IBM_HI_SMALL_URL:-${DEFAULT_URL}}"

mkdir -p "${DATA_DIR}"

if [[ -f "${CSV_PATH}" ]]; then
  echo "IBM AML dataset already present at ${CSV_PATH}"
  exit 0
fi

echo "Downloading IBM AML HI-Small dataset"
echo "Source: ${SOURCE_URL}"
curl -L "${SOURCE_URL}" -o "${ZIP_PATH}"

echo "Extracting dataset"
python3 - <<'PY'
from pathlib import Path
import zipfile

zip_path = Path("cyphron/ml_training/data/ibm_hismall_raw/HI-Small_Trans.csv.zip")
out_dir = zip_path.parent
with zipfile.ZipFile(zip_path, "r") as archive:
    archive.extractall(out_dir)
print(out_dir / "HI-Small_Trans.csv")
PY

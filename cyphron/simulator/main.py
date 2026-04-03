"""
Cyphron Simulator entrypoint.

Print sample transactions or export a CSV dataset for Neo4j/GNN work.
"""

from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from simulator.tx_simulator import export_dataset_csv
from simulator.tx_simulator import generate_fanout_fraud
from simulator.tx_simulator import generate_layering_fraud
from simulator.tx_simulator import generate_normal_tx
from simulator.tx_simulator import generate_structuring_fraud


def main() -> None:
    parser = argparse.ArgumentParser(description="Cyphron simulator utility")
    parser.add_argument("--export-csv", default=None, help="If set, export a training/demo dataset to this CSV path.")
    args = parser.parse_args()

    if args.export_csv:
        path = export_dataset_csv(args.export_csv)
        print(f"Exported dataset to {path}")
        return

    print("---- NORMAL ----")
    for _ in range(3):
        print(generate_normal_tx())

    print("\n---- FANOUT FRAUD ----")
    for tx in generate_fanout_fraud(0):
        print(tx)

    print("\n---- STRUCTURING FRAUD ----")
    for tx in generate_structuring_fraud(0):
        print(tx)

    print("\n---- LAYERING FRAUD ----")
    for tx in generate_layering_fraud(0):
        print(tx)


if __name__ == "__main__":
    main()

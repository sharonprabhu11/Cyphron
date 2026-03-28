"""
Import simulator CSV transactions into the live Neo4j graph and print query matches.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pipeline.graph.neo4j_client import initialize_neo4j
from pipeline.graph.upsert import upsert_transaction_graph
from pipeline.ingestion.schema import Transaction


def import_transactions(csv_path: Path, limit: int | None = None) -> dict[str, object]:
    client = initialize_neo4j()
    if client is None:
        raise RuntimeError("Neo4j client is unavailable.")

    imported = 0
    account_prefixes: set[str] = set()
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, record in enumerate(reader):
            if limit is not None and index >= limit:
                break
            tx = Transaction.model_validate(record)
            upsert_transaction_graph(client, tx.model_dump())
            imported += 1
            if "-" in tx.account_id:
                account_prefixes.add(tx.account_id.split("-")[0] + "-")

    account_prefix = sorted(account_prefixes)[0] if len(account_prefixes) == 1 else None
    summary = {
        "imported_transactions": imported,
        "fan_out_matches": client.run_fan_out_query(account_prefix=account_prefix, limit=10),
        "structuring_matches": client.run_structuring_query(account_prefix=account_prefix, limit=10),
        "shared_device_matches": client.run_shared_device_query(account_prefix=account_prefix, limit=10),
        "layering_matches": client.run_layering_query(account_prefix=account_prefix, limit=10),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Import simulator transactions into Neo4j Aura/local graph.")
    parser.add_argument("--input", required=True, help="CSV file to import.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    summary = import_transactions(Path(args.input), limit=args.limit)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

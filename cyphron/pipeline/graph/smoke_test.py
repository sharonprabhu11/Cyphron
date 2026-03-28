"""
Runnable Neo4j smoke test for Cyphron.

Seeds a deterministic mule-ring scenario into Neo4j Aura/local Neo4j and prints
the results of the current graph-detection queries.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from datetime import timezone
from typing import Any

# Allow `python pipeline/graph/smoke_test.py` from repo root.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pipeline.graph.demo_scenarios import build_demo_transactions
from pipeline.graph.neo4j_client import initialize_neo4j
from pipeline.graph.upsert import upsert_transaction_graph


def _default_prefix() -> str:
    return f"DEMO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-"


def _print_section(title: str, records: list[dict[str, Any]]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    if not records:
        print("No matches found.")
        return
    print(json.dumps(records, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed and verify the Cyphron Neo4j fraud graph.")
    parser.add_argument(
        "--prefix",
        default=_default_prefix(),
        help="Prefix used for demo account ids so each run stays isolated.",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Run the graph queries without inserting demo events first.",
    )
    args = parser.parse_args()

    client = initialize_neo4j()
    if client is None:
        print("Neo4j client is unavailable. Install backend dependencies first.")
        return 1

    print(f"Using demo prefix: {args.prefix}")

    seeded = 0
    if not args.skip_seed:
        for event in build_demo_transactions(args.prefix):
            upsert_transaction_graph(client, event)
            seeded += 1
        print(f"Seeded {seeded} transactions into Neo4j.")

    fan_out = client.run_fan_out_query(account_prefix=args.prefix)
    structuring = client.run_structuring_query(account_prefix=args.prefix)
    shared_device = client.run_shared_device_query(account_prefix=args.prefix)
    layering = client.run_layering_query(account_prefix=args.prefix)

    _print_section("Fan-out matches", fan_out)
    _print_section("Structuring matches", structuring)
    _print_section("Shared-device matches", shared_device)
    _print_section("Layering matches", layering)

    checks = {
        "fan_out": bool(fan_out),
        "structuring": bool(structuring),
        "shared_device": bool(shared_device),
        "layering": bool(layering),
    }
    print("\nSummary")
    print("-------")
    print(json.dumps({"seeded_transactions": seeded, "checks": checks}, indent=2))

    if all(checks.values()):
        print("\nNeo4j smoke test passed.")
        return 0

    print("\nNeo4j smoke test incomplete: at least one detection query returned no matches.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

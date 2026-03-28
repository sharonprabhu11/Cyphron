"""
Neo4j client utilities for AuraDB/local graph access.
"""

from __future__ import annotations

from typing import Any

try:
    from neo4j import GraphDatabase
except Exception:  # foundation-only: allow running without installed deps
    GraphDatabase = None  # type: ignore

from pipeline.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from pipeline.graph import queries


class Neo4jGraphClient:
    def __init__(self, driver: Any, database: str | None = None) -> None:
        self.driver = driver
        self.database = database

    def _execute_query(self, query: str, parameters: dict[str, Any] | None = None):
        kwargs: dict[str, Any] = {}
        if self.database:
            kwargs["database_"] = self.database
        if parameters is None:
            return self.driver.execute_query(query, **kwargs)
        return self.driver.execute_query(query, parameters, **kwargs)

    def close(self) -> None:
        self.driver.close()

    def ping(self) -> dict[str, Any]:
        records, _, _ = self._execute_query(queries.PING_QUERY)
        return dict(records[0]) if records else {"ok": 0}

    def ensure_constraints(self) -> None:
        for statement in queries.CREATE_CONSTRAINTS:
            self._execute_query(statement)

    def upsert_transaction_graph(self, tx_data: dict[str, Any]) -> dict[str, Any]:
        records, _, _ = self._execute_query(
            queries.UPSERT_TRANSACTION_GRAPH,
            tx_data,
        )
        return dict(records[0]) if records else {}

    def run_fan_out_query(
        self,
        *,
        window: str = "PT60S",
        min_recipients: int = 5,
        limit: int = 25,
        account_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        records, _, _ = self._execute_query(
            queries.FAN_OUT_QUERY,
            {
                "window": window,
                "min_recipients": min_recipients,
                "limit": limit,
                "account_prefix": account_prefix,
            },
        )
        return [dict(record) for record in records]

    def run_structuring_query(
        self,
        *,
        window: str = "PT10M",
        lower_bound: float = 45_000,
        upper_bound: float = 50_000,
        min_txns: int = 3,
        limit: int = 25,
        account_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        records, _, _ = self._execute_query(
            queries.STRUCTURING_QUERY,
            {
                "window": window,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "min_txns": min_txns,
                "limit": limit,
                "account_prefix": account_prefix,
            },
        )
        return [dict(record) for record in records]

    def run_shared_device_query(
        self,
        *,
        limit: int = 25,
        account_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        records, _, _ = self._execute_query(
            queries.SHARED_DEVICE_QUERY,
            {
                "limit": limit,
                "account_prefix": account_prefix,
            },
        )
        return [dict(record) for record in records]

    def fetch_subgraph(
        self,
        *,
        account_id: str,
        hops: int = 2,
        limit: int = 200,
    ) -> dict[str, Any]:
        h = min(max(int(hops), 1), 5)
        query = queries.SUBGRAPH_QUERY.format(hops=h)
        records, _, _ = self._execute_query(
            query,
            {"account_id": account_id, "limit": int(limit)},
        )
        nodes: dict[str, dict[str, Any]] = {}
        links: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for row in records:
            src = row.get("source")
            dst = row.get("target")
            if not src or not dst:
                continue
            tid = str(row.get("txn_id") or "")
            key = (str(src), str(dst), tid)
            if key in seen:
                continue
            seen.add(key)
            sid, did = str(src), str(dst)
            nodes.setdefault(sid, {"id": sid, "label": "Account"})
            nodes.setdefault(did, {"id": did, "label": "Account"})
            links.append(
                {
                    "source": sid,
                    "target": did,
                    "id": tid,
                    "amount": row.get("amount"),
                    "channel": row.get("channel"),
                }
            )
        if not nodes:
            recs, _, _ = self._execute_query(
                "MATCH (c:Account {account_id: $account_id}) RETURN c.account_id AS id LIMIT 1",
                {"account_id": account_id},
            )
            if recs and recs[0].get("id"):
                i = str(recs[0]["id"])
                return {"nodes": [{"id": i, "label": "Account"}], "links": []}
            return {"nodes": [], "links": []}
        return {"nodes": list(nodes.values()), "links": links}

    def run_layering_query(
        self,
        *,
        window: str = "PT30M",
        max_total_gap: str = "PT20M",
        limit: int = 25,
        account_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        records, _, _ = self._execute_query(
            queries.LAYERING_QUERY,
            {
                "window": window,
                "max_total_gap": max_total_gap,
                "limit": limit,
                "account_prefix": account_prefix,
            },
        )
        return [dict(record) for record in records]


_graph_client: Neo4jGraphClient | None = None


def initialize_neo4j():
    global _graph_client

    if _graph_client is not None:
        return _graph_client

    if GraphDatabase is None:
        print("Neo4j client initialized (skipped): neo4j package not installed", flush=True)
        return None

    driver = GraphDatabase.driver(
        NEO4J_URI or "bolt://localhost:7687",
        auth=(NEO4J_USER or "neo4j", NEO4J_PASSWORD or "password"),
    )
    _graph_client = Neo4jGraphClient(driver, database=NEO4J_DATABASE)

    try:
        _graph_client.ensure_constraints()
        _graph_client.ping()
        print("Neo4j client initialized and reachable", flush=True)
    except Exception as exc:  # pragma: no cover - depends on live infra
        print(f"Neo4j client initialized (connectivity pending): {exc}", flush=True)

    return _graph_client


def get_neo4j_client() -> Neo4jGraphClient | None:
    return _graph_client

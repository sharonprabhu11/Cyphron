"""
Decision service that combines GraphSAGE inference with Neo4j rule flags.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from pipeline.config import MODEL_ARTIFACT_PATH, PROCESSED_GRAPH_PATH
from pipeline.graph.neo4j_client import Neo4jGraphClient
from pipeline.ingestion.schema import Transaction
from pipeline.ml.dataset import load_processed_graph_npz
from pipeline.ml.model import FraudModel, torch
from pipeline.models import DecisionResponse
from pipeline.scoring.composite import composite_score
from pipeline.scoring.explainability import explain_decision
from pipeline.scoring.rule_engine import score_rules


class GraphInferenceStore:
    """
    Holds the processed training graph plus precomputed node probabilities.

    The current hackathon backend serves inference from the offline processed
    graph artifact so decision-time scoring is constant-time. That keeps the
    API responsive while still surfacing account and neighborhood risk.
    """

    def __init__(self, model_path: str | Path, graph_path: str | Path) -> None:
        if torch is None:
            raise RuntimeError("torch and torch-geometric are required for backend GNN inference.")

        self.graph_path = Path(graph_path)
        self.model_path = Path(model_path)
        self.model = FraudModel(self.model_path)

        raw = load_processed_graph_npz(self.graph_path)
        self.account_ids = [str(account_id) for account_id in raw["account_ids"].tolist()]
        self.account_to_index = {
            account_id: index for index, account_id in enumerate(self.account_ids)
        }
        self.feature_names = [str(name) for name in raw["feature_names"].tolist()]
        self.edge_index = raw["edge_index"].astype(np.int64)
        self.x = raw["x"].astype(np.float32)
        self.adjacency = self._build_adjacency(self.edge_index, len(self.account_ids))
        self.node_probabilities = self._precompute_probabilities()

    @staticmethod
    def _build_adjacency(edge_index: np.ndarray, node_count: int) -> dict[int, set[int]]:
        adjacency: dict[int, set[int]] = {index: set() for index in range(node_count)}
        for src, dst in edge_index.T:
            adjacency[int(src)].add(int(dst))
        return adjacency

    def _precompute_probabilities(self) -> np.ndarray:
        x_tensor = torch.tensor(self.x, dtype=torch.float32)
        edge_index_tensor = torch.tensor(self.edge_index, dtype=torch.long)
        probabilities = self.model.predict_proba(x_tensor, edge_index_tensor)
        return probabilities.detach().cpu().numpy().astype(np.float32)

    def account_probability(self, account_id: str) -> tuple[float, bool]:
        index = self.account_to_index.get(account_id)
        if index is None:
            return 0.0, False
        return float(self.node_probabilities[index]), True

    def account_features(self, account_id: str) -> np.ndarray | None:
        index = self.account_to_index.get(account_id)
        if index is None:
            return None
        return self.x[index]

    def subgraph_context(
        self,
        focal_accounts: list[str],
        *,
        hops: int = 1,
        limit: int = 12,
    ) -> dict[str, Any]:
        visited_indexes: set[int] = set()
        frontier: set[int] = set()

        for account_id in focal_accounts:
            index = self.account_to_index.get(account_id)
            if index is not None:
                visited_indexes.add(index)
                frontier.add(index)

        for _ in range(hops):
            next_frontier: set[int] = set()
            for index in frontier:
                next_frontier.update(self.adjacency.get(index, set()))
            next_frontier -= visited_indexes
            visited_indexes.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break

        ranked_indexes = sorted(
            visited_indexes,
            key=lambda index: float(self.node_probabilities[index]),
            reverse=True,
        )
        ranked_indexes = ranked_indexes[:limit]
        probabilities = [float(self.node_probabilities[index]) for index in ranked_indexes]
        affected_accounts = [self.account_ids[index] for index in ranked_indexes]
        if probabilities:
            mean_probability = float(sum(probabilities) / len(probabilities))
            max_probability = float(max(probabilities))
            subgraph_probability = max(mean_probability, max_probability)
        else:
            subgraph_probability = 0.0

        return {
            "affected_accounts": affected_accounts,
            "subgraph_probability": subgraph_probability,
        }


class DecisionService:
    def __init__(
        self,
        *,
        model_path: str | Path = MODEL_ARTIFACT_PATH,
        graph_path: str | Path = PROCESSED_GRAPH_PATH,
        neo4j_client: Neo4jGraphClient | None = None,
    ) -> None:
        self.neo4j_client = neo4j_client
        self.inference_store = GraphInferenceStore(model_path=model_path, graph_path=graph_path)

    def _upsert_transaction_graph(self, transaction: Transaction) -> None:
        if self.neo4j_client is None:
            return

        tx_data = {
            "txn_id": transaction.transaction_id,
            "source_account_id": transaction.account_id,
            "destination_account_id": transaction.recipient_id,
            "amount": float(transaction.amount),
            "channel": transaction.channel,
            "currency": transaction.currency,
            "merchant": transaction.merchant_id,
            "created_at": transaction.timestamp.isoformat(),
            "device_id": transaction.device_fingerprint,
            "ip_address": transaction.ip_address,
            "phone_number": transaction.phone_number,
        }
        self.neo4j_client.upsert_transaction_graph(tx_data)

    def decide(self, transaction: Transaction) -> DecisionResponse:
        self._upsert_transaction_graph(transaction)

        source_probability, _ = self.inference_store.account_probability(transaction.account_id)
        recipient_probability, _ = self.inference_store.account_probability(transaction.recipient_id)
        subgraph_context = self.inference_store.subgraph_context(
            [transaction.account_id, transaction.recipient_id],
            hops=1,
            limit=12,
        )
        gnn_probability = max(
            source_probability,
            recipient_probability,
            float(subgraph_context["subgraph_probability"]),
        )

        rule_result = score_rules(self.neo4j_client, transaction)
        focal_account_id = (
            transaction.account_id
            if source_probability >= recipient_probability
            else transaction.recipient_id
        )
        composite_result = composite_score(
            gnn_probability=gnn_probability,
            rule_flags=rule_result["rule_flags"],
        )
        top_factors = explain_decision(
            source_account_probability=source_probability,
            recipient_account_probability=recipient_probability,
            subgraph_probability=float(subgraph_context["subgraph_probability"]),
            gnn_probability=gnn_probability,
            rule_flags=rule_result["rule_flags"],
            feature_names=self.inference_store.feature_names,
            focal_features=self.inference_store.account_features(focal_account_id),
        )

        affected_accounts = list(dict.fromkeys([
            transaction.account_id,
            transaction.recipient_id,
            *subgraph_context["affected_accounts"],
        ]))

        return DecisionResponse(
            transaction_id=transaction.transaction_id,
            source_account_id=transaction.account_id,
            recipient_account_id=transaction.recipient_id,
            gnn_probability=round(gnn_probability, 4),
            source_account_probability=round(source_probability, 4),
            recipient_account_probability=round(recipient_probability, 4),
            subgraph_probability=round(float(subgraph_context["subgraph_probability"]), 4),
            rule_flags=rule_result["rule_flags"],
            rule_matches=rule_result["rule_matches"],
            composite_score=round(float(composite_result["score"]), 4),
            risk_tier=composite_result["risk_tier"],
            recommended_action=composite_result["recommended_action"],
            affected_accounts=affected_accounts,
            top_factors=top_factors,
        )

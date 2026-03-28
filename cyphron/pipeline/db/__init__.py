"""Firestore and BigQuery client setup (no business logic)."""

from pipeline.db.bigquery import init_bigquery
from pipeline.db.firestore import create_dummy_collections, init_firestore

__all__ = ["init_bigquery", "create_dummy_collections", "init_firestore"]

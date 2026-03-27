"""
Neo4j client placeholder.

Minimal working check:
- initialize_neo4j() prints "Neo4j client initialized"
"""

from __future__ import annotations

try:
    from neo4j import GraphDatabase
except Exception:  # foundation-only: allow running without installed deps
    GraphDatabase = None  # type: ignore

from pipeline.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


def initialize_neo4j():
    if GraphDatabase is None:
        print("Neo4j client initialized (skipped): neo4j package not installed", flush=True)
        return None

    # Foundation-only: we create the driver without forcing a live connection.
    driver = GraphDatabase.driver(
        NEO4J_URI or "bolt://localhost:7687",
        auth=(NEO4J_USER or "neo4j", NEO4J_PASSWORD or "password"),
    )
    print("Neo4j client initialized", flush=True)
    return driver


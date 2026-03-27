"""
Cypher queries used by the live fraud graph.
"""

from __future__ import annotations


PING_QUERY = "RETURN 1 AS ok"

CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE",
    "CREATE CONSTRAINT device_id_unique IF NOT EXISTS FOR (d:Device) REQUIRE d.device_id IS UNIQUE",
    "CREATE CONSTRAINT ip_address_unique IF NOT EXISTS FOR (i:IPAddress) REQUIRE i.address IS UNIQUE",
    "CREATE CONSTRAINT phone_number_unique IF NOT EXISTS FOR (p:Phone) REQUIRE p.number IS UNIQUE",
]


UPSERT_TRANSACTION_GRAPH = """
MERGE (src:Account {account_id: $source_account_id})
  ON CREATE SET src.created_at = datetime($created_at)
SET src.last_seen_at = datetime($created_at)
MERGE (dst:Account {account_id: $destination_account_id})
  ON CREATE SET dst.created_at = datetime($created_at)
SET dst.last_seen_at = datetime($created_at)
MERGE (src)-[tx:TRANSFERRED_TO {txn_id: $txn_id}]->(dst)
SET tx.amount = $amount,
    tx.channel = $channel,
    tx.currency = $currency,
    tx.timestamp = datetime($created_at),
    tx.merchant = $merchant
WITH src, dst
FOREACH (_ IN CASE WHEN $device_id IS NULL THEN [] ELSE [1] END |
  MERGE (dev:Device {device_id: $device_id})
    ON CREATE SET dev.created_at = datetime($created_at)
  SET dev.last_seen_at = datetime($created_at)
  MERGE (src)-[:USES_DEVICE]->(dev)
)
FOREACH (_ IN CASE WHEN $ip_address IS NULL THEN [] ELSE [1] END |
  MERGE (ip:IPAddress {address: $ip_address})
    ON CREATE SET ip.created_at = datetime($created_at)
  SET ip.last_seen_at = datetime($created_at)
  MERGE (src)-[:USES_IP]->(ip)
)
FOREACH (_ IN CASE WHEN $phone_number IS NULL THEN [] ELSE [1] END |
  MERGE (phone:Phone {number: $phone_number})
    ON CREATE SET phone.created_at = datetime($created_at)
  SET phone.last_seen_at = datetime($created_at)
  MERGE (src)-[:USES_PHONE]->(phone)
)
RETURN src.account_id AS source_account_id,
       dst.account_id AS destination_account_id,
       $txn_id AS txn_id
"""


FAN_OUT_QUERY = """
MATCH (src:Account)-[tx:TRANSFERRED_TO]->(dst:Account)
WHERE tx.timestamp >= datetime() - duration($window)
WITH src, count(DISTINCT dst) AS recipient_count, collect(DISTINCT dst.account_id) AS recipients
WHERE recipient_count >= $min_recipients
RETURN src.account_id AS account_id, recipient_count, recipients
ORDER BY recipient_count DESC
LIMIT $limit
"""


STRUCTURING_QUERY = """
MATCH (src:Account)-[tx:TRANSFERRED_TO]->(:Account)
WHERE tx.timestamp >= datetime() - duration($window)
  AND tx.amount >= $lower_bound
  AND tx.amount < $upper_bound
WITH src,
     count(tx) AS near_threshold_count,
     collect(tx.amount) AS amounts,
     collect(tx.txn_id) AS txn_ids
WHERE near_threshold_count >= $min_txns
RETURN src.account_id AS account_id, near_threshold_count, amounts, txn_ids
ORDER BY near_threshold_count DESC
LIMIT $limit
"""


SHARED_DEVICE_QUERY = """
MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)
WHERE a1.account_id < a2.account_id
RETURN d.device_id AS device_id,
       collect(DISTINCT a1.account_id) + collect(DISTINCT a2.account_id) AS account_ids,
       count(DISTINCT a1) + count(DISTINCT a2) AS linked_accounts
ORDER BY linked_accounts DESC
LIMIT $limit
"""


LAYERING_QUERY = """
MATCH path = (origin:Account)-[t1:TRANSFERRED_TO]->(:Account)-[t2:TRANSFERRED_TO]->(:Account)-[t3:TRANSFERRED_TO]->(beneficiary:Account)
WHERE t1.timestamp >= datetime() - duration($window)
  AND t2.timestamp >= datetime() - duration($window)
  AND t3.timestamp >= datetime() - duration($window)
  AND duration.between(t1.timestamp, t3.timestamp) <= duration($max_total_gap)
RETURN origin.account_id AS origin_account_id,
       beneficiary.account_id AS beneficiary_account_id,
       [node IN nodes(path) | node.account_id] AS hop_accounts
LIMIT $limit
"""

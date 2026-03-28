"""BigQuery dataset, table, and seed row."""

from __future__ import annotations

from datetime import datetime, timezone

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from pipeline import config

_TEST_TX_ID = "cyphron_bq_seed_row"


def _transactions_schema() -> list[bigquery.SchemaField]:
    return [
        bigquery.SchemaField("transaction_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("account_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("amount", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("currency", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("channel", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("tx_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("device_fingerprint", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ip_address", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("phone_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("geo_hash", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("merchant_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("entity_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("cluster_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("velocity_score", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("hop_count", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("risk_score", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("rule_flags", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("behavior_signature", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("str_generated", "BOOLEAN", mode="NULLABLE"),
    ]


def init_bigquery() -> None:
    project = config.GCP_PROJECT_ID
    dataset_id = config.BIGQUERY_DATASET
    if not project or not dataset_id:
        print("BigQuery skipped: GCP_PROJECT_ID or BIGQUERY_DATASET not set", flush=True)
        return

    client = bigquery.Client(project=project)
    dataset_ref = bigquery.DatasetReference(project, dataset_id)

    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        ds = bigquery.Dataset(dataset_ref)
        ds.location = "US"
        client.create_dataset(ds)

    table_ref = dataset_ref.table("transactions")
    try:
        client.get_table(table_ref)
    except NotFound:
        table = bigquery.Table(table_ref, schema=_transactions_schema())
        client.create_table(table)

    check_sql = (
        f"SELECT COUNT(1) AS c FROM `{project}.{dataset_id}.transactions` "
        f"WHERE transaction_id = @tid"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tid", "STRING", _TEST_TX_ID),
        ]
    )
    rows = list(client.query(check_sql, job_config=job_config).result())
    if rows and rows[0]["c"] and int(rows[0]["c"]) > 0:
        print("BigQuery ready", flush=True)
        return

    ts = datetime.now(timezone.utc)
    seed = {
        "transaction_id": _TEST_TX_ID,
        "account_id": "acct_bq_seed",
        "amount": 100.0,
        "currency": "USD",
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S.%f UTC"),
        "channel": "ach",
        "tx_type": "credit",
        "device_fingerprint": "fp_bq_seed",
        "ip_address": "198.51.100.2",
        "phone_number": "+15551234567",
        "session_id": "sess_bq_seed",
        "geo_hash": "dr5ru",
        "merchant_id": "merch_seed",
        "entity_id": "ent_seed",
        "cluster_id": "cl_seed",
        "velocity_score": 0.15,
        "hop_count": 1,
        "risk_score": 0.08,
        "rule_flags": "none",
        "behavior_signature": "sig_bq",
        "status": "cleared",
        "str_generated": False,
    }

    load_config = bigquery.LoadJobConfig(
        schema=_transactions_schema(),
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    try:
        load_job = client.load_table_from_json([seed], table_ref, job_config=load_config)
        load_job.result()
    except Exception as exc:
        # Sandbox / no-billing projects often block streaming, DML, and some loads; keep API up.
        print(f"BigQuery seed row skipped: {exc}", flush=True)

    print("BigQuery ready", flush=True)

"""
Convert IBM AML-Data HI-Small transactions into Cyphron's canonical CSV schema.

This keeps the training pipeline on a fixed public benchmark while preserving the
rest of Cyphron's preprocessing and GraphSAGE code.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "Timestamp",
    "From Bank",
    "To Bank",
    "Amount Received",
    "Receiving Currency",
    "Amount Paid",
    "Payment Currency",
    "Payment Format",
    "Is Laundering",
}


def _resolve_account_columns(df: pd.DataFrame) -> tuple[str, str]:
    candidate_pairs = [
        ("Account", "Account.1"),
        ("From Account", "To Account"),
    ]
    for source_column, target_column in candidate_pairs:
        if source_column in df.columns and target_column in df.columns:
            return source_column, target_column

    if len(df.columns) >= 5:
        return df.columns[2], df.columns[4]
    raise ValueError("Unable to resolve IBM account identifier columns.")


def _canonicalize_chunk(raw: pd.DataFrame, *, start_index: int) -> pd.DataFrame:
    source_account_column, target_account_column = _resolve_account_columns(raw)
    working = raw.copy()
    working["timestamp"] = pd.to_datetime(working["Timestamp"], format="%Y/%m/%d %H:%M", utc=True)
    working["transaction_id"] = [f"IBM-HI-{index}" for index in range(start_index, start_index + len(working))]
    working["account_id"] = (
        working["From Bank"].astype(str).str.strip()
        + ":"
        + working[source_account_column].astype(str).str.strip()
    )
    working["recipient_id"] = (
        working["To Bank"].astype(str).str.strip()
        + ":"
        + working[target_account_column].astype(str).str.strip()
    )
    working["amount"] = working["Amount Paid"].astype(float)
    working["channel"] = working["Payment Format"].astype(str).str.upper().str.strip()
    working["currency"] = working["Payment Currency"].astype(str).str.strip()
    working["merchant_id"] = ""
    working["device_fingerprint"] = ""
    working["ip_address"] = ""
    working["phone_number"] = ""
    working["session_id"] = ""
    working["cluster_id"] = ""
    working["rule_flags"] = ""
    working["behavior_signature"] = "ibm_hi_small_static"
    working["scenario_id"] = ""
    working["is_fraud"] = working["Is Laundering"].astype(int).astype(bool)
    working["risk_score"] = working["is_fraud"].map({True: 0.99, False: 0.01})

    canonical_columns = [
        "transaction_id",
        "account_id",
        "recipient_id",
        "amount",
        "timestamp",
        "channel",
        "currency",
        "merchant_id",
        "device_fingerprint",
        "ip_address",
        "phone_number",
        "session_id",
        "cluster_id",
        "rule_flags",
        "behavior_signature",
        "scenario_id",
        "is_fraud",
        "risk_score",
    ]
    return working.loc[:, canonical_columns]


def prepare_ibm_hi_small(
    input_path: Path,
    output_path: Path,
    *,
    max_rows: int | None = None,
    negative_sample_rate: float = 1.0,
    seed: int = 42,
    chunksize: int = 100_000,
) -> Path:
    prepared_frames: list[pd.DataFrame] = []
    total_rows = 0

    reader = pd.read_csv(input_path, dtype=str, nrows=max_rows, chunksize=chunksize)
    for raw in reader:
        missing = REQUIRED_COLUMNS.difference(raw.columns)
        if missing:
            raise ValueError(f"Missing required IBM AML columns: {sorted(missing)}")

        working = _canonicalize_chunk(raw, start_index=total_rows)
        total_rows += len(raw)

        if negative_sample_rate < 1.0:
            positive_rows = working[working["is_fraud"]]
            negative_rows = working[~working["is_fraud"]]
            if not negative_rows.empty:
                negative_rows = negative_rows.sample(
                    frac=negative_sample_rate,
                    random_state=seed + len(prepared_frames),
                )
            working = pd.concat([positive_rows, negative_rows], ignore_index=True)

        prepared_frames.append(working)

    prepared = pd.concat(prepared_frames, ignore_index=True)
    prepared = prepared.sort_values("timestamp").reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare IBM AML-Data HI-Small CSV for Cyphron training.")
    parser.add_argument(
        "--input",
        default="data/ibm_hismall_raw/HI-Small_Trans.csv",
        help="Path to the raw IBM HI-Small transaction CSV.",
    )
    parser.add_argument(
        "--output",
        default="data/ibm_hismall_transactions.csv",
        help="Path where the canonical Cyphron CSV should be written.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap on the number of IBM rows to convert for a bounded benchmark slice.",
    )
    parser.add_argument(
        "--negative-sample-rate",
        type=float,
        default=1.0,
        help="Fraction of non-laundering rows to retain while always keeping all laundering rows.",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output_path = prepare_ibm_hi_small(
        Path(args.input),
        Path(args.output),
        max_rows=args.max_rows,
        negative_sample_rate=args.negative_sample_rate,
        seed=args.seed,
    )
    print(output_path)


if __name__ == "__main__":
    main()

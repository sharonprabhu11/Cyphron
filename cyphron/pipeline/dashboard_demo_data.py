"""
Static dashboard payloads for local UI when Firestore / Pub/Sub are not wired.

Enable with CYPHRON_DASHBOARD_DEMO=1 in cyphron/.env — disable to revert to live data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from pipeline.compliance.str_generator import _fallback_report
from pipeline.db.ingestion_store import _sanitize_doc_id
from pipeline.ingestion.schema import Transaction


def _ts_iso(val: Any) -> str:
    if val is None:
        return ""
    if hasattr(val, "isoformat"):
        try:
            return val.isoformat()
        except Exception:
            return str(val)
    return str(val)


def _alert_doc_to_record(doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    alert_id = str(data.get("alert_id") or doc_id)
    pt = str(data.get("pipeline_risk_tier") or "").upper()
    if pt not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        rl = str(data.get("risk_level") or "medium").lower()
        pt = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(rl, "MEDIUM")
    return {
        "alertId": alert_id,
        "accountId": str(data.get("account_id") or ""),
        "amount": float(data.get("amount") or 0),
        "timestamp": str(data.get("timestamp") or ""),
        "channel": str(data.get("channel") or ""),
        "riskScore": float(data.get("risk_score") or 0),
        "riskLevel": str(data.get("risk_level") or "medium"),
        "pipelineRiskTier": pt,
        "ruleFlags": str(data.get("rule_flags") or ""),
        "behaviorSignature": str(data.get("behavior_signature") or ""),
        "status": str(data.get("status") or "open"),
        "deviceFingerprint": str(data.get("device_fingerprint") or ""),
        "ipAddress": str(data.get("ip_address") or ""),
        "clusterId": str(data.get("cluster_id") or ""),
        "createdAt": _ts_iso(data.get("created_at")),
        "updatedAt": _ts_iso(data.get("updated_at")),
    }


def _doc_to_transaction_summary(tx: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in tx.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, (dict, list)):
            out[k] = str(v)
        else:
            out[k] = str(v)
    return out


def _normalize_demo_channel(raw: str) -> str:
    m = (raw or "web").strip().lower()
    return {
        "upi": "UPI",
        "atm": "ATM",
        "web": "WEB",
        "online": "WEB",
        "mobile": "MOBILE",
        "card": "WEB",
    }.get(m, "WEB")


def _build_tx_json_from_alert(data: dict[str, Any]) -> dict[str, Any]:
    """Full `transactions`-collection-shaped doc for report `transactionSummary` (matches Transaction JSON)."""
    tx_id = str(data.get("transaction_id") or "").strip() or "unknown"
    tier_u = str(data.get("pipeline_risk_tier") or "MEDIUM").upper()
    ts_raw = str(data.get("timestamp") or _DEMO_NOW.isoformat())
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except Exception:
        ts = _DEMO_NOW
    flags = [s.strip() for s in str(data.get("rule_flags") or "").split(",") if s.strip()]
    ch = _normalize_demo_channel(str(data.get("channel") or ""))
    tx = Transaction(
        transaction_id=tx_id,
        account_id=str(data.get("account_id") or ""),
        recipient_id=f"payee_{_sanitize_doc_id(str(data.get('cluster_id') or 'recv'))[:28]}",
        amount=float(data.get("amount") or 0),
        currency="INR",
        timestamp=ts,
        channel=ch,  # type: ignore[arg-type]
        tx_type="TRANSFER",
        device_fingerprint=str(data.get("device_fingerprint") or ""),
        ip_address=str(data.get("ip_address") or ""),
        phone_number=None,
        session_id=f"sess_{_sanitize_doc_id(tx_id)}"[:80],
        geo_hash="u09demo00",
        merchant_id=None,
        entity_id=str(data.get("account_id") or "") or None,
        cluster_id=str(data.get("cluster_id") or "") or None,
        velocity_score=float(data.get("risk_score") or 0),
        hop_count=2,
        risk_score=float(data.get("risk_score") or 0),
        rule_flags=flags if flags else None,
        behavior_signature=str(data.get("behavior_signature") or "") or None,
        status="flagged",
        str_generated=tier_u == "CRITICAL",
        is_fraud=tier_u in ("HIGH", "CRITICAL"),
    )
    out: dict[str, Any] = dict(tx.model_dump(mode="json"))
    out["alert_id"] = str(data.get("alert_id") or "")
    out["pipeline_risk_tier"] = tier_u
    out["alert_status"] = str(data.get("status") or "open")
    return out


# --- Demo transaction (ingestion / Firestore transaction doc shape, JSON-friendly) ---

_DEMO_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)

_TX_CRITICAL = Transaction(
    transaction_id="tx_demo_critical_01",
    account_id="acct_demo_8f2k9q",
    recipient_id="merch_demo_recv_01",
    amount=48200.0,
    currency="INR",
    timestamp=datetime(2026, 3, 28, 9, 14, tzinfo=timezone.utc),
    channel="UPI",
    tx_type="TRANSFER",
    device_fingerprint="fp_mob_a3b2",
    ip_address="203.0.113.42",
    phone_number=None,
    session_id="sess_demo_9f2a",
    geo_hash="u09tvq0k1",
    merchant_id=None,
    entity_id="acct_demo_8f2k9q",
    cluster_id="cluster_mule_07",
    velocity_score=0.94,
    hop_count=3,
    risk_score=0.91,
    rule_flags=["velocity", "fan-out", "structuring"],
    behavior_signature="sig_upi_burst_01",
    status="flagged",
    str_generated=True,
    is_fraud=True,
)

# Reasons aligned with pipeline top_factors / rule_flags (for STR "Reasons:" block)
_DEMO_CRITICAL_REASONS = [
    "Fan-out velocity exceeds threshold for source account",
    "Structuring pattern consistent with threshold avoidance",
    "Shared device fingerprint correlated with known mule cluster",
]

_DEMO_STR_TEXT = _fallback_report(
    entity_id=_TX_CRITICAL.account_id,
    risk_score=0.91,
    tier="CRITICAL",
    reasons=_DEMO_CRITICAL_REASONS,
    transaction_summary=_TX_CRITICAL.model_dump(mode="json"),
    mode="Demo",
)

# Firestore-style transaction document (as stored after ingestion snapshot)
_DEMO_TX_DOCS: dict[str, dict[str, Any]] = {
    _sanitize_doc_id(_TX_CRITICAL.transaction_id): _TX_CRITICAL.model_dump(mode="json"),
}

# --- Demo alerts: same field names as Firestore `alerts` documents from ingestion_store ---

_DEMO_ALERT_ROWS: list[tuple[str, dict[str, Any]]] = [
    (
        _sanitize_doc_id("tx_demo_critical_01"),
        {
            "alert_id": "AL-TX-tx_demo_critical_01",
            "transaction_id": "tx_demo_critical_01",
            "account_id": "acct_demo_8f2k9q",
            "amount": 48200.0,
            "timestamp": "2026-03-28T09:14:00+00:00",
            "channel": "upi",
            "risk_score": 0.91,
            "risk_level": "high",
            "pipeline_risk_tier": "CRITICAL",
            "rule_flags": "velocity, fan-out, structuring",
            "behavior_signature": "sig_upi_burst_01",
            "status": "open",
            "device_fingerprint": "fp_mob_a3b2",
            "ip_address": "203.0.113.42",
            "cluster_id": "cluster_mule_07",
            "str_report": _DEMO_STR_TEXT,
            "pdf_path": None,
            "top_factors": [
                {"name": "velocity", "value": 0.94, "detail": _DEMO_CRITICAL_REASONS[0]},
                {"name": "structuring", "value": 0.88, "detail": _DEMO_CRITICAL_REASONS[1]},
                {"name": "device", "value": 0.82, "detail": _DEMO_CRITICAL_REASONS[2]},
            ],
            "created_at": "2026-03-28T09:14:22+00:00",
            "updated_at": "2026-03-28T11:45:00+00:00",
        },
    ),
    (
        _sanitize_doc_id("tx_demo_high_02"),
        {
            "alert_id": "AL-TX-tx_demo_high_02",
            "transaction_id": "tx_demo_high_02",
            "account_id": "acct_demo_1p9x7m",
            "amount": 1250.5,
            "timestamp": "2026-03-28T08:52:00+00:00",
            "channel": "web",
            "risk_score": 0.72,
            "risk_level": "high",
            "pipeline_risk_tier": "HIGH",
            "rule_flags": "velocity, geo",
            "behavior_signature": "sig_web_cross_border_02",
            "status": "open",
            "device_fingerprint": "fp_web_c9d1",
            "ip_address": "203.0.113.10",
            "cluster_id": "cluster_seed_01",
            "top_factors": [{"name": "geo", "value": 0.72, "detail": "Geo velocity mismatch vs home region"}],
            "created_at": "2026-03-28T08:52:18+00:00",
            "updated_at": "2026-03-28T08:55:00+00:00",
        },
    ),
    (
        _sanitize_doc_id("tx_demo_high_03"),
        {
            "alert_id": "AL-TX-tx_demo_high_03",
            "transaction_id": "tx_demo_high_03",
            "account_id": "acct_demo_3n4r8w",
            "amount": 8900.0,
            "timestamp": "2026-03-28T07:20:00+00:00",
            "channel": "atm",
            "risk_score": 0.88,
            "risk_level": "high",
            "pipeline_risk_tier": "HIGH",
            "rule_flags": "structuring, channel hop",
            "behavior_signature": "sig_atm_split_12",
            "status": "investigating",
            "device_fingerprint": "fp_atm_001",
            "ip_address": "198.51.100.8",
            "cluster_id": "cluster_seed_01",
            "top_factors": [
                {"name": "structuring", "value": 0.88, "detail": "Repeated sub-threshold deposits across channels within 24h"},
                {"name": "channel_hop", "value": 0.76, "detail": "Funds moved ATM → UPI within minutes of deposit"},
            ],
            "created_at": "2026-03-28T07:21:05+00:00",
            "updated_at": "2026-03-28T10:02:00+00:00",
        },
    ),
    (
        _sanitize_doc_id("tx_demo_med_04"),
        {
            "alert_id": "AL-TX-tx_demo_med_04",
            "transaction_id": "tx_demo_med_04",
            "account_id": "acct_demo_7k2j1h",
            "amount": 420.0,
            "timestamp": "2026-03-27T22:10:00+00:00",
            "channel": "atm",
            "risk_score": 0.41,
            "risk_level": "medium",
            "pipeline_risk_tier": "MEDIUM",
            "rule_flags": "geo",
            "behavior_signature": "sig_atm_night_04",
            "status": "acknowledged",
            "device_fingerprint": "fp_atm_002",
            "ip_address": "192.0.2.55",
            "cluster_id": "cluster_iso_03",
            "created_at": "2026-03-27T22:11:00+00:00",
            "updated_at": "2026-03-28T06:00:00+00:00",
        },
    ),
    (
        _sanitize_doc_id("tx_demo_high_05"),
        {
            "alert_id": "AL-TX-tx_demo_high_05",
            "transaction_id": "tx_demo_high_05",
            "account_id": "acct_demo_8f2k9q",
            "amount": 12000.0,
            "timestamp": "2026-03-27T18:45:00+00:00",
            "channel": "upi",
            "risk_score": 0.85,
            "risk_level": "high",
            "pipeline_risk_tier": "HIGH",
            "rule_flags": "velocity",
            "behavior_signature": "sig_upi_burst_01",
            "status": "open",
            "device_fingerprint": "fp_mob_a3b2",
            "ip_address": "203.0.113.42",
            "cluster_id": "cluster_mule_07",
            "created_at": "2026-03-27T18:46:12+00:00",
            "updated_at": "2026-03-27T18:46:12+00:00",
        },
    ),
    (
        _sanitize_doc_id("tx_demo_med_06"),
        {
            "alert_id": "AL-TX-tx_demo_med_06",
            "transaction_id": "tx_demo_med_06",
            "account_id": "acct_demo_0z9y8x",
            "amount": 210000.0,
            "timestamp": "2026-03-27T14:00:00+00:00",
            "channel": "web",
            "risk_score": 0.79,
            "risk_level": "medium",
            "pipeline_risk_tier": "MEDIUM",
            "rule_flags": "amount threshold, new beneficiary",
            "behavior_signature": "sig_wire_new_09",
            "status": "open",
            "device_fingerprint": "fp_desk_77",
            "ip_address": "203.0.113.201",
            "cluster_id": "cluster_biz_11",
            "created_at": "2026-03-27T14:02:00+00:00",
            "updated_at": "2026-03-27T14:02:00+00:00",
        },
    ),
    (
        _sanitize_doc_id("tx_demo_med_07"),
        {
            "alert_id": "AL-TX-tx_demo_med_07",
            "transaction_id": "tx_demo_med_07",
            "account_id": "acct_demo_5t6u7v",
            "amount": 3300.0,
            "timestamp": "2026-03-27T11:30:00+00:00",
            "channel": "mobile",
            "risk_score": 0.55,
            "risk_level": "medium",
            "pipeline_risk_tier": "MEDIUM",
            "rule_flags": "device mismatch",
            "behavior_signature": "sig_mob_dev_02",
            "status": "investigating",
            "device_fingerprint": "fp_mob_new",
            "ip_address": "198.51.100.22",
            "cluster_id": "cluster_iso_03",
            "created_at": "2026-03-27T11:31:00+00:00",
            "updated_at": "2026-03-27T15:20:00+00:00",
        },
    ),
    (
        _sanitize_doc_id("tx_demo_low_08"),
        {
            "alert_id": "AL-TX-tx_demo_low_08",
            "transaction_id": "tx_demo_low_08",
            "account_id": "acct_demo_2b4c6d",
            "amount": 99.99,
            "timestamp": "2026-03-26T16:00:00+00:00",
            "channel": "web",
            "risk_score": 0.28,
            "risk_level": "low",
            "pipeline_risk_tier": "LOW",
            "rule_flags": "round amount",
            "behavior_signature": "sig_card_low_88",
            "status": "closed",
            "device_fingerprint": "fp_card_aa",
            "ip_address": "192.0.2.1",
            "cluster_id": "cluster_retail_02",
            "created_at": "2026-03-26T16:01:00+00:00",
            "updated_at": "2026-03-27T09:00:00+00:00",
        },
    ),
]

# Extra synthetic transactions (no matching alert) for channel / timeseries analytics
_DEMO_TX_EXTRA: list[dict[str, Any]] = []
for i in range(24):
    ts = (_DEMO_NOW - timedelta(hours=23 - i)).isoformat()
    _DEMO_TX_EXTRA.append(
        {
            "transaction_id": f"tx_demo_synth_{i:02d}",
            "account_id": f"acct_demo_synth_{i % 5}",
            "recipient_id": "merch_demo_pool",
            "amount": float(1200 + (i * 137) % 8000),
            "currency": "INR",
            "timestamp": ts,
            "channel": ["UPI", "ATM", "WEB", "MOBILE"][i % 4],
            "tx_type": "TRANSFER",
            "device_fingerprint": f"fp_synth_{i}",
            "ip_address": "198.51.100.1",
            "phone_number": None,
            "session_id": f"sess_synth_{i}",
            "geo_hash": None,
            "merchant_id": None,
            "entity_id": None,
            "cluster_id": "cluster_demo",
            "velocity_score": None,
            "hop_count": None,
            "risk_score": 0.35 + (i % 7) * 0.08,
            "rule_flags": [],
            "behavior_signature": "demo_synth",
            "status": "posted",
            "str_generated": False,
            "is_fraud": i % 5 == 0,
        }
    )
for d in _DEMO_TX_EXTRA:
    _DEMO_TX_DOCS[_sanitize_doc_id(d["transaction_id"])] = d


def _demo_sort_key(data: dict[str, Any]) -> float:
    u = data.get("updated_at") or data.get("created_at")
    if hasattr(u, "timestamp"):
        return float(u.timestamp())
    if isinstance(u, str):
        try:
            return datetime.fromisoformat(u.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0
    return 0.0


def _find_demo_alert(alert_key: str) -> tuple[str, dict[str, Any]] | None:
    for doc_id, data in _DEMO_ALERT_ROWS:
        if str(data.get("alert_id") or "") == alert_key:
            return doc_id, data
        if doc_id == alert_key:
            return doc_id, data
    if alert_key.startswith("AL-TX-"):
        tid = alert_key.removeprefix("AL-TX-")
        for doc_id, data in _DEMO_ALERT_ROWS:
            if doc_id == tid:
                return doc_id, data
    tid = _sanitize_doc_id(alert_key)
    for doc_id, data in _DEMO_ALERT_ROWS:
        if doc_id == tid:
            return doc_id, data
    return None


def list_alerts_demo(
    status: str | None,
    risk_level: str | None,
    since: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except Exception:
            since_dt = None

    rows: list[tuple[float, dict[str, Any]]] = []
    for doc_id, data in _DEMO_ALERT_ROWS:
        if status and str(data.get("status") or "") != status:
            continue
        if risk_level and str(data.get("risk_level") or "") != risk_level:
            continue
        ts_raw = data.get("timestamp") or data.get("updated_at") or data.get("created_at")
        if since_dt and ts_raw:
            try:
                if isinstance(ts_raw, str):
                    tsd = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    if tsd < since_dt:
                        continue
            except Exception:
                pass
        rows.append((_demo_sort_key(data), _alert_doc_to_record(doc_id, data)))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows[offset : offset + limit]]


def get_alert_demo(alert_id: str) -> dict[str, Any] | None:
    found = _find_demo_alert(alert_id)
    if not found:
        return None
    doc_id, data = found
    return _alert_doc_to_record(doc_id, data)


def get_alert_report_demo(alert_id: str, base_url: str) -> dict[str, Any] | None:
    found = _find_demo_alert(alert_id)
    if not found:
        return None
    doc_id, data = found
    tier = str(data.get("pipeline_risk_tier") or "MEDIUM").upper()
    if tier not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        tier = "MEDIUM"

    tx_data = dict(_DEMO_TX_DOCS.get(doc_id, {}))
    if not tx_data:
        tx_data = _build_tx_json_from_alert(data)
    else:
        tx_data = dict(tx_data)
        tx_data.setdefault("alert_id", str(data.get("alert_id") or ""))
        tx_data.setdefault("pipeline_risk_tier", tier)
        tx_data.setdefault("alert_status", str(data.get("status") or "open"))

    str_report = data.get("str_report")
    reasons: list[str] = []
    for f in data.get("top_factors") or []:
        if isinstance(f, dict) and f.get("detail"):
            reasons.append(str(f["detail"]))
    if not reasons and data.get("rule_flags"):
        reasons = [s.strip() for s in str(data["rule_flags"]).split(",") if s.strip()]
    if not reasons:
        reasons = ["Automated scoring flagged this transaction for compliance review (demo data)."]

    base = base_url.rstrip("/")
    pdf_url = (
        f"{base}/api/v1/alerts/{quote(alert_id, safe='')}/report/pdf"
        if tier == "CRITICAL" and str_report
        else None
    )
    entity_id = str(data.get("account_id") or "")
    summary = _doc_to_transaction_summary(tx_data)

    return {
        "alertId": str(data.get("alert_id") or alert_id),
        "entityId": entity_id,
        "riskScore": float(data.get("risk_score") or 0),
        "riskTier": tier,
        "reasons": reasons,
        "transactionSummary": summary,
        "strReport": str_report,
        "generatedAt": _ts_iso(data.get("updated_at")) or _DEMO_NOW.isoformat(),
        "pdfDownloadPath": pdf_url,
    }


def analytics_summary_demo() -> list[dict[str, Any]]:
    alerts_24 = sum(
        1
        for _, d in _DEMO_ALERT_ROWS
        if _parse_ts_demo(d.get("timestamp") or d.get("created_at")) is not None
        and _parse_ts_demo(d.get("timestamp") or d.get("created_at")) >= _DEMO_NOW - timedelta(hours=24)
    )
    high_risk = sum(1 for _, d in _DEMO_ALERT_ROWS if str(d.get("risk_level") or "") == "high")
    open_cases = sum(1 for _, d in _DEMO_ALERT_ROWS if str(d.get("status") or "") == "open")
    tx_24 = sum(
        1
        for d in _DEMO_TX_DOCS.values()
        if _parse_ts_demo(d.get("timestamp")) is not None
        and _parse_ts_demo(d.get("timestamp")) >= _DEMO_NOW - timedelta(hours=24)
    )

    def fmt_num(n: int) -> str:
        if n >= 1000:
            s = f"{n / 1000:.1f}k"
            return s.replace(".0k", "k")
        return str(n)

    return [
        {
            "id": "alerts",
            "label": "Alerts (24h)",
            "value": str(max(alerts_24, 3)),
            "deltaLabel": "demo",
            "deltaPositive": True,
            "tint": "blueMuted",
        },
        {
            "id": "tx-in",
            "label": "Transactions in",
            "value": fmt_num(max(tx_24, len(_DEMO_TX_DOCS))),
            "deltaLabel": "24h",
            "deltaPositive": True,
            "tint": "greenMuted",
        },
        {
            "id": "high-risk",
            "label": "High risk",
            "value": str(high_risk),
            "deltaLabel": "all alerts",
            "deltaPositive": False,
            "tint": "blueMuted",
        },
        {
            "id": "cases",
            "label": "Open cases",
            "value": str(open_cases),
            "deltaLabel": "queue",
            "deltaPositive": open_cases < 50,
            "tint": "greenMuted",
        },
    ]


def _parse_ts_demo(val: Any) -> datetime | None:
    if val is None:
        return None
    if hasattr(val, "timestamp"):
        dt = val
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _bucket_rule_flag_demo(flag_blob: str) -> str:
    low = flag_blob.lower()
    if "struct" in low:
        return "Structuring"
    if "fan" in low or "velocity" in low:
        return "Fan-out / velocity"
    if "geo" in low or "channel" in low:
        return "Geo / channel"
    if "mule" in low or "identity" in low or "device" in low:
        return "Mule / identity"
    return "Other"


def analytics_fraud_signals_demo() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    colors = {
        "Structuring": "#2563eb",
        "Fan-out / velocity": "#16a34a",
        "Geo / channel": "#38bdf8",
        "Mule / identity": "#22c55e",
        "Other": "#94a3b8",
    }
    for _, d in _DEMO_ALERT_ROWS:
        flags = str(d.get("rule_flags") or "")
        b = _bucket_rule_flag_demo(flags) if flags else "Other"
        counts[b] = counts.get(b, 0) + 1
    if not counts:
        counts = {"Other": 1}
    return [{"name": k, "value": v, "color": colors.get(k, "#94a3b8")} for k, v in counts.items()]


def analytics_channel_exposure_demo() -> list[dict[str, Any]]:
    by_ch: dict[str, dict[str, float | int]] = {}
    for d in _DEMO_TX_DOCS.values():
        ch = str(d.get("channel") or "UNKNOWN").upper()
        amt = float(d.get("amount") or 0)
        entry = by_ch.setdefault(ch, {"volume": 0.0, "flagged": 0})
        entry["volume"] = float(entry["volume"]) + amt
        rs = d.get("risk_score")
        if rs is not None and float(rs) > 0.5:
            entry["flagged"] = int(entry["flagged"]) + 1

    total_vol = sum(float(v["volume"]) for v in by_ch.values()) or 1.0
    rows: list[dict[str, Any]] = []
    for ch, agg in sorted(by_ch.items(), key=lambda x: -float(x[1]["volume"])):
        vol = float(agg["volume"])
        share = int(round(100 * vol / total_vol))
        flagged = int(agg["flagged"])
        vol_label = f"{int(vol):,}"
        exp_label = f"{int(vol / 1000)}k INR" if vol >= 1000 else f"{int(vol)} INR"
        highlight = "high" if share >= 30 else ("medium" if share >= 15 else None)
        rows.append(
            {
                "id": ch.lower(),
                "channel": ch,
                "volume": int(vol),
                "volumeLabel": vol_label,
                "sharePct": share,
                "flaggedCount": flagged,
                "exposureFlaggedLabel": exp_label,
                **({"highlight": highlight} if highlight else {}),
            }
        )
    return rows or [
        {
            "id": "upi",
            "channel": "UPI",
            "volume": 0,
            "volumeLabel": "0",
            "sharePct": 0,
            "flaggedCount": 0,
            "exposureFlaggedLabel": "0 INR",
        }
    ]


def analytics_risk_volume_demo() -> list[dict[str, Any]]:
    now = _DEMO_NOW.date()
    days = [(now - timedelta(days=i)) for i in range(6, -1, -1)]
    buckets = {d.isoformat(): {"volume": 0.0, "alerts": 0, "high": 0} for d in days}
    for _, d in _DEMO_ALERT_ROWS:
        dt = _parse_ts_demo(d.get("timestamp") or d.get("created_at"))
        if not dt:
            continue
        key = dt.date().isoformat()
        if key not in buckets:
            continue
        buckets[key]["volume"] += float(d.get("amount") or 0)
        buckets[key]["alerts"] += 1
        if str(d.get("risk_level") or "") == "high":
            buckets[key]["high"] += 1
    out: list[dict[str, Any]] = []
    for d in days:
        k = d.isoformat()
        b = buckets[k]
        vol = b["volume"]
        alert_n = max(1, int(b["alerts"]))
        risk_pct = int(round(100 * int(b["high"]) / alert_n))
        out.append(
            {
                "label": d.strftime("%a"),
                "volume": int(vol) if vol else int(500 + hash(k) % 400),
                "riskPct": min(99, max(4, risk_pct if b["alerts"] else 8)),
            }
        )
    return out


def analytics_transactions_timeseries_demo() -> list[dict[str, Any]]:
    start = _DEMO_NOW - timedelta(hours=24)
    buckets = [{"total": 0, "highRisk": 0} for _ in range(24)]
    for d in _DEMO_TX_DOCS.values():
        dt = _parse_ts_demo(d.get("timestamp"))
        if not dt:
            continue
        dt = dt.astimezone(timezone.utc)
        if dt < start.astimezone(timezone.utc):
            continue
        slot = int((dt - start.astimezone(timezone.utc)).total_seconds() // 3600)
        if not (0 <= slot < 24):
            continue
        buckets[slot]["total"] += 1
        rs = d.get("risk_score")
        if rs is not None and float(rs) > 0.55:
            buckets[slot]["highRisk"] += 1
    points: list[dict[str, int]] = []
    for i in range(24):
        label = (start + timedelta(hours=i, minutes=30)).astimezone(timezone.utc).strftime("%H:%M")
        b = buckets[i]
        cleared = max(0, b["total"] - b["highRisk"])
        points.append({"t": label, "total": b["total"], "highRisk": b["highRisk"], "cleared": cleared})
    if sum(p["total"] for p in points) == 0:
        return [
            {"t": f"{i:02d}:00", "total": 2 + i % 5, "highRisk": i % 3, "cleared": max(0, (2 + i % 5) - (i % 3))}
            for i in range(24)
        ]
    return points

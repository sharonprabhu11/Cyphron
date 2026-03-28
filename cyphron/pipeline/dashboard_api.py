"""
REST API for the Next.js dashboard: alerts, analytics, graph reads, simulator.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from pipeline import config
from pipeline.compliance.str_attach import build_str_and_pdf
from pipeline.db.ingestion_store import _sanitize_doc_id
from pipeline.graph.neo4j_client import get_neo4j_client, initialize_neo4j
from pipeline.ingestion.publisher import publish_message
from pipeline.ingestion.schema import Transaction
from pipeline.models import DecisionFactor, DecisionResponse
from pipeline.scoring.composite import ACTION_BY_TIER

router = APIRouter(tags=["dashboard-v1"])

_SEED_DOC_ID = "cyphron_db_seed"


def _firestore_db():
    try:
        from pipeline.db.firestore import init_firestore

        init_firestore()
        from firebase_admin import firestore

        return firestore.client()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {exc}") from exc


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
    return {
        "alertId": alert_id,
        "accountId": str(data.get("account_id") or ""),
        "amount": float(data.get("amount") or 0),
        "timestamp": str(data.get("timestamp") or ""),
        "channel": str(data.get("channel") or ""),
        "riskScore": float(data.get("risk_score") or 0),
        "riskLevel": str(data.get("risk_level") or "medium"),
        "ruleFlags": str(data.get("rule_flags") or ""),
        "behaviorSignature": str(data.get("behavior_signature") or ""),
        "status": str(data.get("status") or "open"),
        "deviceFingerprint": str(data.get("device_fingerprint") or ""),
        "ipAddress": str(data.get("ip_address") or ""),
        "clusterId": str(data.get("cluster_id") or ""),
        "createdAt": _ts_iso(data.get("created_at")),
        "updatedAt": _ts_iso(data.get("updated_at")),
    }


def _find_alert(db, alert_key: str) -> tuple[Any, dict[str, Any]] | tuple[None, None]:
    try:
        q = db.collection("alerts").where("alert_id", "==", alert_key).limit(1).stream()
        for snap in q:
            return snap.reference, snap.to_dict() or {}
    except Exception:
        pass
    ref = db.collection("alerts").document(alert_key)
    snap = ref.get()
    if snap.exists:
        return ref, snap.to_dict() or {}
    if alert_key.startswith("AL-TX-"):
        tid = alert_key.removeprefix("AL-TX-")
        ref2 = db.collection("alerts").document(tid)
        s2 = ref2.get()
        if s2.exists:
            return ref2, s2.to_dict() or {}
    tid = _sanitize_doc_id(alert_key)
    ref3 = db.collection("alerts").document(tid)
    s3 = ref3.get()
    if s3.exists:
        return ref3, s3.to_dict() or {}
    return None, None


def _get_decision_service(request: Request):
    svc = getattr(request.app.state, "decision_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Decision service is not ready.")
    return svc


def _public_backend_base(request: Request) -> str:
    base = (os.getenv("PUBLIC_BACKEND_URL") or str(request.base_url)).rstrip("/")
    return base


# --- Alerts ---


@router.get("/alerts")
def list_alerts(
    status: str | None = None,
    risk_level: str | None = None,
    since: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10_000),
) -> list[dict[str, Any]]:
    db = _firestore_db()
    snaps = list(db.collection("alerts").limit(500).stream())
    rows: list[tuple[float, dict[str, Any]]] = []
    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except Exception:
            since_dt = None
    for snap in snaps:
        if snap.id == _SEED_DOC_ID:
            continue
        data = snap.to_dict() or {}
        if status and str(data.get("status") or "") != status:
            continue
        if risk_level and str(data.get("risk_level") or "") != risk_level:
            continue
        ts_raw = data.get("timestamp") or data.get("updated_at") or data.get("created_at")
        if since_dt and ts_raw:
            try:
                if hasattr(ts_raw, "timestamp"):
                    if ts_raw.tzinfo is None:
                        ts_raw = ts_raw.replace(tzinfo=timezone.utc)
                    if ts_raw < since_dt.astimezone(timezone.utc):
                        continue
                elif isinstance(ts_raw, str):
                    tsd = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    if tsd < since_dt:
                        continue
            except Exception:
                pass
        sort_key = 0.0
        u = data.get("updated_at") or data.get("created_at")
        if hasattr(u, "timestamp"):
            sort_key = float(u.timestamp())
        rows.append((sort_key, _alert_doc_to_record(snap.id, data)))
    rows.sort(key=lambda x: x[0], reverse=True)
    sliced = [r[1] for r in rows[offset : offset + limit]]
    return sliced


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str) -> dict[str, Any]:
    db = _firestore_db()
    ref, data = _find_alert(db, alert_id)
    if ref is None or not data:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_doc_to_record(ref.id, data)


class AlertPatchBody(BaseModel):
    status: Literal["open", "acknowledged", "investigating", "closed"]


@router.patch("/alerts/{alert_id}")
def patch_alert(alert_id: str, body: AlertPatchBody) -> dict[str, Any]:
    db = _firestore_db()
    from google.cloud.firestore import SERVER_TIMESTAMP

    ref, data = _find_alert(db, alert_id)
    if ref is None or not data:
        raise HTTPException(status_code=404, detail="Alert not found")
    ref.set({"status": body.status, "updated_at": SERVER_TIMESTAMP}, merge=True)
    snap = ref.get()
    return _alert_doc_to_record(ref.id, snap.to_dict() or {})


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


@router.get("/alerts/{alert_id}/report")
def get_alert_report(alert_id: str, request: Request) -> dict[str, Any]:
    db = _firestore_db()
    ref, data = _find_alert(db, alert_id)
    if ref is None or not data:
        raise HTTPException(status_code=404, detail="Alert not found")

    tier = str(data.get("pipeline_risk_tier") or "MEDIUM").upper()
    if tier not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        tier = "MEDIUM"

    tx_id = str(data.get("transaction_id") or "")
    tid = _sanitize_doc_id(tx_id)
    tx_snap = db.collection("transactions").document(tid).get()
    tx_data = tx_snap.to_dict() if tx_snap.exists else {}

    str_report = data.get("str_report")
    pdf_path = data.get("pdf_path")
    reasons: list[str] = []
    for f in data.get("top_factors") or []:
        if isinstance(f, dict) and f.get("detail"):
            reasons.append(str(f["detail"]))
    if not reasons and data.get("rule_flags"):
        reasons = [s.strip() for s in str(data["rule_flags"]).split(",") if s.strip()]

    if str_report is None and tier == "CRITICAL" and tx_data:
        try:
            tx = Transaction.model_validate(tx_data)
            base = DecisionResponse(
                transaction_id=tx.transaction_id,
                source_account_id=str(data.get("account_id") or tx.account_id),
                recipient_account_id=tx.recipient_id,
                gnn_probability=float(data.get("risk_score") or 0),
                source_account_probability=float(data.get("risk_score") or 0),
                recipient_account_probability=float(data.get("risk_score") or 0),
                subgraph_probability=float(data.get("risk_score") or 0),
                rule_flags=[s.strip() for s in str(data.get("rule_flags") or "").split(",") if s.strip()],
                composite_score=float(data.get("risk_score") or 0),
                risk_tier="CRITICAL",
                recommended_action=str(ACTION_BY_TIER["CRITICAL"]),
                affected_accounts=[str(data.get("account_id") or tx.account_id)],
                top_factors=[DecisionFactor(name="ingestion", value=1.0, detail=r) for r in reasons]
                or [DecisionFactor(name="ingestion", value=1.0, detail="Critical risk alert")],
            )
            str_report, pdf_path = build_str_and_pdf(base, tx)
            from google.cloud.firestore import SERVER_TIMESTAMP

            ref.set(
                {
                    "str_report": str_report,
                    "pdf_path": pdf_path,
                    "updated_at": SERVER_TIMESTAMP,
                },
                merge=True,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"STR generation failed: {exc}") from exc

    base_url = _public_backend_base(request)
    pdf_url = (
        f"{base_url}/api/v1/alerts/{quote(alert_id, safe='')}/report/pdf"
        if tier == "CRITICAL" and str_report
        else None
    )

    entity_id = str(data.get("account_id") or "")
    summary = _doc_to_transaction_summary(tx_data) if tx_data else {}

    return {
        "alertId": str(data.get("alert_id") or alert_id),
        "entityId": entity_id,
        "riskScore": float(data.get("risk_score") or 0),
        "riskTier": tier,
        "reasons": reasons,
        "transactionSummary": summary,
        "strReport": str_report,
        "generatedAt": _ts_iso(data.get("updated_at")) or datetime.now(timezone.utc).isoformat(),
        "pdfDownloadPath": pdf_url,
    }


@router.get("/alerts/{alert_id}/report/pdf")
def get_alert_report_pdf(alert_id: str) -> FileResponse:
    db = _firestore_db()
    ref, data = _find_alert(db, alert_id)
    if ref is None or not data:
        raise HTTPException(status_code=404, detail="Alert not found")
    tier = str(data.get("pipeline_risk_tier") or "").upper()
    path_str = data.get("pdf_path")
    if path_str and Path(str(path_str)).is_file():
        return FileResponse(
            str(path_str),
            media_type="application/pdf",
            filename=f"STR_{_sanitize_doc_id(alert_id)}.pdf",
        )
    if tier != "CRITICAL":
        raise HTTPException(status_code=404, detail="PDF not available for this alert")
    raise HTTPException(status_code=404, detail="PDF not found on disk; regenerate via report endpoint")


# --- Analytics ---


def _parse_ts(val: Any) -> datetime | None:
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


def _bucket_rule_flag(flag_blob: str) -> str:
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


@router.get("/analytics/summary")
def analytics_summary() -> list[dict[str, Any]]:
    db = _firestore_db()
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    alerts = [s for s in db.collection("alerts").stream() if s.id != _SEED_DOC_ID]
    txs = [s for s in db.collection("transactions").stream() if s.id != _SEED_DOC_ID]

    def in_window(ts: Any) -> bool:
        dt = _parse_ts(ts)
        return dt is not None and dt >= day_ago

    alerts_24 = 0
    high_risk = 0
    for s in alerts:
        d = s.to_dict() or {}
        if in_window(d.get("timestamp") or d.get("created_at")):
            alerts_24 += 1
        if str(d.get("risk_level") or "") == "high":
            high_risk += 1

    tx_24 = sum(
        1
        for s in txs
        if in_window((s.to_dict() or {}).get("timestamp") or (s.to_dict() or {}).get("ingested_at"))
    )
    open_cases = sum(1 for s in alerts if str((s.to_dict() or {}).get("status") or "") == "open")

    def fmt_num(n: int) -> str:
        if n >= 1000:
            return f"{n / 1000:.1f}k".replace(".0k", "k")
        return str(n)

    return [
        {
            "id": "alerts",
            "label": "Alerts (24h)",
            "value": str(alerts_24),
            "deltaLabel": "live",
            "deltaPositive": True,
            "tint": "blueMuted",
        },
        {
            "id": "tx-in",
            "label": "Transactions in",
            "value": fmt_num(max(tx_24, len(txs))),
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


@router.get("/analytics/fraud-signals")
def analytics_fraud_signals() -> list[dict[str, Any]]:
    db = _firestore_db()
    counts: dict[str, int] = {}
    colors = {
        "Structuring": "#2563eb",
        "Fan-out / velocity": "#16a34a",
        "Geo / channel": "#38bdf8",
        "Mule / identity": "#22c55e",
        "Other": "#94a3b8",
    }
    for s in db.collection("alerts").stream():
        if s.id == _SEED_DOC_ID:
            continue
        flags = str((s.to_dict() or {}).get("rule_flags") or "")
        if not flags:
            b = "Other"
        else:
            b = _bucket_rule_flag(flags)
        counts[b] = counts.get(b, 0) + 1
    if not counts:
        counts = {"Other": 1}
    return [{"name": k, "value": v, "color": colors.get(k, "#94a3b8")} for k, v in counts.items()]


@router.get("/analytics/channel-exposure")
def analytics_channel_exposure() -> list[dict[str, Any]]:
    db = _firestore_db()
    by_ch: dict[str, dict[str, float | int]] = {}
    for s in db.collection("transactions").stream():
        if s.id == _SEED_DOC_ID:
            continue
        d = s.to_dict() or {}
        ch = str(d.get("channel") or "UNKNOWN").upper()
        amt = float(d.get("amount") or 0)
        entry = by_ch.setdefault(ch, {"volume": 0.0, "flagged": 0})
        entry["volume"] = float(entry["volume"]) + amt
        if d.get("is_fraud") or d.get("risk_score"):
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
    if not rows:
        rows = [
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
    return rows


@router.get("/analytics/risk-volume")
def analytics_risk_volume() -> list[dict[str, Any]]:
    db = _firestore_db()
    now = datetime.now(timezone.utc).date()
    days = [(now - timedelta(days=i)) for i in range(6, -1, -1)]
    buckets = {d.isoformat(): {"volume": 0.0, "alerts": 0, "high": 0} for d in days}
    for s in db.collection("alerts").stream():
        if s.id == _SEED_DOC_ID:
            continue
        d = s.to_dict() or {}
        dt = _parse_ts(d.get("timestamp") or d.get("created_at"))
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


@router.get("/analytics/transactions-timeseries")
def analytics_transactions_timeseries() -> list[dict[str, Any]]:
    db = _firestore_db()
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    buckets = [{"total": 0, "highRisk": 0} for _ in range(24)]
    for s in db.collection("transactions").limit(3000).stream():
        if s.id == _SEED_DOC_ID:
            continue
        d = s.to_dict() or {}
        dt = _parse_ts(d.get("timestamp"))
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


# --- Graph + simulator ---


@router.get("/graph/subgraph")
def graph_subgraph(
    account_id: str = Query(..., min_length=1),
    hops: int = Query(2, ge=1, le=5),
    limit: int = Query(200, ge=1, le=500),
) -> dict[str, Any]:
    client = get_neo4j_client() or initialize_neo4j()
    if client is None:
        raise HTTPException(status_code=503, detail="Neo4j not configured")
    try:
        return client.fetch_subgraph(account_id=account_id, hops=hops, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/graph/insights")
def graph_insights(
    account_prefix: str | None = None,
) -> dict[str, Any]:
    client = get_neo4j_client() or initialize_neo4j()
    if client is None:
        raise HTTPException(status_code=503, detail="Neo4j not configured")
    try:
        return {
            "fanOut": client.run_fan_out_query(account_prefix=account_prefix, limit=15),
            "structuring": client.run_structuring_query(account_prefix=account_prefix, limit=15),
            "sharedDevice": client.run_shared_device_query(account_prefix=account_prefix, limit=15),
            "layering": client.run_layering_query(account_prefix=account_prefix, limit=15),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class SimulatorPublishBody(BaseModel):
    fraud_type: Literal["normal", "fanout", "structuring"] | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)


@router.post("/simulator/publish")
def simulator_publish(body: SimulatorPublishBody) -> dict[str, Any]:
    from simulator import tx_simulator

    tx_dict: dict[str, Any]
    if body.fraud_type == "fanout":
        txs = tx_simulator.generate_fanout_fraud()
        tx_dict = dict(txs[0]) if txs else dict(tx_simulator.generate_normal_tx())
    elif body.fraud_type == "structuring":
        txs = tx_simulator.generate_structuring_fraud()
        tx_dict = dict(txs[0]) if txs else dict(tx_simulator.generate_normal_tx())
    else:
        tx_dict = dict(tx_simulator.generate_normal_tx())
    tx_dict.update(body.overrides or {})
    publish_message(tx_dict)
    return {"transactionId": str(tx_dict.get("transaction_id") or ""), "published": True}


@router.get("/ingestion/health")
def ingestion_health() -> dict[str, Any]:
    pid = config.GCP_PROJECT_ID or "cyphron"
    topic = config.PUBSUB_TOPIC or "transactions"
    sub = config.PUBSUB_SUBSCRIPTION or "transactions-sub"
    return {
        "projectId": pid,
        "topic": topic,
        "subscription": sub,
        "topicPath": f"projects/{pid}/topics/{topic}",
        "subscriptionPath": f"projects/{pid}/subscriptions/{sub}",
    }

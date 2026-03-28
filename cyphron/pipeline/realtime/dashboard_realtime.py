"""
WebSocket hub + debounced Firestore snapshot listeners for dashboard refresh pings.

Single-process MVP: no Redis. See docs/REALTIME.md for multi-instance notes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from fastapi import WebSocket

from pipeline import config

logger = logging.getLogger(__name__)


class DashboardRealtimeHub:
    """Holds WebSocket connections and schedules debounced broadcast from listener threads."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._debounce_timer: threading.Timer | None = None
        self._debounce_lock = threading.Lock()
        self._watch_handles: list[Any] = []

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket, max_connections: int) -> bool:
        await websocket.accept()
        async with self._lock:
            if len(self._connections) >= max_connections:
                await websocket.close(code=1008, reason="Too many dashboard socket connections")
                return False
            self._connections.add(websocket)
        return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def _broadcast_payload(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, separators=(",", ":"))
        async with self._lock:
            targets = list(self._connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(raw)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)

    def schedule_refresh_ping(self, source: str) -> None:
        """Called from Firestore snapshot thread; debounces N writes into one WS message."""

        def fire() -> None:
            try:
                from pipeline.dashboard_api import invalidate_dashboard_firestore_cache

                invalidate_dashboard_firestore_cache()
            except Exception as exc:
                logger.debug("Cache invalidate skipped: %s", exc)
            loop = self._loop
            if loop is None or not loop.is_running():
                return
            payload = {"v": 1, "kind": "refresh", "source": source}
            asyncio.run_coroutine_threadsafe(self._broadcast_payload(payload), loop)

        delay = config.ws_broadcast_debounce_ms() / 1000.0
        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None

            timer = threading.Timer(delay, fire)
            timer.daemon = True
            self._debounce_timer = timer
            timer.start()

    def add_watch(self, handle: Any) -> None:
        self._watch_handles.append(handle)

    def stop_watchers(self) -> None:
        for h in self._watch_handles:
            try:
                if hasattr(h, "unsubscribe"):
                    h.unsubscribe()
            except Exception as exc:
                logger.debug("Watch unsubscribe: %s", exc)
        self._watch_handles.clear()
        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None

    async def shutdown_sockets(self) -> None:
        self.stop_watchers()
        async with self._lock:
            targets = list(self._connections)
            self._connections.clear()
        for ws in targets:
            try:
                await ws.close()
            except Exception:
                pass


dashboard_realtime_hub = DashboardRealtimeHub()


def start_firestore_watchers(db: Any) -> None:
    """Attach bounded snapshot listeners; requires Firestore initialized."""
    if not config.enable_firestore_realtime():
        logger.info("ENABLE_FIRESTORE_REALTIME=false; skipping snapshot listeners")
        return

    try:
        from google.cloud.firestore import Query
    except ImportError:
        logger.warning("google.cloud.firestore Query unavailable; skipping listeners")
        return

    hub = dashboard_realtime_hub
    alert_limit = config.firestore_listener_alert_limit()
    tx_limit = config.firestore_listener_transaction_limit()

    def on_alerts_snapshot(
        doc_snapshot: Any,
        changes: Any,
        read_time: Any,
    ) -> None:
        if not changes:
            return
        hub.schedule_refresh_ping("alerts")

    try:
        q_alerts = (
            db.collection("alerts")
            .order_by("updated_at", direction=Query.DESCENDING)
            .limit(alert_limit)
        )
        hub.add_watch(q_alerts.on_snapshot(on_alerts_snapshot))
        logger.info("Firestore listener: alerts (order_by updated_at, limit=%s)", alert_limit)
    except Exception as exc:
        logger.warning("Alerts listener order_by failed (%s); using limit-only query", exc)
        try:
            q_fallback = db.collection("alerts").limit(alert_limit)
            hub.add_watch(q_fallback.on_snapshot(on_alerts_snapshot))
        except Exception as exc2:
            logger.error("Alerts snapshot listener could not start: %s", exc2)

    def on_tx_snapshot(
        doc_snapshot: Any,
        changes: Any,
        read_time: Any,
    ) -> None:
        if not changes:
            return
        hub.schedule_refresh_ping("transactions")

    try:
        q_tx = (
            db.collection("transactions")
            .order_by("ingested_at", direction=Query.DESCENDING)
            .limit(tx_limit)
        )
        hub.add_watch(q_tx.on_snapshot(on_tx_snapshot))
        logger.info("Firestore listener: transactions (order_by ingested_at, limit=%s)", tx_limit)
    except Exception as exc:
        logger.warning("Transactions listener order_by failed (%s); using limit-only query", exc)
        try:
            q_tf = db.collection("transactions").limit(tx_limit)
            hub.add_watch(q_tf.on_snapshot(on_tx_snapshot))
        except Exception as exc2:
            logger.warning("Transactions snapshot listener could not start: %s", exc2)


def stop_firestore_watchers() -> None:
    dashboard_realtime_hub.stop_watchers()

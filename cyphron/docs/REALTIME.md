# Dashboard realtime (WebSockets + Firestore)

## What runs where

- **`python -m pipeline.main serve`** exposes `GET ws://<host>:<port>/ws/dashboard` and starts **bounded Firestore snapshot listeners** (when `ENABLE_GCP_STARTUP` succeeds and `ENABLE_FIRESTORE_REALTIME` is true).
- **Ingestion** keeps writing to Firestore; listeners debounce many writes into **one** WebSocket message `{ "kind": "refresh", "source": "alerts" | "transactions" }`.
- The Next.js app opens the socket from [`DashboardRealtimeProvider`](../dashboard/src/lib/dashboardRealtimeContext.tsx), **invalidates SWR keys** on `refresh`, and **lengthens** `refreshInterval` while the socket is connected and pushes are expected (saves Firestore reads on repeated REST polling).

## Environment variables (pipeline / `cyphron/.env`)

| Variable | Purpose |
|----------|---------|
| `ENABLE_FIRESTORE_REALTIME` | `false` disables listeners; WebSocket still accepts and sends `hello` with `realtime: false`. |
| `FIRESTORE_LISTENER_ALERT_LIMIT` | Max docs in the `alerts` watch query (default 180). |
| `FIRESTORE_LISTENER_TRANSACTION_LIMIT` | Max docs in the `transactions` watch query (default 120). |
| `WS_BROADCAST_DEBOUNCE_MS` | Coalesce snapshot bursts (default 400). |
| `WS_MAX_CONNECTIONS` | Cap concurrent dashboard sockets (default 80). |
| `DASHBOARD_FIRESTORE_CACHE_SECONDS` | REST TTL cache for analytics/list (default 20; `0` disables). |
| `FIRESTORE_ANALYTICS_DOC_CAP` | Max docs per analytics collection scan (default 400). |
| `FIRESTORE_LIST_ALERTS_FETCH_CAP` | Max docs loaded for alert list before filter (default 280). |

## Firestore indexes

Listeners use `order_by` when possible:

- `alerts`: `updated_at` descending (composite index may be required in console).
- `transactions`: `ingested_at` descending (same).

If index creation is pending, the server **falls back** to `limit`-only queries (still bounded).

## WSS (production)

Terminate TLS at your reverse proxy (e.g. Nginx, Cloud Run) and use `wss://` from the browser. Set `NEXT_PUBLIC_WS_URL` if the public WS URL differs from `NEXT_PUBLIC_BACKEND_URL` (scheme/host).

## Auth (not implemented)

For public dashboards, the current socket is **open**. Before exposing broadly, add a token (query or first frame) and validate server-side.

## Multi-instance API (horizontal scale)

Each Uvicorn worker/process would run **its own** Firestore listeners and only see **its** WebSocket clients. Use **Redis pub/sub** (or similar) to publish `refresh` events from one place and have every instance `broadcast` to local sockets.

## Billing

Listeners consume Firestore reads on changes; REST remains capped and TTL-cached. Tune limits and debounce to stay within quota.

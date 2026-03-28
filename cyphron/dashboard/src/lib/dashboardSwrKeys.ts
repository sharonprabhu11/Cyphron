/**
 * SWR cache keys used by dashboard widgets; WebSocket handler mutates these on `refresh`.
 */
export const DASHBOARD_SWR_KEYS = [
  "dash-summary",
  "dash-fraud",
  "dash-channels",
  "dash-risk-vol",
  "ticker-alerts",
  "alerts-page",
  "tx-timeseries",
] as const;

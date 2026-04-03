import type {
  AlertRecord,
  DecisionRiskTier,
  AlertStrReportPayload,
  AlertTickerItem,
  FraudSignalSlice,
  RiskVolumePoint,
  SummaryKpi,
  TimeSeriesPoint,
  TransactionCategoryRow,
} from "@/lib/dashboard/types";

export function getBackendBaseUrl(): string {
  const raw = typeof window !== "undefined" ? process.env.NEXT_PUBLIC_BACKEND_URL : process.env.NEXT_PUBLIC_BACKEND_URL;
  const u = raw?.trim() ?? "";
  return u.replace(/\/$/, "");
}

export class BackendNotConfiguredError extends Error {
  constructor() {
    super("NEXT_PUBLIC_BACKEND_URL is not set");
    this.name = "BackendNotConfiguredError";
  }
}

type BackendFetchInit = RequestInit & { timeoutMs?: number };

async function backendFetch<T>(path: string, init?: BackendFetchInit): Promise<T> {
  const base = getBackendBaseUrl();
  if (!base) throw new BackendNotConfiguredError();
  const { timeoutMs = 45_000, ...fetchInit } = init ?? {};
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...fetchInit,
      signal: ctrl.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(fetchInit.headers as Record<string, string>),
      },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<T>;
  } catch (e: unknown) {
    const name =
      e instanceof Error
        ? e.name
        : e instanceof DOMException
          ? e.name
          : typeof e === "object" && e !== null && "name" in e
            ? String((e as { name: unknown }).name)
            : "";
    if (name === "AbortError") {
      throw new Error(
        `Request timed out after ${timeoutMs / 1000}s. Check the pipeline is running at ${base} (report requests wait on Firestore / STR generation).`
      );
    }
    throw e;
  } finally {
    clearTimeout(tid);
  }
}

export async function fetchAlerts(params?: { status?: string; riskLevel?: string; limit?: number; offset?: number }) {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.riskLevel) q.set("risk_level", params.riskLevel);
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  return backendFetch<AlertRecord[]>(`/api/v1/alerts${qs ? `?${qs}` : ""}`);
}

export async function fetchAlert(alertId: string) {
  const enc = encodeURIComponent(alertId);
  return backendFetch<AlertRecord>(`/api/v1/alerts/${enc}`);
}

export async function patchAlertStatus(alertId: string, status: AlertRecord["status"]) {
  const enc = encodeURIComponent(alertId);
  return backendFetch<AlertRecord>(`/api/v1/alerts/${enc}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function fetchReport(alertId: string) {
  const enc = encodeURIComponent(alertId);
  return backendFetch<AlertStrReportPayload>(`/api/v1/alerts/${enc}/report`, { timeoutMs: 90_000 });
}

export async function fetchAnalyticsSummary() {
  return backendFetch<SummaryKpi[]>("/api/v1/analytics/summary");
}

export async function fetchFraudSignals() {
  return backendFetch<FraudSignalSlice[]>("/api/v1/analytics/fraud-signals");
}

export async function fetchChannelExposure() {
  return backendFetch<TransactionCategoryRow[]>("/api/v1/analytics/channel-exposure");
}

export async function fetchRiskVolume() {
  return backendFetch<RiskVolumePoint[]>("/api/v1/analytics/risk-volume");
}

export async function fetchTransactionsTimeseries() {
  return backendFetch<TimeSeriesPoint[]>("/api/v1/analytics/transactions-timeseries");
}

export type SubgraphResponse = {
  nodes: { id: string; label: string }[];
  links: { source: string; target: string; id?: string; amount?: number; channel?: string }[];
};

export async function fetchSubgraph(accountId: string, hops = 2, limit = 200) {
  const q = new URLSearchParams({ account_id: accountId, hops: String(hops), limit: String(limit) });
  return backendFetch<SubgraphResponse>(`/api/v1/graph/subgraph?${q.toString()}`);
}

export async function postSimulatorPublish(body?: {
  fraudType?: "normal" | "fanout" | "structuring";
  overrides?: Record<string, unknown>;
}) {
  return backendFetch<{ transactionId: string; published: boolean }>("/api/v1/simulator/publish", {
    method: "POST",
    body: JSON.stringify({
      fraud_type: body?.fraudType ?? null,
      overrides: body?.overrides ?? {},
    }),
  });
}

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

function tickerPipelineTier(a: AlertRecord): DecisionRiskTier {
  if (a.pipelineRiskTier) return a.pipelineRiskTier;
  if (a.riskLevel === "high") return "HIGH";
  if (a.riskLevel === "low") return "LOW";
  return "MEDIUM";
}

export function alertRecordToTickerItem(a: AlertRecord): AlertTickerItem {
  const tier = tickerPipelineTier(a);
  const strong = tier === "HIGH" || tier === "CRITICAL";
  return {
    id: a.alertId,
    title: `${a.accountId} · ${a.channel.toUpperCase()}`,
    meta: a.ruleFlags || "Pipeline alert",
    value: inr.format(a.amount),
    badge: `${(a.riskScore * 100).toFixed(1)}%`,
    badgeUp: strong,
    inverted: tier === "CRITICAL",
  };
}

/** SWR-compatible fetcher: key is full path including /api/v1/... */
export const swrFetcher = <T>(key: string) => backendFetch<T>(key);

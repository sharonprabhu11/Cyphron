import type {
  AlertRecord,
  AlertStrReportPayload,
  AlertTickerItem,
  DecisionRiskTier,
  FraudSignalSlice,
  RiskVolumePoint,
  SummaryKpi,
  TimeSeriesPoint,
  TransactionCategoryRow,
} from "./types";

export const mockSummaryKpis: SummaryKpi[] = [
  {
    id: "alerts",
    label: "Alerts (24h)",
    value: "47",
    deltaLabel: "+12%",
    deltaPositive: true,
    tint: "blueMuted",
  },
  {
    id: "tx-in",
    label: "Transactions in",
    value: "12.4k",
    deltaLabel: "+3.2%",
    deltaPositive: true,
    tint: "greenMuted",
  },
  {
    id: "high-risk",
    label: "High risk",
    value: "186",
    deltaLabel: "-4%",
    deltaPositive: false,
    tint: "blueMuted",
  },
  {
    id: "cases",
    label: "Open cases",
    value: "23",
    deltaLabel: "+2",
    deltaPositive: false,
    tint: "greenMuted",
  },
];

export const mockFraudSignals: FraudSignalSlice[] = [
  { name: "Structuring", value: 312, color: "#2563eb" },
  { name: "Fan-out / velocity", value: 428, color: "#16a34a" },
  { name: "Geo / channel", value: 156, color: "#38bdf8" },
  { name: "Mule / identity", value: 89, color: "#22c55e" },
  { name: "Other", value: 64, color: "#94a3b8" },
];

export const mockCategoryRows: TransactionCategoryRow[] = [
  {
    id: "upi",
    channel: "UPI",
    volume: 5820,
    volumeLabel: "5,820",
    sharePct: 38,
    flaggedCount: 94,
    exposureFlaggedLabel: "2.1M INR",
    highlight: "high",
  },
  {
    id: "atm",
    channel: "ATM",
    volume: 3210,
    volumeLabel: "3,210",
    sharePct: 21,
    flaggedCount: 41,
    exposureFlaggedLabel: "890k INR",
  },
  {
    id: "web",
    channel: "WEB",
    volume: 4102,
    volumeLabel: "4,102",
    sharePct: 27,
    flaggedCount: 58,
    exposureFlaggedLabel: "1.4M INR",
    highlight: "medium",
  },
  {
    id: "mobile",
    channel: "MOBILE",
    volume: 2104,
    volumeLabel: "2,104",
    sharePct: 14,
    flaggedCount: 22,
    exposureFlaggedLabel: "512k INR",
  },
];

let tickerSeq = 0;

export function createTickerAlert(): AlertTickerItem {
  tickerSeq += 1;
  const risks = ["high", "medium", "low"] as const;
  const risk = risks[tickerSeq % 3];
  const up = risk !== "high";
  return {
    id: `AL-${Date.now()}-${tickerSeq}`,
    title: `Alert ${risk.toUpperCase()}`,
    meta: `ACC_***${(tickerSeq % 900) + 100} · ${risk === "high" ? "velocity" : risk === "medium" ? "structuring" : "geo"}`,
    value:
      risk === "high"
        ? `${(48000 + (tickerSeq % 12) * 1200).toLocaleString()} INR`
        : `${(12000 + (tickerSeq % 20) * 500).toLocaleString()} INR`,
    badge: risk === "high" ? "+Risk" : risk === "medium" ? "Review" : "-2%",
    badgeUp: up,
    inverted: tickerSeq % 7 === 0,
  };
}

export function seedTickerItems(count: number): AlertTickerItem[] {
  return Array.from({ length: count }, () => createTickerAlert());
}

const bucketMins = 24;

export function initialTimeSeries(): TimeSeriesPoint[] {
  const now = Date.now();
  return Array.from({ length: bucketMins }, (_, i) => {
    const t = new Date(now - (bucketMins - 1 - i) * 60_000);
    const label = `${t.getHours().toString().padStart(2, "0")}:${t.getMinutes().toString().padStart(2, "0")}`;
    const base = 40 + Math.sin(i / 3) * 12;
    return {
      t: label,
      total: Math.round(base + Math.random() * 15),
      highRisk: Math.round(base * 0.12 + Math.random() * 6),
      cleared: Math.round(base * 0.78 + Math.random() * 10),
    };
  });
}

export function shiftTimeSeries(prev: TimeSeriesPoint[]): TimeSeriesPoint[] {
  const last = prev[prev.length - 1];
  const nextTotal = Math.max(
    5,
    Math.round(last.total + (Math.random() - 0.45) * 8)
  );
  const nextHigh = Math.max(
    0,
    Math.round(last.highRisk + (Math.random() - 0.5) * 4)
  );
  const nextCleared = Math.max(
    0,
    Math.round(Math.min(nextTotal, last.cleared + (Math.random() - 0.4) * 6))
  );
  const t = new Date();
  const label = `${t.getHours().toString().padStart(2, "0")}:${t.getMinutes().toString().padStart(2, "0")}`;
  const next = [...prev.slice(1), { t: label, total: nextTotal, highRisk: nextHigh, cleared: nextCleared }];
  return next;
}

/** Demo alerts for `/dashboard/alerts` until Firestore API is wired. */
export const mockAlertRecords: AlertRecord[] = [
  {
    alertId: "AL-2026-0041",
    accountId: "acct_8f2k9q",
    amount: 48200,
    timestamp: "2026-03-28T09:14:00.000Z",
    channel: "UPI",
    riskScore: 0.91,
    riskLevel: "high",
    ruleFlags: "velocity, fan-out",
    behaviorSignature: "sig_upi_burst_01",
    status: "open",
    deviceFingerprint: "fp_mob_a3b2",
    ipAddress: "203.0.113.42",
    clusterId: "cluster_mule_07",
    createdAt: "2026-03-28T09:14:22.000Z",
    updatedAt: "2026-03-28T09:14:22.000Z",
  },
  {
    alertId: "AL-2026-0040",
    accountId: "acct_1p9x7m",
    amount: 1250.5,
    timestamp: "2026-03-28T08:52:00.000Z",
    channel: "online",
    riskScore: 0.72,
    riskLevel: "medium",
    ruleFlags: "velocity, geo",
    behaviorSignature: "sig_seed_abc",
    status: "open",
    deviceFingerprint: "fp_seed_xyz",
    ipAddress: "203.0.113.10",
    clusterId: "cluster_seed_01",
    createdAt: "2026-03-28T08:52:18.000Z",
    updatedAt: "2026-03-28T08:55:00.000Z",
  },
  {
    alertId: "AL-2026-0038",
    accountId: "acct_3n4r8w",
    amount: 8900,
    timestamp: "2026-03-28T07:20:00.000Z",
    channel: "card",
    riskScore: 0.88,
    riskLevel: "high",
    ruleFlags: "structuring, channel hop",
    behaviorSignature: "sig_card_split_12",
    status: "investigating",
    deviceFingerprint: "fp_web_c9d1",
    ipAddress: "198.51.100.8",
    clusterId: "cluster_seed_01",
    createdAt: "2026-03-28T07:21:05.000Z",
    updatedAt: "2026-03-28T10:02:00.000Z",
  },
  {
    alertId: "AL-2026-0035",
    accountId: "acct_7k2j1h",
    amount: 420,
    timestamp: "2026-03-27T22:10:00.000Z",
    channel: "ATM",
    riskScore: 0.41,
    riskLevel: "low",
    ruleFlags: "geo",
    behaviorSignature: "sig_atm_night_04",
    status: "acknowledged",
    deviceFingerprint: "fp_atm_001",
    ipAddress: "192.0.2.55",
    clusterId: "cluster_iso_03",
    createdAt: "2026-03-27T22:11:00.000Z",
    updatedAt: "2026-03-28T06:00:00.000Z",
  },
  {
    alertId: "AL-2026-0032",
    accountId: "acct_8f2k9q",
    amount: 12000,
    timestamp: "2026-03-27T18:45:00.000Z",
    channel: "UPI",
    riskScore: 0.85,
    riskLevel: "high",
    ruleFlags: "velocity",
    behaviorSignature: "sig_upi_burst_01",
    status: "open",
    deviceFingerprint: "fp_mob_a3b2",
    ipAddress: "203.0.113.42",
    clusterId: "cluster_mule_07",
    createdAt: "2026-03-27T18:46:12.000Z",
    updatedAt: "2026-03-27T18:46:12.000Z",
  },
  {
    alertId: "AL-2026-0029",
    accountId: "acct_0z9y8x",
    amount: 210000,
    timestamp: "2026-03-27T14:00:00.000Z",
    channel: "WEB",
    riskScore: 0.79,
    riskLevel: "medium",
    ruleFlags: "amount threshold, new beneficiary",
    behaviorSignature: "sig_wire_new_09",
    status: "open",
    deviceFingerprint: "fp_desk_77",
    ipAddress: "203.0.113.201",
    clusterId: "cluster_biz_11",
    createdAt: "2026-03-27T14:02:00.000Z",
    updatedAt: "2026-03-27T14:02:00.000Z",
  },
  {
    alertId: "AL-2026-0024",
    accountId: "acct_5t6u7v",
    amount: 3300,
    timestamp: "2026-03-27T11:30:00.000Z",
    channel: "MOBILE",
    riskScore: 0.55,
    riskLevel: "medium",
    ruleFlags: "device mismatch",
    behaviorSignature: "sig_mob_dev_02",
    status: "investigating",
    deviceFingerprint: "fp_mob_new",
    ipAddress: "198.51.100.22",
    clusterId: "cluster_iso_03",
    createdAt: "2026-03-27T11:31:00.000Z",
    updatedAt: "2026-03-27T15:20:00.000Z",
  },
  {
    alertId: "AL-2026-0020",
    accountId: "acct_2b4c6d",
    amount: 99.99,
    timestamp: "2026-03-26T16:00:00.000Z",
    channel: "card",
    riskScore: 0.28,
    riskLevel: "low",
    ruleFlags: "round amount",
    behaviorSignature: "sig_card_low_88",
    status: "closed",
    deviceFingerprint: "fp_card_aa",
    ipAddress: "192.0.2.1",
    clusterId: "cluster_retail_02",
    createdAt: "2026-03-26T16:01:00.000Z",
    updatedAt: "2026-03-27T09:00:00.000Z",
  },
  {
    alertId: "AL-2026-0018",
    accountId: "acct_1p9x7m",
    amount: 499.99,
    timestamp: "2026-03-26T10:00:00.000Z",
    channel: "card",
    riskScore: 0.61,
    riskLevel: "medium",
    ruleFlags: "recurring pattern",
    behaviorSignature: "sig_tx_seed",
    status: "closed",
    deviceFingerprint: "fp_seed_xyz",
    ipAddress: "203.0.113.10",
    clusterId: "cluster_seed_01",
    createdAt: "2026-03-26T10:05:00.000Z",
    updatedAt: "2026-03-26T18:00:00.000Z",
  },
  {
    alertId: "AL-2026-0015",
    accountId: "acct_9q8w7e",
    amount: 67000,
    timestamp: "2026-03-25T08:00:00.000Z",
    channel: "UPI",
    riskScore: 0.93,
    riskLevel: "high",
    ruleFlags: "velocity, mule pattern",
    behaviorSignature: "sig_upi_mule_44",
    status: "acknowledged",
    deviceFingerprint: "fp_mob_z1",
    ipAddress: "203.0.113.99",
    clusterId: "cluster_mule_07",
    createdAt: "2026-03-25T08:12:00.000Z",
    updatedAt: "2026-03-26T12:00:00.000Z",
  },
  {
    alertId: "AL-2026-0012",
    accountId: "acct_4r5t6y",
    amount: 15000,
    timestamp: "2026-03-24T19:40:00.000Z",
    channel: "online",
    riskScore: 0.48,
    riskLevel: "low",
    ruleFlags: "off-hours",
    behaviorSignature: "sig_online_night_03",
    status: "closed",
    deviceFingerprint: "fp_tab_12",
    ipAddress: "198.51.100.3",
    clusterId: "cluster_biz_11",
    createdAt: "2026-03-24T19:42:00.000Z",
    updatedAt: "2026-03-25T10:00:00.000Z",
  },
];

function reasonsFromRuleFlags(ruleFlags: string): string[] {
  return ruleFlags
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const lower = s.toLowerCase();
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    });
}

/** Mirrors pipeline `str_generator._fallback_report` shape (Mock mode). */
export function buildMockFallbackStrReportText(
  mode: string,
  entityId: string,
  riskScore: number,
  tier: string,
  reasons: string[],
  transactionSummary: Record<string, string>
): string {
  const summaryLines = Object.entries(transactionSummary).map(([key, value]) => `- ${key}: ${value}`);
  const reasonsText =
    reasons.length > 0 ? reasons.map((r) => `- ${r}`).join("\n") : "- No rule reasons available";
  const summaryText = summaryLines.length > 0 ? summaryLines.join("\n") : "- Not available";
  return (
    `STR Report (${mode})\n\n` +
    `Entity: ${entityId}\n` +
    `Risk Score: ${riskScore.toFixed(4)}\n` +
    `Tier: ${tier}\n\n` +
    `Reasons:\n${reasonsText}\n\n` +
    `Transaction Summary:\n${summaryText}\n\n` +
    "Automated system detected suspicious activity and recommends analyst review."
  );
}

export function transactionSummaryFromAlert(a: AlertRecord): Record<string, string> {
  const ch = a.channel.toUpperCase();
  const channelNorm = ["UPI", "ATM", "WEB", "MOBILE"].includes(ch) ? ch : "WEB";
  return {
    transaction_id: `tx_${a.alertId.replace(/-/g, "_")}`,
    account_id: a.accountId,
    recipient_id: a.clusterId,
    amount: String(a.amount),
    currency: "INR",
    timestamp: a.timestamp,
    channel: channelNorm,
    tx_type: "TRANSFER",
    device_fingerprint: a.deviceFingerprint,
    ip_address: a.ipAddress,
    session_id: `sess_${a.alertId}`,
    geo_hash: "",
    merchant_id: "",
    entity_id: a.accountId,
    cluster_id: a.clusterId,
    behavior_signature: a.behaviorSignature,
    alert_id: a.alertId,
    alert_status: a.status,
  };
}

function alertToDecisionTier(a: AlertRecord): DecisionRiskTier {
  if (a.riskLevel === "low") return "LOW";
  if (a.riskLevel === "medium") return "MEDIUM";
  return "HIGH";
}

/** Demo: STR + PDF only for high-severity alerts above this score (pipeline: CRITICAL only). */
const MOCK_STR_SCORE_THRESHOLD = 0.85;

function isMockStrEligible(a: AlertRecord): boolean {
  return a.riskLevel === "high" && a.riskScore >= MOCK_STR_SCORE_THRESHOLD;
}

export function getMockAlertById(alertId: string): AlertRecord | undefined {
  return mockAlertRecords.find((r) => r.alertId === alertId);
}

export function getMockStrReportPayloadForAlert(alertId: string): AlertStrReportPayload | null {
  const alert = getMockAlertById(alertId);
  if (!alert) return null;

  const reasons = reasonsFromRuleFlags(alert.ruleFlags);
  const transactionSummary = transactionSummaryFromAlert(alert);
  const critical = isMockStrEligible(alert);
  const riskTier: DecisionRiskTier = critical ? "CRITICAL" : alertToDecisionTier(alert);
  const strReport = critical
    ? buildMockFallbackStrReportText(
        "Mock",
        alert.accountId,
        alert.riskScore,
        riskTier,
        reasons,
        transactionSummary
      )
    : null;
  const generatedAt = critical ? alert.updatedAt : null;

  return {
    alertId: alert.alertId,
    entityId: alert.accountId,
    riskScore: alert.riskScore,
    riskTier,
    reasons,
    transactionSummary,
    strReport,
    generatedAt,
    pdfDownloadPath: critical ? `/api/alerts/${encodeURIComponent(alertId)}/report/pdf` : null,
  };
}

export const mockRiskVolume: RiskVolumePoint[] = [
  { label: "Mon", volume: 4200, riskPct: 8.2 },
  { label: "Tue", volume: 5100, riskPct: 9.1 },
  { label: "Wed", volume: 4800, riskPct: 7.4 },
  { label: "Thu", volume: 6200, riskPct: 11.2 },
  { label: "Fri", volume: 5900, riskPct: 10.0 },
  { label: "Sat", volume: 3100, riskPct: 6.8 },
  { label: "Sun", volume: 2800, riskPct: 5.9 },
];

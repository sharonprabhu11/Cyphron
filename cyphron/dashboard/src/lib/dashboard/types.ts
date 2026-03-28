export type SummaryKpi = {
  id: string;
  label: string;
  value: string;
  deltaLabel: string;
  deltaPositive: boolean;
  tint: "blue" | "green" | "blueMuted" | "greenMuted";
};

export type FraudSignalSlice = {
  name: string;
  value: number;
  color: string;
};

export type TransactionCategoryRow = {
  id: string;
  channel: string;
  volume: number;
  volumeLabel: string;
  sharePct: number;
  flaggedCount: number;
  exposureFlaggedLabel: string;
  highlight?: "high" | "medium";
};

export type AlertTickerItem = {
  id: string;
  title: string;
  meta: string;
  value: string;
  badge: string;
  badgeUp: boolean;
  inverted?: boolean;
};

export type TimeSeriesPoint = {
  t: string;
  total: number;
  highRisk: number;
  cleared: number;
};

export type RiskVolumePoint = {
  label: string;
  volume: number;
  riskPct: number;
};

/** Operational alert row — aligns with Firestore `alerts` seed shape (camelCase in UI). */
export type AlertRiskLevel = "high" | "medium" | "low";

export type AlertStatus = "open" | "acknowledged" | "investigating" | "closed";

export type AlertRecord = {
  alertId: string;
  accountId: string;
  amount: number;
  timestamp: string;
  channel: string;
  riskScore: number;
  riskLevel: AlertRiskLevel;
  ruleFlags: string;
  behaviorSignature: string;
  status: AlertStatus;
  deviceFingerprint: string;
  ipAddress: string;
  clusterId: string;
  createdAt: string;
  updatedAt: string;
};

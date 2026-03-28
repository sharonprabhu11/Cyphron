"use client";

import useSWR from "swr";

import { AlertTicker } from "@/components/dashboard/AlertTicker";
import { FraudDonutCard } from "@/components/dashboard/FraudDonutCard";
import { LiveTransactionsChart } from "@/components/dashboard/LiveTransactionsChart";
import { RiskVolumeComboCard } from "@/components/dashboard/RiskVolumeComboCard";
import { SummaryStrip } from "@/components/dashboard/SummaryStrip";
import { TransactionCategoryTable } from "@/components/dashboard/TransactionCategoryTable";
import {
  BackendNotConfiguredError,
  fetchAnalyticsSummary,
  fetchChannelExposure,
  fetchFraudSignals,
  fetchRiskVolume,
  getBackendBaseUrl,
} from "@/lib/api";
import { useDashboardRealtime } from "@/lib/dashboardRealtimeContext";

export function DashboardHomeClient() {
  const backendOk = Boolean(getBackendBaseUrl());
  const { reducePolling } = useDashboardRealtime();
  const pollFast = 12_000;
  const pollSlow = 90_000;
  const homeIv = reducePolling ? pollSlow : pollFast;
  const otherIv = reducePolling ? pollSlow : 15_000;

  const { data: summary = [], error: summaryError } = useSWR(
    backendOk ? "dash-summary" : null,
    fetchAnalyticsSummary,
    { refreshInterval: homeIv }
  );
  const { data: fraudSignals = [] } = useSWR(backendOk ? "dash-fraud" : null, fetchFraudSignals, {
    refreshInterval: otherIv,
  });
  const { data: categoryRows = [] } = useSWR(backendOk ? "dash-channels" : null, fetchChannelExposure, {
    refreshInterval: otherIv,
  });
  const { data: riskVolume = [] } = useSWR(backendOk ? "dash-risk-vol" : null, fetchRiskVolume, {
    refreshInterval: otherIv,
  });

  const displaySummary =
    summary.length > 0
      ? summary
      : backendOk && !summaryError
        ? [
            {
              id: "placeholder",
              label: "Pipeline",
              value: "—",
              deltaLabel: "awaiting data",
              deltaPositive: true,
              tint: "blueMuted" as const,
            },
          ]
        : [];

  const riskData =
    riskVolume.length > 0
      ? riskVolume
      : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label) => ({
          label,
          volume: 0,
          riskPct: 0,
        }));

  const configError =
    !backendOk || summaryError instanceof BackendNotConfiguredError ? (
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-100">
        Set <code className="rounded bg-white/60 px-1 dark:bg-black/30">NEXT_PUBLIC_BACKEND_URL</code> to your
        pipeline URL (for example <code className="rounded bg-white/60 px-1 dark:bg-black/30">http://localhost:8810</code>)
        and restart Next.js.
      </div>
    ) : summaryError ? (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-500/40 dark:bg-red-950/40 dark:text-red-100">
        Could not load dashboard data: {summaryError.message}
      </div>
    ) : null;

  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
      {configError}
      <div className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-12">
        <div className="flex min-h-0 min-w-0 lg:col-span-3">
          <SummaryStrip items={displaySummary} />
        </div>
        <div className="flex min-h-0 min-w-0 lg:col-span-4">
          <FraudDonutCard data={fraudSignals.length ? fraudSignals : [{ name: "—", value: 1, color: "#94a3b8" }]} />
        </div>
        <div className="flex min-h-0 min-w-0 lg:col-span-5">
          <TransactionCategoryTable rows={categoryRows} />
        </div>
      </div>

      <AlertTicker />

      <div className="grid grid-cols-1 items-stretch gap-6 xl:grid-cols-2 xl:auto-rows-[1fr]">
        <div className="flex min-h-[min(24rem,50vh)] min-w-0 xl:min-h-[20rem]">
          <LiveTransactionsChart />
        </div>
        <div className="flex min-h-[min(24rem,50vh)] min-w-0 xl:min-h-[20rem]">
          <RiskVolumeComboCard data={riskData} />
        </div>
      </div>
    </div>
  );
}

"use client";

import { notFound, useParams } from "next/navigation";
import useSWR from "swr";

import { AlertReportClient } from "@/components/dashboard/AlertReportClient";
import { fetchAlert, fetchReport, getBackendBaseUrl } from "@/lib/api";

/**
 * Client-only route: avoids Next RSC server chunk incorrectly requiring
 * `tailwind-merge` (MODULE_NOT_FOUND on ./vendor-chunks/tailwind-merge.js).
 */
export default function AlertReportPage() {
  const params = useParams();
  const raw = params?.alertId;
  const alertId =
    typeof raw === "string"
      ? decodeURIComponent(raw)
      : Array.isArray(raw)
        ? decodeURIComponent(raw[0] ?? "")
        : "";

  const backendOk = Boolean(getBackendBaseUrl());
  const { data: alert, error: alertErr } = useSWR(
    backendOk && alertId ? ["alert", alertId] : null,
    () => fetchAlert(alertId)
  );
  const { data: report, error: reportErr } = useSWR(
    backendOk && alertId ? ["report", alertId] : null,
    () => fetchReport(alertId)
  );

  if (!alertId) {
    notFound();
  }

  if (!backendOk) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-950 dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-100">
        Configure <code className="rounded bg-white/70 px-1 dark:bg-black/30">NEXT_PUBLIC_BACKEND_URL</code> to load
        this report.
      </div>
    );
  }

  if (alertErr || reportErr) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-900 dark:border-red-500/40 dark:bg-red-950/40 dark:text-red-100">
        {alertErr?.message ?? reportErr?.message ?? "Failed to load report."}
      </div>
    );
  }

  if (!alert || !report) {
    return <p className="text-sm text-stone-500 dark:text-zinc-400">Loading report…</p>;
  }

  return <AlertReportClient alert={alert} report={report} />;
}

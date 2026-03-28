"use client";

import useSWR from "swr";
import { memo, useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { fetchTransactionsTimeseries, getBackendBaseUrl } from "@/lib/api";
import type { TimeSeriesPoint } from "@/lib/dashboard/types";

const ChartInner = memo(function ChartInner({ data }: { data: TimeSeriesPoint[] }) {
  return (
    <ResponsiveContainer
      width="100%"
      height="100%"
      minHeight={280}
      initialDimension={{ width: 640, height: 280 }}
    >
      <LineChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
        <XAxis dataKey="t" tick={{ fontSize: 11, fill: "#5c6f66" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: "#5c6f66" }} axisLine={false} tickLine={false} width={36} />
        <Tooltip
          contentStyle={{
            borderRadius: 12,
            border: "1px solid rgba(0,0,0,0.06)",
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" />
        <Line type="monotone" dataKey="total" name="Tx / min" stroke="#2563eb" strokeWidth={2} dot={false} />
        <Line
          type="monotone"
          dataKey="highRisk"
          name="High risk"
          stroke="#dc2626"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="cleared"
          name="Cleared"
          stroke="#16a34a"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
});

export function LiveTransactionsChart() {
  const [mounted, setMounted] = useState(false);
  const backendOk = Boolean(getBackendBaseUrl());
  const { data = [] } = useSWR(
    backendOk && mounted ? "tx-timeseries" : null,
    fetchTransactionsTimeseries,
    { refreshInterval: 8000 }
  );
  const chartData: TimeSeriesPoint[] =
    data.length > 0
      ? data
      : Array.from({ length: 24 }, (_, i) => ({
          t: `${String(i).padStart(2, "0")}:00`,
          total: 0,
          highRisk: 0,
          cleared: 0,
        }));

  useEffect(() => setMounted(true), []);

  return (
    <DashboardCard className="w-full flex-1" title="Transaction throughput (live)">
      <div className="h-full min-h-[280px] w-full flex-1">
        {mounted ? (
          <ChartInner data={chartData} />
        ) : (
          <div className="h-full rounded-xl bg-surface-muted/40 dark:bg-zinc-800/50" aria-hidden />
        )}
      </div>
    </DashboardCard>
  );
}

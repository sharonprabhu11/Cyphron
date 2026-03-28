"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { DashboardCard } from "@/components/dashboard/DashboardCard";
import type { RiskVolumePoint } from "@/lib/dashboard/types";

export function RiskVolumeComboCard({ data }: { data: RiskVolumePoint[] }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <DashboardCard className="w-full flex-1" title="Volume vs risk intensity">
      <p className="mb-3 shrink-0 text-xs text-ink-muted">
        Bars: transaction volume. Line: % of transactions flagged (rolling).
      </p>
      <div className="h-full min-h-[280px] w-full flex-1">
        {!mounted ? (
          <div className="h-full rounded-xl bg-surface-muted/40 dark:bg-zinc-800/50" aria-hidden />
        ) : (
        <ResponsiveContainer
          width="100%"
          height="100%"
          minHeight={280}
          initialDimension={{ width: 640, height: 280 }}
        >
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#5c6f66" }} axisLine={false} tickLine={false} />
            <YAxis
              yAxisId="vol"
              tick={{ fontSize: 11, fill: "#5c6f66" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <YAxis
              yAxisId="risk"
              orientation="right"
              tick={{ fontSize: 11, fill: "#5c6f66" }}
              axisLine={false}
              tickLine={false}
              width={36}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(value, name) => {
                const v = typeof value === "number" ? value : Number(value);
                const label = String(name);
                if (label.includes("Flagged") || label === "riskPct")
                  return [`${Number.isFinite(v) ? v : 0}%`, "Flagged %"];
                return [(Number.isFinite(v) ? v : 0).toLocaleString(), "Volume"];
              }}
              contentStyle={{
                borderRadius: 12,
                border: "1px solid rgba(0,0,0,0.06)",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar
              yAxisId="vol"
              dataKey="volume"
              name="Volume"
              fill="#93c5fd"
              radius={[10, 10, 4, 4]}
              barSize={28}
            />
            <Line
              yAxisId="risk"
              type="monotone"
              dataKey="riskPct"
              name="Flagged %"
              stroke="#0f2823"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#0f2823", strokeWidth: 0 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
        )}
      </div>
    </DashboardCard>
  );
}

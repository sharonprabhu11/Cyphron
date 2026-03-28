"use client";

import { useEffect, useState } from "react";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { DashboardCard } from "@/components/dashboard/DashboardCard";
import type { FraudSignalSlice } from "@/lib/dashboard/types";

export function FraudDonutCard({ data }: { data: FraudSignalSlice[] }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <DashboardCard className="w-full flex-1" title="Fraud signals mix">
      <div className="relative flex min-h-0 w-full flex-1 flex-col items-center justify-center">
        <div className="relative h-full min-h-[200px] w-full max-w-[280px] flex-1">
        {!mounted ? (
          <div className="h-full w-full rounded-2xl bg-surface-muted/40 dark:bg-zinc-800/50" aria-hidden />
        ) : (
        <ResponsiveContainer
          width="100%"
          height="100%"
          minHeight={200}
          initialDimension={{ width: 280, height: 220 }}
        >
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="70%"
              startAngle={180}
              endAngle={0}
              innerRadius="58%"
              outerRadius="92%"
              paddingAngle={2}
              dataKey="value"
              nameKey="name"
              stroke="none"
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, _name, item) => {
                const v = typeof value === "number" ? value : 0;
                const slice = item?.payload as FraudSignalSlice | undefined;
                return [
                  `${v} (${total ? ((v / total) * 100).toFixed(1) : 0}%)`,
                  slice?.name ?? "",
                ];
              }}
              contentStyle={{
                borderRadius: 12,
                border: "1px solid rgba(0,0,0,0.06)",
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        )}
        <div className="pointer-events-none absolute inset-x-0 bottom-6 flex flex-col items-center justify-end text-center">
          <p className="text-xs font-medium text-ink-muted">Signals (7d)</p>
          <p className="text-2xl font-bold tabular-nums text-ink">{total.toLocaleString()}</p>
        </div>
        </div>
      </div>
    </DashboardCard>
  );
}

"use client";

import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { SummaryKpi } from "@/lib/dashboard/types";
import { cn } from "@/lib/utils";

const tintClass: Record<SummaryKpi["tint"], string> = {
  blueMuted: "bg-brand-blue-muted/35 dark:bg-sky-950/50",
  greenMuted: "bg-brand-green-muted/50 dark:bg-emerald-950/40",
  blue: "bg-brand-blue-muted/50 dark:bg-sky-950/60",
  green: "bg-brand-green-muted/60 dark:bg-emerald-950/50",
};

export function SummaryStrip({ items }: { items: SummaryKpi[] }) {
  return (
    <DashboardCardShell title="Summary">
      <ul className="flex min-h-0 flex-1 flex-col gap-3">
        {items.map((row) => (
          <li
            key={row.id}
            className={cn(
              "flex min-h-0 flex-1 items-center justify-between rounded-pill border border-border px-4 py-3 dark:border-white/10",
              tintClass[row.tint]
            )}
          >
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 shrink-0 rounded-full bg-primary" />
              <span className="text-sm font-medium text-ink">{row.label}</span>
            </div>
            <div className="flex items-center gap-3">
              <Badge
                variant={row.deltaPositive ? "success" : "destructive"}
                className={cn(
                  "rounded-pill border-0 font-semibold",
                  row.deltaPositive && "bg-brand-green-muted text-brand-green hover:bg-brand-green-muted/90 dark:bg-emerald-900/60 dark:text-emerald-300",
                  !row.deltaPositive && "bg-red-50 text-brand-red hover:bg-red-50 dark:bg-red-950/50 dark:text-red-300"
                )}
              >
                {row.deltaLabel}
              </Badge>
              <span className="text-lg font-bold tabular-nums text-ink">{row.value}</span>
            </div>
          </li>
        ))}
      </ul>
    </DashboardCardShell>
  );
}

function DashboardCardShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Card className="relative flex h-full min-h-0 w-full flex-1 flex-col rounded-xl border-border bg-white p-0 dark:border-white/10 dark:bg-zinc-900">
      <CardHeader className="px-5 pb-2 pt-4">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col px-5 pb-5 pt-0">{children}</CardContent>
    </Card>
  );
}

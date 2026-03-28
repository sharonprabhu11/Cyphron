"use client";

import { Building2, Globe, MoreHorizontal, Smartphone, Zap } from "lucide-react";

import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { TransactionCategoryRow } from "@/lib/dashboard/types";
import { cn } from "@/lib/utils";

function ChannelIcon({ channel }: { channel: string }) {
  const c = channel.toUpperCase();
  const cls = "flex h-8 w-8 shrink-0 items-center justify-center rounded-full";
  if (c === "UPI")
    return (
      <div className={cn(cls, "bg-brand-blue-muted text-primary dark:bg-sky-950 dark:text-sky-400")}>
        <Zap className="h-4 w-4" strokeWidth={1.75} />
      </div>
    );
  if (c === "ATM")
    return (
      <div className={cn(cls, "bg-brand-green-muted text-brand-green dark:bg-emerald-950 dark:text-emerald-400")}>
        <Building2 className="h-4 w-4" strokeWidth={1.75} />
      </div>
    );
  if (c === "WEB")
    return (
      <div className={cn(cls, "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300")}>
        <Globe className="h-4 w-4" strokeWidth={1.75} />
      </div>
    );
  return (
    <div className={cn(cls, "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300")}>
      <Smartphone className="h-4 w-4" strokeWidth={1.75} />
    </div>
  );
}

export function TransactionCategoryTable({ rows }: { rows: TransactionCategoryRow[] }) {
  return (
    <DashboardCard className="w-full flex-1" title="By channel & exposure">
      <div className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead>
            <tr className="border-b border-ink/8 text-ink-muted dark:border-white/10">
              <th className="pb-3 pr-2 font-medium">Channel</th>
              <th className="pb-3 pr-2 font-medium tabular-nums">Volume</th>
              <th className="pb-3 pr-2 font-medium tabular-nums">Share</th>
              <th className="pb-3 pr-2 font-medium tabular-nums">Flagged</th>
              <th className="pb-3 font-medium tabular-nums">Exposure flagged</th>
              <th className="w-8 pb-3" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-ink/[0.06] last:border-0 dark:border-white/10">
                <td className="py-3 pr-2">
                  <div className="flex items-center gap-3">
                    <ChannelIcon channel={r.channel} />
                    <span className="font-semibold text-ink">{r.channel}</span>
                  </div>
                </td>
                <td className="py-3 pr-2 tabular-nums text-ink">{r.volumeLabel}</td>
                <td className="py-3 pr-2 tabular-nums text-ink-muted">{r.sharePct}%</td>
                <td className="py-3 pr-2 tabular-nums text-ink">{r.flaggedCount}</td>
                <td
                  className={cn(
                    "py-3 font-semibold tabular-nums",
                    r.highlight === "high" && "text-brand-red",
                    r.highlight === "medium" && "text-brand-yellow dark:text-amber-400"
                  )}
                >
                  {r.exposureFlaggedLabel}
                </td>
                <td className="py-3 text-ink-muted">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Row menu">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem>View channel</DropdownMenuItem>
                      <DropdownMenuItem>Open case</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardCard>
  );
}

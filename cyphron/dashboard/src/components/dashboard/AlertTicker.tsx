"use client";

import useSWR from "swr";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { alertRecordToTickerItem, fetchAlerts, getBackendBaseUrl } from "@/lib/api";
import { useDashboardRealtime } from "@/lib/dashboardRealtimeContext";
import type { AlertTickerItem } from "@/lib/dashboard/types";
import { cn } from "@/lib/utils";

export function AlertTicker() {
  const backendOk = Boolean(getBackendBaseUrl());
  const { reducePolling } = useDashboardRealtime();
  const { data: alerts = [] } = useSWR(backendOk ? "ticker-alerts" : null, () => fetchAlerts({ limit: 30 }), {
    refreshInterval: reducePolling ? 90_000 : 5000,
  });
  const items: AlertTickerItem[] = alerts.length
    ? alerts.map(alertRecordToTickerItem)
    : backendOk
      ? []
      : [
          {
            id: "cfg",
            title: "Configure backend",
            meta: "Set NEXT_PUBLIC_BACKEND_URL to the FastAPI base URL",
            value: "—",
            badge: "API",
            badgeUp: false,
            inverted: false,
          },
        ];
  const [reduceMotion, setReduceMotion] = useState(false);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const fn = () => setReduceMotion(mq.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  const scrollToEnd = useCallback(() => {
    const el = scrollerRef.current;
    if (!el || reduceMotion) return;
    el.scrollTo({ left: el.scrollWidth, behavior: "smooth" });
  }, [reduceMotion]);

  useEffect(() => {
    scrollToEnd();
  }, [items, scrollToEnd]);

  return (
    <section className="rounded-xl border border-border bg-white p-4 dark:border-white/10 dark:bg-zinc-900">
      <div className="mb-3 flex items-center justify-between px-1">
        <h2 className="text-sm font-semibold text-ink">Live alerts</h2>
        <span className="text-xs text-ink-muted">Auto-updating stream</span>
      </div>
      <div
        ref={scrollerRef}
        className="flex gap-4 overflow-x-auto pb-2 pt-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {items.length === 0 && backendOk ? (
          <p className="px-2 text-sm text-ink-muted">No alerts yet — run ingestion or the simulator.</p>
        ) : null}
        {items.map((item) => (
          <article
            key={item.id}
            className={cn(
              "w-[200px] shrink-0 rounded-xl border border-border p-4 dark:border-white/10",
              item.inverted
                ? "border-ink bg-ink text-white dark:border-zinc-600 dark:bg-zinc-950"
                : "bg-surface-muted text-ink dark:bg-zinc-800/80"
            )}
          >
            <p className="text-xs font-medium text-current/80">{item.title}</p>
            <p className="mt-1 line-clamp-2 text-[11px] text-current/60">{item.meta}</p>
            <p className="mt-3 text-lg font-bold tabular-nums">{item.value}</p>
            <div className="mt-2 flex justify-end">
              <Badge
                variant="outline"
                className={cn(
                  "rounded-pill border-0 px-2 py-0.5 text-[10px] font-semibold",
                  item.inverted
                    ? item.badgeUp
                      ? "bg-brand-green text-white hover:bg-brand-green"
                      : "bg-brand-red text-white hover:bg-brand-red"
                    : item.badgeUp
                      ? "bg-brand-green-muted text-brand-green hover:bg-brand-green-muted dark:bg-emerald-900/50 dark:text-emerald-300"
                      : "bg-amber-100 text-amber-800 hover:bg-amber-100 dark:bg-amber-950/50 dark:text-amber-200"
                )}
              >
                {item.badge}
              </Badge>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

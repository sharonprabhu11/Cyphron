"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import useSWR from "swr";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Bell,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Flag,
  Search,
  ThumbsUp,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchAlerts, getBackendBaseUrl, patchAlertStatus } from "@/lib/api";
import type { AlertRecord, AlertRiskLevel, AlertStatus } from "@/lib/dashboard/types";
import { cn } from "@/lib/utils";

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const PAGE_SIZE = 10;

const accent = {
  pillActive: "bg-orange-500 text-white shadow-sm hover:bg-orange-500 dark:bg-orange-600 dark:hover:bg-orange-600",
  pillIdle: "text-stone-600 hover:text-stone-900 dark:text-zinc-400 dark:hover:text-zinc-100",
  iconBg: "bg-orange-50 text-orange-600 dark:bg-orange-950/50 dark:text-orange-400",
  barHigh: "border-l-orange-500",
  barMed: "border-l-orange-300 dark:border-l-orange-400/80",
  barLow: "border-l-stone-300 dark:border-l-zinc-600",
};

function maskAccountId(accountId: string) {
  const tail = accountId.replace(/^acct_/, "").slice(-4);
  return `••••${tail}`;
}

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function formatDateTimeLabel(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  if (startOfDay(d) === startOfDay(now)) {
    return `Today, ${d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", hour12: true })}`;
  }
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatWhenDetail(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Reference-style criticality labels from fraud risk level. */
function criticalityLabel(level: AlertRiskLevel) {
  if (level === "high") return "Critical";
  if (level === "medium") return "High";
  return "Low";
}

function criticalityBadge(level: AlertRiskLevel) {
  if (level === "high") {
    return (
      <span className="inline-flex rounded-md bg-orange-600 px-2.5 py-0.5 text-xs font-semibold text-white dark:bg-orange-600">
        Critical
      </span>
    );
  }
  if (level === "medium") {
    return (
      <span className="inline-flex rounded-md border border-orange-400 bg-orange-50 px-2.5 py-0.5 text-xs font-semibold text-red-800 dark:border-orange-500/60 dark:bg-orange-950/40 dark:text-orange-200">
        High
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-md bg-stone-100 px-2.5 py-0.5 text-xs font-semibold text-stone-600 dark:bg-zinc-800 dark:text-zinc-300">
      Low
    </span>
  );
}

function statusBadge(status: AlertStatus) {
  const map: Record<AlertStatus, string> = {
    open: "bg-brand-blue-muted/80 text-primary dark:bg-sky-950/60 dark:text-sky-300",
    investigating: "bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200",
    acknowledged: "bg-muted text-muted-foreground",
    closed: "border border-border bg-transparent text-ink-muted dark:border-white/15",
  };
  return (
    <Badge variant="outline" className={cn("rounded-pill border-0 font-semibold capitalize", map[status])}>
      {status}
    </Badge>
  );
}

type SortKey = "timestamp" | "riskScore" | "amount";
type SortDir = "asc" | "desc";
type QueueTab = "all" | "active" | "resolved";

function SortHeader({
  label,
  active,
  dir,
  onClick,
  className,
  alignEnd,
}: {
  label: string;
  active: boolean;
  dir: SortDir;
  onClick: () => void;
  className?: string;
  alignEnd?: boolean;
}) {
  return (
    <TableHead className={cn("text-stone-500 dark:text-zinc-400", alignEnd && "text-right", className)}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={cn(
          "h-8 gap-1 px-2 font-medium text-stone-600 hover:text-stone-900 dark:text-zinc-300 dark:hover:text-zinc-50",
          alignEnd ? "-mr-2 ml-auto flex w-full justify-end" : "-ml-2"
        )}
        onClick={onClick}
      >
        {label}
        {active ? (
          dir === "asc" ? (
            <ArrowUp className="h-3.5 w-3.5 opacity-70" />
          ) : (
            <ArrowDown className="h-3.5 w-3.5 opacity-70" />
          )
        ) : (
          <ArrowUpDown className="h-3.5 w-3.5 opacity-40" />
        )}
      </Button>
    </TableHead>
  );
}

function computeHeaderStats(alerts: AlertRecord[]) {
  const active = alerts.filter((a) => a.status !== "closed").length;
  const unacknowledged = alerts.filter((a) => a.status === "open").length;
  const critical = alerts.filter((a) => a.riskLevel === "high" && a.status !== "closed").length;
  const subscribed = alerts.filter((a) => a.status === "investigating" || a.status === "acknowledged").length;
  const escalated = alerts.filter((a) => a.status === "investigating").length;
  return { active, unacknowledged, critical, subscribed, escalated };
}

function KpiTile({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
}) {
  return (
    <div className="flex min-w-[140px] flex-1 items-center gap-3 rounded-xl border border-stone-200/90 bg-white px-4 py-3 shadow-none dark:border-white/10 dark:bg-zinc-900">
      <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", accent.iconBg)}>
        <Icon className="h-5 w-5" strokeWidth={1.75} />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold tabular-nums leading-none text-stone-900 dark:text-zinc-50">{value}</p>
        <p className="mt-1 text-xs font-medium text-stone-500 dark:text-zinc-400">{label}</p>
      </div>
    </div>
  );
}

function OccurrenceSpark({ seed }: { seed: string }) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h + seed.charCodeAt(i) * (i + 1)) % 997;
  const bars = Array.from({ length: 5 }, (_, i) => {
    const v = ((h >> (i * 3)) & 7) / 7;
    return Math.max(0.2, v);
  });
  return (
    <div className="flex h-8 items-end gap-0.5" aria-hidden title="Relative activity (derived from alert id)">
      {bars.map((hgt, i) => (
        <div
          key={i}
          className="w-1 rounded-sm bg-orange-500/85 dark:bg-orange-500/70"
          style={{ height: `${hgt * 100}%` }}
        />
      ))}
    </div>
  );
}

/** Split Firestore-style `rule_flags` (comma-separated) into display tokens. */
function parseRuleFlags(ruleFlags: string): string[] {
  return ruleFlags
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const lower = s.toLowerCase();
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    });
}

function RuleFlagBadges({ ruleFlags, alignStart }: { ruleFlags: string; alignStart?: boolean }) {
  const tags = parseRuleFlags(ruleFlags);
  if (tags.length === 0) {
    return <span className="text-xs text-stone-400 dark:text-zinc-500">—</span>;
  }
  return (
    <div className={cn("flex flex-wrap gap-1", alignStart ? "justify-start" : "justify-end")}>
      {tags.map((tag, i) => (
        <span
          key={`${tag}-${i}`}
          className="inline-flex rounded-md border border-orange-200/90 bg-orange-50/80 px-2 py-0.5 text-[11px] font-medium text-stone-800 dark:border-orange-500/40 dark:bg-orange-950/35 dark:text-orange-100"
        >
          {tag}
        </span>
      ))}
    </div>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <p className="text-xs font-medium text-stone-500 dark:text-zinc-400">{label}</p>
      <p className="break-all text-sm text-stone-900 dark:text-zinc-100">{value}</p>
    </div>
  );
}

function queueTabFilter(tab: QueueTab, a: AlertRecord): boolean {
  if (tab === "all") return true;
  if (tab === "active") return a.status !== "closed";
  return a.status === "closed";
}

export function AlertsPageClient() {
  const backendOk = Boolean(getBackendBaseUrl());
  const {
    data: records = [],
    error: loadError,
    isLoading,
    mutate,
  } = useSWR(backendOk ? "alerts-page" : null, () => fetchAlerts({ limit: 200 }), { refreshInterval: 8000 });

  const [search, setSearch] = useState("");
  const [queueTab, setQueueTab] = useState<QueueTab>("all");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const channels = useMemo(() => {
    const s = new Set(records.map((a) => a.channel));
    return Array.from(s).sort((a, b) => a.localeCompare(b));
  }, [records]);

  const headerStats = useMemo(() => computeHeaderStats(records), [records]);

  const filterBadgeCount = (riskFilter !== "all" ? 1 : 0) + (channelFilter !== "all" ? 1 : 0);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return records.filter((a) => {
      if (!queueTabFilter(queueTab, a)) return false;
      if (riskFilter !== "all" && a.riskLevel !== riskFilter) return false;
      if (channelFilter !== "all" && a.channel !== channelFilter) return false;
      if (!q) return true;
      const hay = [
        a.alertId,
        a.accountId,
        a.clusterId,
        a.ruleFlags,
        a.channel,
        a.behaviorSignature,
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [search, queueTab, riskFilter, channelFilter, records]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    const mul = sortDir === "asc" ? 1 : -1;
    arr.sort((a, b) => {
      if (sortKey === "timestamp") {
        return (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) * mul;
      }
      if (sortKey === "riskScore") {
        return (a.riskScore - b.riskScore) * mul;
      }
      return (a.amount - b.amount) * mul;
    });
    return arr;
  }, [filtered, sortKey, sortDir]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const pageClamped = Math.min(page, pageCount);
  const pageSlice = useMemo(() => {
    const start = (pageClamped - 1) * PAGE_SIZE;
    return sorted.slice(start, start + PAGE_SIZE);
  }, [sorted, pageClamped]);

  useEffect(() => {
    setPage(1);
  }, [search, queueTab, riskFilter, channelFilter]);

  useEffect(() => {
    if (sorted.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !sorted.some((a) => a.alertId === selectedId)) {
      setSelectedId(sorted[0].alertId);
    }
  }, [sorted, selectedId]);

  const selected = useMemo(
    () => sorted.find((a) => a.alertId === selectedId) ?? null,
    [sorted, selectedId]
  );

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "timestamp" ? "desc" : "desc");
    }
  };

  const rowBorderClass = (level: AlertRiskLevel) => {
    if (level === "high") return accent.barHigh;
    if (level === "medium") return accent.barMed;
    return accent.barLow;
  };

  const from = sorted.length === 0 ? 0 : (pageClamped - 1) * PAGE_SIZE + 1;
  const to = Math.min(pageClamped * PAGE_SIZE, sorted.length);

  return (
    <div className="space-y-5">
      {!backendOk ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-100">
          Set <code className="rounded bg-white/70 px-1 dark:bg-black/30">NEXT_PUBLIC_BACKEND_URL</code> (e.g.{" "}
          <code className="rounded bg-white/70 px-1 dark:bg-black/30">http://localhost:8810</code>) to load alerts.
        </div>
      ) : null}
      {loadError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-500/40 dark:bg-red-950/40 dark:text-red-100">
          Failed to load alerts: {loadError.message}
        </div>
      ) : null}
      {isLoading && !records.length ? (
        <p className="text-sm text-stone-500 dark:text-zinc-400">Loading alerts…</p>
      ) : null}
      {/* Breadcrumb */}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Button variant="ghost" size="sm" className="-ml-2 h-8 gap-1 px-2 text-stone-600 hover:text-stone-900 dark:text-zinc-400 dark:hover:text-zinc-100" asChild>
          <Link href="/dashboard">
            <ChevronLeft className="h-4 w-4" />
            Dashboard
          </Link>
        </Button>
        <span className="text-stone-300 dark:text-zinc-600">/</span>
        <span className="font-semibold text-stone-900 dark:text-zinc-100">Alerts</span>
      </div>

      {/* KPI strip (reference-style) */}
      <div className="flex flex-wrap gap-3">
        <KpiTile icon={Bell} label="Active alerts" value={headerStats.active} />
        <KpiTile icon={ThumbsUp} label="Unacknowledged" value={headerStats.unacknowledged} />
        <KpiTile icon={AlertTriangle} label="Critical alerts" value={headerStats.critical} />
        <KpiTile icon={Bookmark} label="Subscribed / tracked" value={headerStats.subscribed} />
        <KpiTile icon={Flag} label="Escalated" value={headerStats.escalated} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
        <Card className="overflow-hidden rounded-xl border-stone-200/90 bg-white shadow-none dark:border-white/10 dark:bg-zinc-900">
          <CardHeader className="space-y-4 border-b border-stone-100 pb-4 dark:border-white/10">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
                <CardTitle className="text-lg text-stone-900 dark:text-zinc-50">Alerts</CardTitle>
                <div
                  className="inline-flex rounded-full bg-stone-100 p-1 dark:bg-zinc-800"
                  role="tablist"
                  aria-label="Alert queue"
                >
                  {(
                    [
                      { id: "all" as const, label: "All" },
                      { id: "active" as const, label: "Active" },
                      { id: "resolved" as const, label: "Resolved" },
                    ] as const
                  ).map(({ id, label }) => (
                    <button
                      key={id}
                      type="button"
                      role="tab"
                      aria-selected={queueTab === id}
                      onClick={() => setQueueTab(id)}
                      className={cn(
                        "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                        queueTab === id ? accent.pillActive : accent.pillIdle
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-2">
                <Select value={riskFilter} onValueChange={setRiskFilter}>
                  <SelectTrigger className="h-9 w-full min-w-[140px] rounded-lg border-stone-200 bg-white sm:w-[160px] dark:border-white/10 dark:bg-zinc-950">
                    <SelectValue placeholder="All alerts" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All alerts</SelectItem>
                    <SelectItem value="high">Critical risk</SelectItem>
                    <SelectItem value="medium">High risk</SelectItem>
                    <SelectItem value="low">Low risk</SelectItem>
                  </SelectContent>
                </Select>
                <div className="relative w-full sm:w-[180px]">
                  <Select value={channelFilter} onValueChange={setChannelFilter}>
                    <SelectTrigger className="h-9 w-full rounded-lg border-stone-200 bg-white dark:border-white/10 dark:bg-zinc-950">
                      <SelectValue placeholder="Channel" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All channels</SelectItem>
                      {channels.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {channelFilter !== "all" ? (
                    <span className="pointer-events-none absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                      1
                    </span>
                  ) : null}
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="relative h-9 rounded-lg border-stone-200 bg-white dark:border-white/10 dark:bg-zinc-950"
                    >
                      More
                      {filterBadgeCount > 0 ? (
                        <span className="ml-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                          {filterBadgeCount}
                        </span>
                      ) : null}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => {
                        setRiskFilter("all");
                        setChannelFilter("all");
                        setSearch("");
                      }}
                    >
                      Clear filters
                    </DropdownMenuItem>
                    <DropdownMenuItem disabled>Export CSV (soon)</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <Input
                id="alert-search"
                placeholder="Search alerts, accounts, clusters, rules…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-10 rounded-xl border-stone-200 bg-stone-50/80 pl-9 text-stone-900 placeholder:text-stone-400 dark:border-white/10 dark:bg-zinc-950 dark:text-zinc-100"
              />
            </div>
            <CardDescription className="text-xs text-stone-500 dark:text-zinc-400">
              Demo dataset — same fields as Firestore seed. API wiring later.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-stone-100 hover:bg-transparent dark:border-white/10">
                  <TableHead className="pl-6 text-stone-500 dark:text-zinc-400">Details</TableHead>
                  <SortHeader
                    label="Date & time"
                    active={sortKey === "timestamp"}
                    dir={sortDir}
                    onClick={() => toggleSort("timestamp")}
                  />
                  <SortHeader
                    label="Criticality"
                    active={sortKey === "riskScore"}
                    dir={sortDir}
                    onClick={() => toggleSort("riskScore")}
                    className="hidden sm:table-cell"
                  />
                  <TableHead className="hidden text-stone-500 md:table-cell dark:text-zinc-400">Occurrence</TableHead>
                  <SortHeader
                    label="Amount"
                    active={sortKey === "amount"}
                    dir={sortDir}
                    onClick={() => toggleSort("amount")}
                    alignEnd
                    className="w-[1%] whitespace-nowrap pr-2"
                  />
                  <TableHead className="hidden min-w-[148px] pr-6 text-right text-stone-500 lg:table-cell dark:text-zinc-400">
                    Rule signals
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="h-28 text-center text-stone-500 dark:text-zinc-400">
                      No alerts match your filters.
                    </TableCell>
                  </TableRow>
                ) : (
                  pageSlice.map((row) => {
                    const resolvedRow = row.status === "closed";
                    return (
                      <TableRow
                        key={row.alertId}
                        data-state={selected?.alertId === row.alertId ? "selected" : undefined}
                        className={cn(
                          "cursor-pointer border-b border-stone-100 border-l-4 dark:border-white/10",
                          rowBorderClass(row.riskLevel),
                          selected?.alertId === row.alertId && "bg-orange-50/60 dark:bg-orange-950/20",
                          resolvedRow && "opacity-70"
                        )}
                        onClick={() => setSelectedId(row.alertId)}
                      >
                        <TableCell className="max-w-[min(100vw,320px)] pl-6">
                          <div className="flex gap-3">
                            <div className="mt-0.5 shrink-0 text-orange-500 dark:text-orange-400">
                              <Bell className="h-4 w-4" strokeWidth={2} />
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold tabular-nums leading-snug tracking-tight text-stone-900 dark:text-zinc-50">
                                {row.alertId}
                              </p>
                              <p className="mt-0.5 text-xs text-stone-500 dark:text-zinc-400">
                                <span className="uppercase">{row.channel}</span>
                                <span className="mx-1.5 text-stone-300 dark:text-zinc-600" aria-hidden>
                                  ·
                                </span>
                                <span className="font-mono tabular-nums">{maskAccountId(row.accountId)}</span>
                              </p>
                              <p className="mt-1 line-clamp-1 text-[11px] text-stone-400 dark:text-zinc-500">
                                {row.status} · {row.clusterId}
                              </p>
                              <div className="mt-2 lg:hidden">
                                <RuleFlagBadges ruleFlags={row.ruleFlags} alignStart />
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-sm text-stone-600 dark:text-zinc-300">
                          {formatDateTimeLabel(row.timestamp)}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">{criticalityBadge(row.riskLevel)}</TableCell>
                        <TableCell className="hidden md:table-cell">
                          <OccurrenceSpark seed={row.alertId} />
                        </TableCell>
                        <TableCell className="text-right font-semibold tabular-nums text-stone-900 dark:text-zinc-100">
                          {inr.format(row.amount)}
                        </TableCell>
                        <TableCell className="hidden align-top pt-3 lg:table-cell">
                          <RuleFlagBadges ruleFlags={row.ruleFlags} />
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>

            {sorted.length > 0 ? (
              <div className="flex flex-col gap-3 border-t border-stone-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between dark:border-white/10">
                <div className="flex items-center gap-2 text-sm text-stone-500 dark:text-zinc-400">
                  <span className="whitespace-nowrap">Alerts per page</span>
                  <span className="tabular-nums font-medium text-stone-700 dark:text-zinc-200">{PAGE_SIZE}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm tabular-nums text-stone-600 dark:text-zinc-300">
                    {from}–{to} of {sorted.length}
                  </span>
                  <div className="flex gap-1">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8 border-stone-200 dark:border-white/10"
                      disabled={pageClamped <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      aria-label="Previous page"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8 border-stone-200 dark:border-white/10"
                      disabled={pageClamped >= pageCount}
                      onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                      aria-label="Next page"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="flex max-h-[min(720px,calc(100vh-12rem))] flex-col rounded-xl border-stone-200/90 bg-white shadow-none dark:border-white/10 dark:bg-zinc-900">
          <CardHeader className="shrink-0 border-b border-stone-100 pb-3 dark:border-white/10">
            <CardTitle className="text-lg text-stone-900 dark:text-zinc-50">Details</CardTitle>
            <CardDescription className="text-stone-500 dark:text-zinc-400">
              {selected ? selected.alertId : "Select an alert"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-4 px-6 pb-6 pt-4">
            {!selected ? (
              <p className="text-sm text-stone-500 dark:text-zinc-400">No alert selected.</p>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  {criticalityBadge(selected.riskLevel)}
                  <span className="text-xs text-stone-500 dark:text-zinc-400">
                    ({criticalityLabel(selected.riskLevel)} · {(selected.riskScore * 100).toFixed(0)}% model score)
                  </span>
                  {statusBadge(selected.status)}
                  <Select
                    value={selected.status}
                    onValueChange={async (v) => {
                      try {
                        await patchAlertStatus(selected.alertId, v as AlertStatus);
                        await mutate();
                      } catch (err) {
                        console.error(err);
                      }
                    }}
                  >
                    <SelectTrigger className="h-8 w-[168px] rounded-lg border-stone-200 bg-white text-xs dark:border-white/10 dark:bg-zinc-950">
                      <SelectValue placeholder="Set status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">open</SelectItem>
                      <SelectItem value="acknowledged">acknowledged</SelectItem>
                      <SelectItem value="investigating">investigating</SelectItem>
                      <SelectItem value="closed">closed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <ScrollArea className="min-h-0 flex-1 pr-3">
                  <div className="grid gap-4 pb-2">
                    <DetailField label="Account" value={selected.accountId} />
                    <DetailField label="Amount" value={inr.format(selected.amount)} />
                    <DetailField label="Transaction time" value={formatWhenDetail(selected.timestamp)} />
                    <DetailField label="Channel" value={selected.channel} />
                    <DetailField label="Risk score" value={`${(selected.riskScore * 100).toFixed(1)}%`} />
                    <DetailField label="Rule flags" value={selected.ruleFlags} />
                    <DetailField label="Behavior signature" value={selected.behaviorSignature} />
                    <DetailField label="Cluster" value={selected.clusterId} />
                    <DetailField label="Device fingerprint" value={selected.deviceFingerprint} />
                    <DetailField label="IP address" value={selected.ipAddress} />
                    <DetailField label="Created" value={formatWhenDetail(selected.createdAt)} />
                    <DetailField label="Updated" value={formatWhenDetail(selected.updatedAt)} />
                  </div>
                </ScrollArea>
                <div className="flex shrink-0 flex-col gap-2 border-t border-stone-100 pt-4 dark:border-white/10 sm:flex-row sm:flex-wrap">
                  <Button asChild className="rounded-xl bg-orange-500 hover:bg-orange-600 dark:bg-orange-600 dark:hover:bg-orange-500">
                    <Link href={`/dashboard/alerts/${encodeURIComponent(selected.alertId)}/report`}>
                      View STR report
                      <FileText className="h-4 w-4 opacity-90" />
                    </Link>
                  </Button>
                  <Button variant="outline" asChild className="rounded-xl border-stone-200 dark:border-white/10">
                    <Link href="/dashboard/review-queue">
                      Review queue
                      <ExternalLink className="h-4 w-4 opacity-90" />
                    </Link>
                  </Button>
                  <Button variant="outline" asChild className="rounded-xl border-stone-200 dark:border-white/10">
                    <Link href="/dashboard/str-viewer">STR viewer</Link>
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

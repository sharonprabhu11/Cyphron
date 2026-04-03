"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  MOCK_LIVE_GRAPH_LINKS,
  MOCK_LIVE_GRAPH_NODES,
  type MockGraphNodeTier,
} from "@/lib/dashboard/mockLiveGraph";
import { fetchSubgraph, getBackendBaseUrl, postSimulatorPublish } from "@/lib/api";
import type { SubgraphResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[420px] items-center justify-center bg-[#fafaf9] text-sm text-stone-400 dark:bg-zinc-950 dark:text-zinc-500">
      Preparing graph…
    </div>
  ),
});

type GraphNode = {
  id: string;
  label?: string;
  tier?: MockGraphNodeTier;
};

type GraphLink = {
  source: string | GraphNode;
  target: string | GraphNode;
  amount?: number;
  channel?: string;
};

function tierOf(id: string): MockGraphNodeTier {
  const n = MOCK_LIVE_GRAPH_NODES.find((x) => x.id === id);
  return n?.tier ?? "neutral";
}

function normalizeApiGraph(g: SubgraphResponse): { nodes: GraphNode[]; links: GraphLink[] } {
  return {
    nodes: g.nodes.map((n) => ({ id: n.id, label: n.label, tier: "neutral" as const })),
    links: g.links.map((l) => ({
      source: l.source,
      target: l.target,
      amount: l.amount,
      channel: l.channel,
    })),
  };
}

function mockGraphData(): { nodes: GraphNode[]; links: GraphLink[] } {
  return {
    nodes: MOCK_LIVE_GRAPH_NODES.map((n) => ({ id: n.id, label: n.label, tier: n.tier })),
    links: MOCK_LIVE_GRAPH_LINKS.map((l) => ({ ...l })),
  };
}

export function LiveGraphClient() {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [source, setSource] = useState<"demo" | "api">("demo");
  const [accountId, setAccountId] = useState("acct_core_7f2a");
  const [hops, setHops] = useState(2);
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; links: GraphLink[] } | null>(() => mockGraphData());
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [simMsg, setSimMsg] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pulse, setPulse] = useState(0);
  const [tick, setTick] = useState(0);

  const backendOk = useMemo(() => Boolean(getBackendBaseUrl()), []);
  const isDark = resolvedTheme === "dark";

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const id = setInterval(() => setPulse((p) => p + 1), 2400);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (source === "demo") {
      setGraph(mockGraphData());
      setError(null);
      setSelectedId(null);
      setTick((t) => t + 1);
    }
  }, [source]);

  const loadApi = useCallback(async () => {
    if (!accountId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const g = await fetchSubgraph(accountId.trim(), hops, 250);
      setGraph(normalizeApiGraph(g));
      setSelectedId(null);
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [accountId, hops]);

  const bg = isDark ? "#09090b" : "#fafaf9";
  const inkMuted = isDark ? "#71717a" : "#64748b";
  const linkBase = isDark ? "rgba(244,244,245,0.14)" : "rgba(15,40,35,0.14)";
  const breathe = 0.04 + 0.03 * Math.sin(pulse * 0.8);

  const nodeColor = useCallback(
    (n: GraphNode) => {
      const t = n.tier ?? tierOf(n.id);
      if (t === "focal") return isDark ? "#60a5fa" : "#2563eb";
      if (t === "risk") return isDark ? "#f87171" : "#dc2626";
      return isDark ? "#a1a1aa" : "#64748b";
    },
    [isDark]
  );

  const nodeCanvasObject = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as GraphNode & { x?: number; y?: number };
      const x = n.x ?? 0;
      const y = n.y ?? 0;
      const t = n.tier ?? tierOf(n.id);
      const r = t === "focal" ? 8 : t === "risk" ? 6.5 : 5;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fillStyle = nodeColor(n);
      ctx.fill();
      if (t === "focal") {
        ctx.strokeStyle = isDark ? "rgba(96,165,250,0.45)" : "rgba(37,99,235,0.35)";
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }
      // Target ~7px on screen; clamp local size so extreme zoom stays readable, not billboard-sized.
      const targetScreenPx = 7;
      const fontPx = Math.min(14, Math.max(5.5, targetScreenPx / globalScale));
      ctx.font = `400 ${fontPx}px var(--font-sans), ui-sans-serif, system-ui`;
      ctx.textAlign = "center";
      ctx.fillStyle = inkMuted;
      const id = n.id || "";
      const short =
        id.length > 11 ? `${id.slice(0, 9)}…` : id;
      ctx.fillText(short, x, y + r + fontPx * 0.85 + 1.5 / globalScale);
    },
    [inkMuted, isDark, nodeColor]
  );

  const selected = graph?.nodes.find((n) => n.id === selectedId);
  const selectedLinks =
    graph?.links.filter((l) => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      return selectedId && (s === selectedId || t === selectedId);
    }) ?? [];

  if (!mounted) {
    return <div className="min-h-[420px] rounded-2xl bg-[#fafaf9] dark:bg-zinc-950" />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1 rounded-full border border-stone-200/90 bg-stone-50/80 p-1 dark:border-white/10 dark:bg-zinc-900/80">
          <button
            type="button"
            onClick={() => setSource("demo")}
            className={cn(
              "rounded-full px-4 py-1.5 text-xs font-medium tracking-wide transition-colors",
              source === "demo"
                ? "bg-white text-stone-900 shadow-sm dark:bg-zinc-800 dark:text-zinc-100"
                : "text-stone-500 hover:text-stone-800 dark:text-zinc-500 dark:hover:text-zinc-300"
            )}
          >
            Demo graph
          </button>
          <button
            type="button"
            disabled={!backendOk}
            onClick={() => setSource("api")}
            className={cn(
              "rounded-full px-4 py-1.5 text-xs font-medium tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-40",
              source === "api"
                ? "bg-white text-stone-900 shadow-sm dark:bg-zinc-800 dark:text-zinc-100"
                : "text-stone-500 hover:text-stone-800 dark:text-zinc-500 dark:hover:text-zinc-300"
            )}
          >
            Live · Neo4j
          </button>
        </div>
        <p className="text-xs font-medium tracking-[0.2em] text-stone-400 uppercase dark:text-zinc-500">
          {source === "demo" ? "Simulated flow · fan-out" : "Subgraph query"}
        </p>
      </div>

      {source === "api" ? (
        <div className="flex flex-wrap items-end gap-4 border-b border-stone-100 pb-6 dark:border-white/10">
          <div className="grid gap-1.5">
            <label className="text-[11px] font-medium tracking-wide text-stone-500 uppercase dark:text-zinc-400" htmlFor="acct">
              Account id
            </label>
            <Input
              id="acct"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="h-9 w-56 rounded-lg border-stone-200 bg-white text-sm dark:border-white/10 dark:bg-zinc-950"
              placeholder="ACC_100"
            />
          </div>
          <div className="grid gap-1.5">
            <label className="text-[11px] font-medium tracking-wide text-stone-500 uppercase dark:text-zinc-400" htmlFor="hops">
              Hops
            </label>
            <Input
              id="hops"
              type="number"
              min={1}
              max={5}
              value={hops}
              onChange={(e) => setHops(Math.min(5, Math.max(1, Number(e.target.value) || 1)))}
              className="h-9 w-20 rounded-lg border-stone-200 bg-white text-sm dark:border-white/10 dark:bg-zinc-950"
            />
          </div>
          <Button
            type="button"
            className="h-9 rounded-lg bg-stone-900 px-5 text-xs font-medium tracking-wide text-white hover:bg-stone-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
            onClick={() => void loadApi()}
          >
            {loading ? "Loading…" : "Load subgraph"}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-9 rounded-lg border-stone-200 text-xs dark:border-white/10"
            onClick={async () => {
              try {
                const r = await postSimulatorPublish({ fraudType: "normal" });
                setSimMsg(`Published ${r.transactionId}`);
              } catch (e) {
                setSimMsg(e instanceof Error ? e.message : "Publish failed");
              }
            }}
          >
            Simulator
          </Button>
        </div>
      ) : null}

      {!backendOk && source === "api" ? (
        <p className="text-xs text-amber-800 dark:text-amber-200/90">
          Set <code className="rounded bg-stone-100 px-1 dark:bg-zinc-800">NEXT_PUBLIC_BACKEND_URL</code> for Neo4j mode.
        </p>
      ) : null}
      {error ? <p className="text-xs text-red-600 dark:text-red-400">{error}</p> : null}
      {simMsg ? <p className="text-[11px] text-stone-400 dark:text-zinc-500">{simMsg}</p> : null}

      <div className="grid gap-6 lg:grid-cols-[1fr_220px]">
        <div
          className="relative overflow-hidden rounded-2xl border border-stone-200/80 shadow-[0_1px_0_rgba(0,0,0,0.03)] dark:border-white/[0.08] dark:shadow-none"
          style={{ minHeight: "min(520px, 72vh)" }}
        >
          <div className="pointer-events-none absolute left-5 top-4 z-10">
            <span className="text-[10px] font-semibold tracking-[0.25em] text-stone-400 uppercase dark:text-zinc-500">
              {source === "demo" ? "Live preview" : "Graph"}
            </span>
          </div>
          {graph && graph.nodes.length > 0 ? (
            <ForceGraph2D
              key={`${source}-${tick}`}
              graphData={graph as { nodes: object[]; links: object[] }}
              backgroundColor={bg}
              nodeCanvasObject={nodeCanvasObject}
              nodePointerAreaPaint={(node, color, ctx) => {
                const n = node as GraphNode & { x?: number; y?: number };
                const x = n.x ?? 0;
                const y = n.y ?? 0;
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(x, y, 14, 0, 2 * Math.PI);
                ctx.fill();
              }}
              linkColor={() => linkBase}
              linkWidth={(l) => {
                const link = l as GraphLink;
                const a = link.amount;
                if (a == null) return 0.9;
                return Math.min(2.4, 0.7 + Math.sqrt(a) / 120);
              }}
              linkDirectionalParticles={source === "demo" ? 2 : 1}
              linkDirectionalParticleWidth={1.2}
              linkDirectionalParticleSpeed={0.006}
              linkDirectionalParticleColor={() =>
                isDark ? `rgba(96,165,250,${0.35 + breathe})` : `rgba(37,99,235,${0.25 + breathe})`
              }
              cooldownTicks={source === "demo" ? 120 : 90}
              d3AlphaDecay={0.022}
              d3VelocityDecay={0.35}
              onNodeClick={(node) => {
                const n = node as GraphNode;
                setSelectedId(n.id === selectedId ? null : n.id);
              }}
              onBackgroundClick={() => setSelectedId(null)}
            />
          ) : (
            <div
              className="flex h-[min(520px,72vh)] items-center justify-center text-sm text-stone-400 dark:text-zinc-500"
              style={{ backgroundColor: bg }}
            >
              {source === "api" && !loading
                ? "Load a subgraph to visualize transfers."
                : loading
                  ? "Loading…"
                  : "No graph data."}
            </div>
          )}
        </div>

        <aside className="flex flex-col justify-between rounded-2xl border border-stone-200/80 bg-stone-50/50 p-5 dark:border-white/[0.08] dark:bg-zinc-900/40">
          <div>
            <h3 className="text-[10px] font-semibold tracking-[0.2em] text-stone-400 uppercase dark:text-zinc-500">
              Selection
            </h3>
            {selected ? (
              <div className="mt-4 space-y-3">
                <p className="font-mono text-sm text-stone-900 dark:text-zinc-100">{selected.id}</p>
                {selected.label ? (
                  <p className="text-xs leading-relaxed text-stone-600 dark:text-zinc-400">{selected.label}</p>
                ) : null}
                <p className="text-[11px] text-stone-400 dark:text-zinc-500">
                  {selectedLinks.length} adjacent edge{selectedLinks.length === 1 ? "" : "s"}
                </p>
                <ul className="max-h-40 space-y-2 overflow-y-auto text-[11px] text-stone-500 dark:text-zinc-400">
                  {selectedLinks.slice(0, 8).map((l, i) => {
                    const s = typeof l.source === "object" ? l.source.id : l.source;
                    const t = typeof l.target === "object" ? l.target.id : l.target;
                    const other = s === selected.id ? t : s;
                    return (
                      <li key={i} className="border-l-2 border-stone-200 pl-2 dark:border-zinc-700">
                        <span className="font-mono text-stone-700 dark:text-zinc-300">{other}</span>
                        {l.amount != null ? (
                          <span className="ml-1 text-stone-400 dark:text-zinc-500">
                            · ₹{l.amount.toLocaleString("en-IN")}
                          </span>
                        ) : null}
                        {l.channel ? (
                          <span className="block text-[10px] uppercase tracking-wider text-stone-400 dark:text-zinc-500">
                            {l.channel}
                          </span>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="mt-4 text-xs leading-relaxed text-stone-500 dark:text-zinc-400">
                Click a node to inspect connections and channel metadata.
              </p>
            )}
          </div>
          <p className="mt-8 text-[10px] leading-relaxed text-stone-400 dark:text-zinc-600">
            Demo uses static topology. Neo4j mode calls{" "}
            <code className="rounded bg-stone-200/60 px-1 text-[9px] dark:bg-zinc-800">/api/v1/graph/subgraph</code>.
          </p>
        </aside>
      </div>
    </div>
  );
}

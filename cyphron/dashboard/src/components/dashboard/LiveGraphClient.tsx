"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchSubgraph, getBackendBaseUrl, postSimulatorPublish } from "@/lib/api";
import type { SubgraphResponse } from "@/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => <div className="h-[480px] rounded-xl bg-surface-muted/50 dark:bg-zinc-800/50" />,
});

export function LiveGraphClient() {
  const [accountId, setAccountId] = useState("ACC_100");
  const [hops, setHops] = useState(2);
  const [graph, setGraph] = useState<SubgraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [simMsg, setSimMsg] = useState<string | null>(null);

  const backendOk = useMemo(() => Boolean(getBackendBaseUrl()), []);

  const load = useCallback(async () => {
    if (!accountId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const g = await fetchSubgraph(accountId.trim(), hops, 250);
      setGraph(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [accountId, hops]);

  const graphData = useMemo(() => {
    if (!graph) return { nodes: [] as { id: string }[], links: [] as { source: string; target: string }[] };
    return {
      nodes: graph.nodes.map((n) => ({ id: n.id, label: n.label })),
      links: graph.links.map((l) => ({
        source: l.source,
        target: l.target,
      })),
    };
  }, [graph]);

  return (
    <div className="space-y-4">
      {!backendOk ? (
        <p className="text-sm text-amber-800 dark:text-amber-200">
          Set NEXT_PUBLIC_BACKEND_URL to use the live graph (FastAPI + Neo4j).
        </p>
      ) : null}
      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1">
          <label className="text-xs font-medium text-ink-muted" htmlFor="acct">
            Account id
          </label>
          <Input
            id="acct"
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="w-56 rounded-lg"
            placeholder="ACC_100"
          />
        </div>
        <div className="grid gap-1">
          <label className="text-xs font-medium text-ink-muted" htmlFor="hops">
            Hops (1–5)
          </label>
          <Input
            id="hops"
            type="number"
            min={1}
            max={5}
            value={hops}
            onChange={(e) => setHops(Math.min(5, Math.max(1, Number(e.target.value) || 1)))}
            className="w-24 rounded-lg"
          />
        </div>
        <Button type="button" className="rounded-lg bg-orange-500 hover:bg-orange-600" onClick={() => void load()}>
          {loading ? "Loading…" : "Load subgraph"}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="rounded-lg"
          onClick={async () => {
            try {
              const r = await postSimulatorPublish({ fraudType: "normal" });
              setSimMsg(`Published ${r.transactionId}`);
            } catch (e) {
              setSimMsg(e instanceof Error ? e.message : "Publish failed");
            }
          }}
        >
          Publish one (simulator)
        </Button>
      </div>
      {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
      {simMsg ? <p className="text-xs text-ink-muted">{simMsg}</p> : null}
      <div className="h-[min(560px,70vh)] w-full overflow-hidden rounded-xl border border-border bg-white dark:border-white/10 dark:bg-zinc-900">
        {graphData.nodes.length > 0 ? (
          <ForceGraph2D
            graphData={graphData}
            nodeLabel="id"
            nodeAutoColorBy="id"
            linkDirectionalParticles={1}
            cooldownTicks={80}
            onEngineStop={() => undefined}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-6 text-sm text-ink-muted">
            {loading ? "Loading…" : "Load a subgraph to visualize Neo4j transfers."}
          </div>
        )}
      </div>
    </div>
  );
}

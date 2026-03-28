<<<<<<< HEAD
export default function LiveGraphPage() {
  return (
    <main style={{ padding: 24 }}>
      <h2 style={{ margin: 0 }}>Live Graph</h2>
      <p style={{ marginTop: 12, opacity: 0.8 }}>Placeholder page.</p>
    </main>
  );
}

=======
import { LiveGraphClient } from "@/components/dashboard/LiveGraphClient";

export default function LiveGraphPage() {
  return (
    <div className="rounded-xl border border-border bg-white p-6 dark:border-white/10 dark:bg-zinc-900">
      <h2 className="text-lg font-semibold text-ink">Live graph</h2>
      <p className="mt-2 text-sm text-ink-muted">
        Neighborhood view from Neo4j (<code className="text-xs">GET /api/v1/graph/subgraph</code>).
      </p>
      <div className="mt-6">
        <LiveGraphClient />
      </div>
    </div>
  );
}
>>>>>>> pr-7

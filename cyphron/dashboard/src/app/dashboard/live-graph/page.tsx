import { LiveGraphClient } from "@/components/dashboard/LiveGraphClient";

export default function LiveGraphPage() {
  return (
    <div className="mx-auto max-w-[1400px] space-y-8">
      <header className="space-y-2">
        <p className="text-[10px] font-semibold tracking-[0.3em] text-stone-400 uppercase dark:text-zinc-500">
          Graph intelligence
        </p>
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-zinc-50">Live transaction graph</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-stone-500 dark:text-zinc-400">
          Explore account neighborhoods: fan-out, pass-throughs, and high-risk nodes. Use the demo to validate the
          experience without Neo4j, or connect the pipeline for{" "}
          <code className="rounded bg-stone-100 px-1.5 py-0.5 text-xs text-stone-700 dark:bg-zinc-800 dark:text-zinc-300">
            /api/v1/graph/subgraph
          </code>
          .
        </p>
      </header>
      <LiveGraphClient />
    </div>
  );
}

/**
 * Representative “live” money-flow subgraph for dashboard demo (fan-out + sink).
 * Shape matches API `SubgraphResponse` with optional link metadata for the UI.
 */

import type { SubgraphResponse } from "@/lib/api";

/** Visual tier for canvas styling (not sent to Neo4j API). */
export type MockGraphNodeTier = "focal" | "risk" | "neutral";

export type MockGraphNode = { id: string; label: string; tier: MockGraphNodeTier };

export type MockGraphLink = {
  source: string;
  target: string;
  amount?: number;
  channel?: string;
};

export const MOCK_LIVE_GRAPH_NODES: MockGraphNode[] = [
  { id: "acct_core_7f2a", label: "Core account", tier: "focal" },
  { id: "acct_spoke_01", label: "Spoke · UPI", tier: "neutral" },
  { id: "acct_spoke_02", label: "Spoke · UPI", tier: "neutral" },
  { id: "acct_spoke_03", label: "Spoke · ATM", tier: "neutral" },
  { id: "acct_spoke_04", label: "Spoke · WEB", tier: "neutral" },
  { id: "acct_spoke_05", label: "Spoke · MOBILE", tier: "neutral" },
  { id: "merch_pool_a", label: "Merchant A", tier: "neutral" },
  { id: "merch_pool_b", label: "Merchant B", tier: "neutral" },
  { id: "acct_mule_x", label: "Flagged cluster", tier: "risk" },
  { id: "acct_mule_y", label: "Shared device", tier: "risk" },
  { id: "acct_pass_12", label: "Pass-through", tier: "neutral" },
  { id: "acct_pass_13", label: "Pass-through", tier: "neutral" },
];

export const MOCK_LIVE_GRAPH_LINKS: MockGraphLink[] = [
  { source: "acct_core_7f2a", target: "acct_spoke_01", amount: 8200, channel: "UPI" },
  { source: "acct_core_7f2a", target: "acct_spoke_02", amount: 6400, channel: "UPI" },
  { source: "acct_core_7f2a", target: "acct_spoke_03", amount: 9900, channel: "ATM" },
  { source: "acct_core_7f2a", target: "acct_spoke_04", amount: 4100, channel: "WEB" },
  { source: "acct_core_7f2a", target: "acct_spoke_05", amount: 7300, channel: "MOBILE" },
  { source: "acct_spoke_01", target: "merch_pool_a", amount: 8000, channel: "UPI" },
  { source: "acct_spoke_02", target: "merch_pool_a", amount: 6200, channel: "UPI" },
  { source: "acct_spoke_03", target: "merch_pool_b", amount: 9800, channel: "ATM" },
  { source: "acct_spoke_04", target: "acct_mule_x", amount: 4000, channel: "WEB" },
  { source: "acct_spoke_05", target: "acct_mule_y", amount: 7100, channel: "MOBILE" },
  { source: "acct_mule_x", target: "acct_pass_12", amount: 3800, channel: "UPI" },
  { source: "acct_mule_y", target: "acct_pass_12", amount: 6900, channel: "UPI" },
  { source: "acct_pass_12", target: "acct_pass_13", amount: 10200, channel: "WEB" },
  { source: "merch_pool_a", target: "acct_pass_13", amount: 2100, channel: "UPI" },
];

/** Plain API shape (labels only) if you need to pass through fetchers. */
export function mockGraphAsSubgraphResponse(): SubgraphResponse {
  return {
    nodes: MOCK_LIVE_GRAPH_NODES.map(({ id, label }) => ({ id, label })),
    links: MOCK_LIVE_GRAPH_LINKS.map(({ source, target, amount, channel }) => ({
      source,
      target,
      amount,
      channel,
    })),
  };
}

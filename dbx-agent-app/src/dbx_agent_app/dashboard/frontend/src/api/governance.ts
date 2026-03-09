import type { LineageGraph, GovernanceStatus } from "../types/lineage";
import { apiFetch } from "./client";

export function fetchAgentLineage(name: string): Promise<LineageGraph> {
  return apiFetch<LineageGraph>(
    `/api/agents/${encodeURIComponent(name)}/lineage`,
  );
}

export function fetchAgentGovernance(name: string): Promise<GovernanceStatus> {
  return apiFetch<GovernanceStatus>(
    `/api/agents/${encodeURIComponent(name)}/governance`,
  );
}

export function fetchWorkspaceLineage(
  warehouseId?: string,
): Promise<LineageGraph> {
  const params = warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : "";
  return apiFetch<LineageGraph>(`/api/lineage${params}`);
}

export function observeTrace(agentName: string, trace: Record<string, unknown>): void {
  fetch("/api/lineage/observe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_name: agentName, trace }),
  }).catch(() => {});
}

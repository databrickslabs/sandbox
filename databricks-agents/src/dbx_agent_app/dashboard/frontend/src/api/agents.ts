import type { Agent, AgentCard, ScanResult } from "../types";
import { apiFetch } from "./client";

export function fetchAgents(): Promise<Agent[]> {
  return apiFetch<Agent[]>("/api/agents");
}

export function fetchAgentCard(name: string): Promise<AgentCard> {
  return apiFetch<AgentCard>(`/api/agents/${encodeURIComponent(name)}/card`);
}

export function triggerScan(): Promise<ScanResult> {
  return apiFetch<ScanResult>("/api/scan", { method: "POST" });
}

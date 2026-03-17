/* System Builder API client — uses apiFetch from client.ts */

import { apiFetch } from "./client";
import type { SystemDefinition, SystemCreate, DeployResult, DeployProgress } from "../types/systems";

export async function fetchSystems(): Promise<SystemDefinition[]> {
  return apiFetch<SystemDefinition[]>("/api/systems");
}

export async function fetchSystem(id: string): Promise<SystemDefinition> {
  return apiFetch<SystemDefinition>(`/api/systems/${id}`);
}

export async function createSystem(data: SystemCreate): Promise<SystemDefinition> {
  return apiFetch<SystemDefinition>("/api/systems", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSystem(
  id: string,
  data: Partial<SystemCreate>,
): Promise<SystemDefinition> {
  return apiFetch<SystemDefinition>(`/api/systems/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSystem(id: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`/api/systems/${id}`, { method: "DELETE" });
}

export async function deploySystem(id: string): Promise<DeployResult> {
  return apiFetch<DeployResult>(`/api/systems/${id}/deploy`, { method: "POST" });
}

/** Start async deploy — returns deploy_id for polling */
export async function startDeploy(id: string): Promise<{ deploy_id: string; status: string }> {
  return apiFetch<{ deploy_id: string; status: string }>(`/api/systems/${id}/deploy`, {
    method: "POST",
    body: JSON.stringify({ async: true }),
  });
}

/** Poll deploy progress */
export async function getDeployStatus(id: string): Promise<DeployProgress> {
  return apiFetch<DeployProgress>(`/api/systems/${id}/deploy/status`);
}

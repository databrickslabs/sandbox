import type { JsonRpcRequest, JsonRpcResponse } from "../types";
import { apiFetch } from "./client";

export function mcpRequest(
  agentName: string,
  payload: JsonRpcRequest,
): Promise<JsonRpcResponse> {
  return apiFetch<JsonRpcResponse>(
    `/api/agents/${encodeURIComponent(agentName)}/mcp`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

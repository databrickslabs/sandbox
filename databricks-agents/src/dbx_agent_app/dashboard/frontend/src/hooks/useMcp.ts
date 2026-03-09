import { useState, useCallback } from "react";
import type { AgentTool, JsonRpcResponse } from "../types";
import { mcpRequest } from "../api/mcp";

interface UseMcpResult {
  tools: AgentTool[];
  toolsLoading: boolean;
  toolsError: string | null;
  lastResponse: JsonRpcResponse | null;
  sendingMcp: boolean;
  loadTools: () => Promise<void>;
  sendRaw: (method: string, params: Record<string, unknown>) => Promise<void>;
  callTool: (name: string, args: Record<string, unknown>) => Promise<void>;
}

export function useMcp(agentName: string): UseMcpResult {
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<JsonRpcResponse | null>(
    null,
  );
  const [sendingMcp, setSendingMcp] = useState(false);

  const loadTools = useCallback(async () => {
    setToolsLoading(true);
    setToolsError(null);
    try {
      const resp = await mcpRequest(agentName, {
        jsonrpc: "2.0",
        id: "1",
        method: "tools/list",
        params: {},
      });
      const result = resp.result as { tools?: AgentTool[] } | undefined;
      setTools(result?.tools ?? []);
    } catch (e) {
      setToolsError(e instanceof Error ? e.message : "Failed to load tools");
    } finally {
      setToolsLoading(false);
    }
  }, [agentName]);

  const sendRaw = useCallback(
    async (method: string, params: Record<string, unknown>) => {
      setSendingMcp(true);
      try {
        const resp = await mcpRequest(agentName, {
          jsonrpc: "2.0",
          id: String(Date.now()),
          method,
          params,
        });
        setLastResponse(resp);
      } catch (e) {
        setLastResponse({
          jsonrpc: "2.0",
          id: null,
          error: {
            code: -1,
            message: e instanceof Error ? e.message : "Request failed",
          },
        });
      } finally {
        setSendingMcp(false);
      }
    },
    [agentName],
  );

  const callTool = useCallback(
    async (name: string, args: Record<string, unknown>) => {
      await sendRaw("tools/call", { name, arguments: args });
    },
    [sendRaw],
  );

  return {
    tools,
    toolsLoading,
    toolsError,
    lastResponse,
    sendingMcp,
    loadTools,
    sendRaw,
    callTool,
  };
}

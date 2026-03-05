/* Agent as returned by GET /api/agents */
export interface Agent {
  name: string;
  endpoint_url: string;
  app_name: string;
  description: string | null;
  capabilities: string | null;
  protocol_version: string | null;
}

/* Full A2A agent card JSON */
export interface AgentCard {
  name: string;
  description?: string;
  protocolVersion?: string;
  capabilities?: Record<string, unknown> | string[];
  skills?: AgentTool[];
  tools?: AgentTool[];
  url?: string;
  [key: string]: unknown;
}

export interface AgentTool {
  name?: string;
  id?: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
  [key: string]: unknown;
}

/* A2A message parts */
export interface TextPart {
  type: "text";
  text: string;
}

export interface ToolCallPart {
  type: "tool-call";
  toolCallId: string;
  toolName: string;
  args: Record<string, unknown>;
}

export interface ToolResultPart {
  type: "tool-result";
  toolCallId: string;
  result: unknown;
}

export type MessagePart = TextPart | ToolCallPart | ToolResultPart;

/* Chat message for the UI */
export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  parts: MessagePart[];
  timestamp: number;
}

/* Tool call entry for the inspector timeline */
export interface ToolCallEntry {
  id: string;
  toolName: string;
  args: Record<string, unknown>;
  result?: unknown;
  startTime: number;
  endTime?: number;
  status: "running" | "success" | "error";
}

/* JSON-RPC types for MCP */
export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: string;
  method: string;
  params: Record<string, unknown>;
}

export interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: string | null;
  result?: unknown;
  error?: { code: number; message: string };
}

/* Scan result from POST /api/scan */
export interface ScanResult {
  count: number;
  agents: string[];
  lineage_refreshed?: boolean;
}

/* ---------- Routing Observability ---------- */

export interface SqlQueryTrace {
  statement: string;
  parameters: Array<{ name: string; value: string }>;
  row_count: number;
  columns: Array<{ name: string; type: string }>;
  duration_ms: number;
  warehouse_id: string;
  error?: string;
  fallback_reason?: string;
}

export interface RoutingInfo {
  tool: string | null;
  sub_agent: string | null;
  timestamp: string;
  data_source: "live" | "demo_fallback" | "llm_direct";
  tables_accessed: string[];
  keywords_extracted: string[];
  routing_decision: {
    model: string;
    latency_ms: number;
    tool_selected: string | null;
    tool_args?: Record<string, unknown>;
    reason?: string;
  };
  sql_queries: SqlQueryTrace[];
  timing: {
    routing_ms: number;
    network_ms: number;
    sql_total_ms: number;
    subagent_ms: number;
    total_ms: number;
  };
  agent_endpoint?: string | null;
}

/* ---------- Trace / Event Inspection ---------- */

export interface TraceEvent {
  id: string;
  type: "a2a_request" | "a2a_response" | "mcp_tools_list" | "mcp_tools_call" | "error";
  label: string;
  timestamp: number;
  durationMs?: number;
  payload?: unknown;
}

export interface TraceTurn {
  id: string;
  userMessageId: string;
  agentMessageId?: string;
  startTime: number;
  endTime?: number;
  latencyMs?: number;
  events: TraceEvent[];
  protocol: "a2a" | "mcp_fallback";
  serverTiming?: {
    requestSentAt: string;
    responseReceivedAt: string;
    latencyMs: number;
    subEvents?: Array<{
      type: string;
      label: string;
      duration_ms: number;
      request?: unknown;
      response?: unknown;
    }>;
  };
  requestPayload?: unknown;
  responsePayload?: unknown;
  routing?: RoutingInfo;
}

/* ---------- Session Persistence ---------- */

export interface SessionMeta {
  id: string;
  name: string;
  createdAt: number;
  updatedAt: number;
  messageCount: number;
}

export interface SessionIndex {
  activeSessionId: string | null;
  sessions: SessionMeta[];
}

export interface ChatSession {
  id: string;
  name: string;
  messages: ChatMessage[];
  toolCalls: ToolCallEntry[];
  traces: TraceTurn[];
  contextId: string | null;
  createdAt: number;
  updatedAt: number;
}

/* ---------- Artifacts ---------- */

export type ArtifactType = "json" | "text" | "image" | "file" | "table";

export interface Artifact {
  id: string;
  type: ArtifactType;
  label: string;
  timestamp: number;
  sourceToolCallId?: string;
  data: unknown;
  preview?: string;
  url?: string;
  sizeBytes?: number;
}

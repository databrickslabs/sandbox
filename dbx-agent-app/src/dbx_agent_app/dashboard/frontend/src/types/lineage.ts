/* Lineage graph types — mirrors backend LineageNode/Edge/Graph dataclasses */

export type NodeType = "agent" | "tool" | "uc_function" | "table" | "model";

export type RelationshipType =
  | "uses_tool"
  | "calls_agent"
  | "reads_table"
  | "uses_function"
  | "writes_to"
  | "registered_as"
  | "observed_uses_tool"
  | "observed_calls_agent"
  | "observed_reads_table";

export interface LineageNode {
  id: string;
  node_type: NodeType;
  name: string;
  full_name: string;
  metadata: Record<string, unknown>;
}

export interface LineageEdge {
  source: string;
  target: string;
  relationship: RelationshipType;
}

export interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
  root_id: string | null;
}

export interface ConnectedTable {
  full_name: string;
  schema: string;
  relationship: string;
}

export type ResourceType =
  | "uc_securable"
  | "sql_warehouse"
  | "job"
  | "secret"
  | "serving_endpoint"
  | "database"
  | "genie_space";

export interface DeclaredResource {
  name: string;
  type: ResourceType;
  securable_type?: string;
  securable_full_name?: string;
  permission?: string;
  id?: string;
  [key: string]: unknown;
}

export interface GovernanceStatus {
  app_running: boolean;
  app_name: string | null;
  declared_resources: DeclaredResource[];
  connected_tables: ConnectedTable[];
  connected_table_count: number;
}

export interface InvocationRecord {
  timestamp: number;
  success: boolean;
  latency_ms: number;
  source: string;
  error: string | null;
}

export interface AgentAnalytics {
  total: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_latency_ms: number;
  recent: InvocationRecord[];
}

export interface EvalResult {
  response: string;
  output: Record<string, unknown>[];
}

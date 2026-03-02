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
  | "observed_calls_agent";

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

export interface UCRegistrationResult {
  registered: Array<{ full_name: string; name: string }>;
  failed: Array<{ name: string; error: string }>;
  total: number;
  error?: string;
}

export interface GovernanceStatus {
  registered: boolean;
  full_name: string | null;
  catalog: string | null;
  schema: string | null;
  tags: Record<string, string>;
  endpoint_url: string | null;
  capabilities?: string[] | null;
  description?: string | null;
  connected_tables?: ConnectedTable[];
  connected_table_count?: number;
}

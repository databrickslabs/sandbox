import type { LineageNode, LineageEdge, NodeType, RelationshipType } from "../../types/lineage";

const NODE_COLORS: Record<NodeType, string> = {
  agent: "#3b82f6",
  tool: "#eab308",
  uc_function: "#22c55e",
  table: "#a78bfa",
  model: "#ef4444",
};

const NODE_LABELS: Record<NodeType, string> = {
  agent: "Agent",
  tool: "Tool",
  uc_function: "UC Function",
  table: "Table",
  model: "UC Model",
};

const EDGE_COLORS: Record<RelationshipType, string> = {
  uses_tool: "#eab308",
  calls_agent: "#3b82f6",
  reads_table: "#a78bfa",
  uses_function: "#22c55e",
  writes_to: "#ef4444",
  registered_as: "#ef4444",
  observed_uses_tool: "#06b6d4",
  observed_calls_agent: "#06b6d4",
};

const EDGE_LABELS: Record<RelationshipType, string> = {
  uses_tool: "Uses Tool",
  calls_agent: "Calls Agent",
  reads_table: "Reads Table",
  uses_function: "Uses Function",
  writes_to: "Writes To",
  registered_as: "Registered As",
  observed_uses_tool: "Observed (runtime)",
  observed_calls_agent: "Observed (runtime)",
};

const EDGE_DASHED: Record<RelationshipType, boolean> = {
  uses_tool: true,
  calls_agent: false,
  reads_table: false,
  uses_function: true,
  writes_to: false,
  registered_as: true,
  observed_uses_tool: true,
  observed_calls_agent: true,
};

interface Props {
  nodes: LineageNode[];
  edges: LineageEdge[];
}

export function LineageLegend({ nodes, edges }: Props) {
  // Only show types that appear in the graph
  const nodeTypes = [...new Set(nodes.map((n) => n.node_type))];
  const edgeTypes = [...new Set(edges.map((e) => e.relationship))];

  if (nodeTypes.length === 0) return null;

  return (
    <div className="lineage-legend">
      <div className="legend-section">
        {nodeTypes.map((t) => (
          <span key={t} className="legend-item">
            <span
              className="legend-dot"
              style={{ background: NODE_COLORS[t] }}
            />
            {NODE_LABELS[t] ?? t}
          </span>
        ))}
      </div>
      {edgeTypes.length > 0 && (
        <div className="legend-section">
          {edgeTypes.map((r) => (
            <span key={r} className="legend-item">
              <svg width={24} height={10} style={{ verticalAlign: "middle" }}>
                <line
                  x1={0}
                  y1={5}
                  x2={24}
                  y2={5}
                  stroke={EDGE_COLORS[r] ?? "#6b7280"}
                  strokeWidth={2}
                  strokeDasharray={EDGE_DASHED[r] ? "4 3" : undefined}
                />
              </svg>
              {EDGE_LABELS[r] ?? r}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

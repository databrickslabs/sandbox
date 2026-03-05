import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LineageGraph as LineageGraphData, LineageNode, NodeType, RelationshipType } from "../../types/lineage";
import { LineageLegend } from "./LineageLegend";

/* Layout constants */
const NODE_W = 180;
const NODE_H = 48;
const LAYER_GAP = 260;
const NODE_GAP = 72;
const PADDING = 60;

/* Color maps */
const NODE_COLORS: Record<NodeType, string> = {
  agent: "#3b82f6",
  tool: "#eab308",
  uc_function: "#22c55e",
  table: "#a78bfa",
  model: "#ef4444",
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
  observed_reads_table: "#06b6d4",
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
  observed_reads_table: true,
};

interface LayoutNode {
  node: LineageNode;
  x: number;
  y: number;
}

interface Props {
  graph: LineageGraphData;
  onNodeClick?: (nodeId: string) => void;
}

/**
 * Assign depths via BFS from root (or leftmost agents if no root).
 * Returns a map of nodeId → depth.
 */
function assignDepths(graph: LineageGraphData): Map<string, number> {
  const depths = new Map<string, number>();
  const nodeById = new Map(graph.nodes.map((n) => [n.id, n]));

  // Adjacency list (directed)
  const adj = new Map<string, string[]>();
  for (const e of graph.edges) {
    if (!adj.has(e.source)) adj.set(e.source, []);
    adj.get(e.source)!.push(e.target);
  }

  // Depth priority: agent=-1 if connected from root, tools=1, uc_function=2, table=2, model=1
  const typeDepthHint: Record<NodeType, number> = {
    agent: -1,
    tool: 1,
    uc_function: 2,
    table: 2,
    model: 1,
  };

  // Start BFS from root or all agents
  const queue: Array<{ id: string; depth: number }> = [];

  if (graph.root_id && nodeById.has(graph.root_id)) {
    queue.push({ id: graph.root_id, depth: 0 });
    depths.set(graph.root_id, 0);
  } else {
    // No root — start from all agents at depth 0
    for (const n of graph.nodes) {
      if (n.node_type === "agent") {
        queue.push({ id: n.id, depth: 0 });
        depths.set(n.id, 0);
      }
    }
  }

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!;
    const neighbors = adj.get(id) || [];
    for (const nid of neighbors) {
      if (!depths.has(nid)) {
        const targetNode = nodeById.get(nid);
        const hint = targetNode ? typeDepthHint[targetNode.node_type] : 1;
        // calls_agent goes to -1 from root, everything else goes right
        const isAgentCall = targetNode?.node_type === "agent";
        const nextDepth = isAgentCall ? depth - 1 : depth + Math.abs(hint);
        depths.set(nid, nextDepth);
        queue.push({ id: nid, depth: nextDepth });
      }
    }
  }

  // Assign unvisited nodes at depth +3
  for (const n of graph.nodes) {
    if (!depths.has(n.id)) {
      depths.set(n.id, 3);
    }
  }

  return depths;
}

function computeLayout(graph: LineageGraphData): LayoutNode[] {
  if (graph.nodes.length === 0) return [];

  const depths = assignDepths(graph);

  // Group nodes by depth
  const layers = new Map<number, LineageNode[]>();
  for (const n of graph.nodes) {
    const d = depths.get(n.id) ?? 0;
    if (!layers.has(d)) layers.set(d, []);
    layers.get(d)!.push(n);
  }

  // Sort depth keys
  const sortedDepths = [...layers.keys()].sort((a, b) => a - b);
  const minDepth = sortedDepths[0] ?? 0;

  const result: LayoutNode[] = [];

  for (const depth of sortedDepths) {
    const nodesInLayer = layers.get(depth)!;
    const col = depth - minDepth;
    const x = PADDING + col * LAYER_GAP;
    const totalHeight = nodesInLayer.length * NODE_H + (nodesInLayer.length - 1) * (NODE_GAP - NODE_H);
    const startY = PADDING + (300 - totalHeight / 2); // center vertically around 300px

    nodesInLayer.forEach((node, i) => {
      result.push({
        node,
        x,
        y: startY + i * NODE_GAP,
      });
    });
  }

  return result;
}

export function LineageGraphView({ graph, onNodeClick }: Props) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const navigate = useNavigate();

  const layout = useMemo(() => computeLayout(graph), [graph]);
  const posMap = useMemo(
    () => new Map(layout.map((l) => [l.node.id, { x: l.x, y: l.y }])),
    [layout],
  );

  if (graph.nodes.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "2rem" }}>
        <p>No lineage data available</p>
      </div>
    );
  }

  // Compute viewBox
  const maxX = Math.max(...layout.map((l) => l.x)) + NODE_W + PADDING;
  const maxY = Math.max(...layout.map((l) => l.y)) + NODE_H + PADDING;
  const viewBox = `0 0 ${maxX} ${maxY}`;

  const handleNodeClick = (nodeId: string, nodeType: NodeType) => {
    if (onNodeClick) {
      onNodeClick(nodeId);
      return;
    }
    if (nodeType === "agent") {
      const name = nodeId.replace("agent:", "");
      navigate(`/agent/${encodeURIComponent(name)}`);
    }
  };

  return (
    <div>
      <svg
        viewBox={viewBox}
        width="100%"
        style={{ minHeight: 300, maxHeight: 600, background: "#111827", borderRadius: 8 }}
      >
        {/* Arrow markers */}
        <defs>
          {Object.entries(EDGE_COLORS).map(([rel, color]) => (
            <marker
              key={rel}
              id={`arrow-${rel}`}
              viewBox="0 0 10 8"
              refX="10"
              refY="4"
              markerWidth="8"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,4 L0,8 Z" fill={color} />
            </marker>
          ))}
        </defs>

        {/* Edges */}
        {graph.edges.map((edge, i) => {
          const src = posMap.get(edge.source);
          const tgt = posMap.get(edge.target);
          if (!src || !tgt) return null;

          const x1 = src.x + NODE_W;
          const y1 = src.y + NODE_H / 2;
          const x2 = tgt.x;
          const y2 = tgt.y + NODE_H / 2;

          // Handle left-going edges (when target is to the left)
          const goingLeft = x2 < x1;
          const sx = goingLeft ? src.x : x1;
          const tx = goingLeft ? tgt.x + NODE_W : x2;
          const sy = y1;
          const ty = y2;

          const cpOffset = Math.abs(tx - sx) * 0.4;
          const cp1x = goingLeft ? sx - cpOffset : sx + cpOffset;
          const cp2x = goingLeft ? tx + cpOffset : tx - cpOffset;

          const color = EDGE_COLORS[edge.relationship] ?? "#6b7280";
          const dashed = EDGE_DASHED[edge.relationship];

          const isObserved = edge.relationship.startsWith("observed_");
          const edgeTitle = isObserved
            ? `${edge.relationship.replace(/_/g, " ")} (observed at runtime)`
            : edge.relationship.replace(/_/g, " ");

          return (
            <path
              key={i}
              d={`M${sx},${sy} C${cp1x},${sy} ${cp2x},${ty} ${tx},${ty}`}
              fill="none"
              stroke={color}
              strokeWidth={isObserved ? 2 : 1.5}
              strokeDasharray={dashed ? "6 4" : undefined}
              markerEnd={`url(#arrow-${edge.relationship})`}
              opacity={isObserved ? 0.9 : 0.7}
            >
              <title>{edgeTitle}</title>
            </path>
          );
        })}

        {/* Nodes */}
        {layout.map(({ node, x, y }) => {
          const color = NODE_COLORS[node.node_type] ?? "#6b7280";
          const isHovered = hoveredNode === node.id;
          const isRoot = node.id === graph.root_id;

          return (
            <g
              key={node.id}
              transform={`translate(${x}, ${y})`}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() => handleNodeClick(node.id, node.node_type)}
              style={{ cursor: node.node_type === "agent" ? "pointer" : "default" }}
            >
              {/* Background rect */}
              <rect
                width={NODE_W}
                height={NODE_H}
                rx={6}
                fill={isHovered ? "#1f2937" : "#111827"}
                stroke={isRoot ? color : "#374151"}
                strokeWidth={isRoot ? 2 : 1}
              />
              {/* Left color bar */}
              <rect
                width={4}
                height={NODE_H}
                rx={2}
                fill={color}
              />
              {/* Type label */}
              <text
                x={14}
                y={16}
                fontSize={10}
                fill={color}
                fontWeight={600}
                fontFamily="sans-serif"
              >
                {node.node_type.toUpperCase().replace("_", " ")}
              </text>
              {/* Name */}
              <text
                x={14}
                y={34}
                fontSize={12}
                fill="#f3f4f6"
                fontFamily="sans-serif"
              >
                {node.name.length > 20 ? node.name.slice(0, 18) + "..." : node.name}
              </text>

              {/* Tooltip on hover */}
              {isHovered && (
                <g>
                  <rect
                    x={0}
                    y={NODE_H + 4}
                    width={Math.max(NODE_W, node.full_name.length * 7 + 16)}
                    height={28}
                    rx={4}
                    fill="#1f2937"
                    stroke="#374151"
                  />
                  <text
                    x={8}
                    y={NODE_H + 22}
                    fontSize={10}
                    fill="#9ca3af"
                    fontFamily="monospace"
                  >
                    {node.full_name}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
      <LineageLegend nodes={graph.nodes} edges={graph.edges} />
    </div>
  );
}

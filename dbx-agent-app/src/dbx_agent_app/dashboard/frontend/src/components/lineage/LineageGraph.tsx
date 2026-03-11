import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LineageGraph as LineageGraphData, LineageNode, NodeType, RelationshipType } from "../../types/lineage";
import { LineageLegend } from "./LineageLegend";

/* Layout constants — vertical (top-down) orientation */
const NODE_W = 140;
const NODE_H = 44;
const COL_ROW_H = 18;
const LAYER_GAP = 100;
const NODE_GAP = 160;
const PADDING = 40;

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
  h: number;
}

interface Props {
  graph: LineageGraphData;
  onNodeClick?: (nodeId: string) => void;
}

type ColumnInfo = Array<{ name: string; type: string }>;

function getNodeColumns(node: LineageNode): ColumnInfo {
  const cols = node.metadata?.columns;
  if (!Array.isArray(cols)) return [];
  return cols as ColumnInfo;
}

function getNodeHeight(node: LineageNode, expanded: Set<string>): number {
  if (node.node_type !== "table" || !expanded.has(node.id)) return NODE_H;
  const cols = getNodeColumns(node);
  if (cols.length === 0) return NODE_H;
  return NODE_H + cols.length * COL_ROW_H + 8;
}

/**
 * Assign depths via BFS from root (or topmost agents if no root).
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

  const typeDepthHint: Record<NodeType, number> = {
    agent: -1,
    tool: 1,
    uc_function: 2,
    table: 2,
    model: 1,
  };

  const queue: Array<{ id: string; depth: number }> = [];

  if (graph.root_id && nodeById.has(graph.root_id)) {
    queue.push({ id: graph.root_id, depth: 0 });
    depths.set(graph.root_id, 0);
  } else {
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
        const isAgentCall = targetNode?.node_type === "agent";
        const nextDepth = isAgentCall ? depth - 1 : depth + Math.abs(hint);
        depths.set(nid, nextDepth);
        queue.push({ id: nid, depth: nextDepth });
      }
    }
  }

  for (const n of graph.nodes) {
    if (!depths.has(n.id)) {
      depths.set(n.id, 3);
    }
  }

  return depths;
}

function computeLayout(
  graph: LineageGraphData,
  expanded: Set<string>,
): LayoutNode[] {
  if (graph.nodes.length === 0) return [];

  const depths = assignDepths(graph);

  // Group nodes by depth
  const layers = new Map<number, LineageNode[]>();
  for (const n of graph.nodes) {
    const d = depths.get(n.id) ?? 0;
    if (!layers.has(d)) layers.set(d, []);
    layers.get(d)!.push(n);
  }

  const sortedDepths = [...layers.keys()].sort((a, b) => a - b);

  const result: LayoutNode[] = [];

  // Find max layer width to center all layers consistently
  let maxLayerWidth = 0;
  for (const depth of sortedDepths) {
    const count = layers.get(depth)!.length;
    const w = count * NODE_W + (count - 1) * (NODE_GAP - NODE_W);
    if (w > maxLayerWidth) maxLayerWidth = w;
  }

  // Accumulate y position per row, accounting for tallest node in previous rows
  let currentY = PADDING;
  for (const depth of sortedDepths) {
    const nodesInLayer = layers.get(depth)!;
    const totalWidth =
      nodesInLayer.length * NODE_W +
      (nodesInLayer.length - 1) * (NODE_GAP - NODE_W);
    const startX = PADDING + (maxLayerWidth - totalWidth) / 2;

    let maxH = NODE_H;
    nodesInLayer.forEach((node, i) => {
      const h = getNodeHeight(node, expanded);
      if (h > maxH) maxH = h;
      result.push({
        node,
        x: startX + i * NODE_GAP,
        y: currentY,
        h,
      });
    });

    currentY += maxH + LAYER_GAP - NODE_H;
  }

  return result;
}

export function LineageGraphView({ graph, onNodeClick }: Props) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const navigate = useNavigate();

  const layout = useMemo(
    () => computeLayout(graph, expandedNodes),
    [graph, expandedNodes],
  );
  const posMap = useMemo(
    () =>
      new Map(layout.map((l) => [l.node.id, { x: l.x, y: l.y, h: l.h }])),
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
  const maxY = Math.max(...layout.map((l) => l.y + l.h)) + PADDING;
  const viewBox = `0 0 ${maxX} ${maxY}`;

  const toggleExpand = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const handleNodeClick = (nodeId: string, nodeType: NodeType, hasColumns: boolean) => {
    if (nodeType === "table" && hasColumns) {
      toggleExpand(nodeId);
      return;
    }
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
        preserveAspectRatio="xMidYMin meet"
        style={{ background: "#111827", borderRadius: 8 }}
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

          // Vertical layout: edges go from bottom of source to top of target
          const sx = src.x + NODE_W / 2;
          const sy = src.y + src.h;
          const tx = tgt.x + NODE_W / 2;
          const ty = tgt.y;

          // Handle upward edges (when target is above source)
          const goingUp = ty < sy;
          const startY = goingUp ? src.y : sy;
          const endY = goingUp ? tgt.y + tgt.h : ty;

          const cpOffset = Math.abs(endY - startY) * 0.4;
          const cp1y = goingUp ? startY - cpOffset : startY + cpOffset;
          const cp2y = goingUp ? endY + cpOffset : endY - cpOffset;

          const color = EDGE_COLORS[edge.relationship] ?? "#6b7280";
          const dashed = EDGE_DASHED[edge.relationship];

          const isObserved = edge.relationship.startsWith("observed_");
          const edgeTitle = isObserved
            ? `${edge.relationship.replace(/_/g, " ")} (observed at runtime)`
            : edge.relationship.replace(/_/g, " ");

          return (
            <path
              key={i}
              d={`M${sx},${startY} C${sx},${cp1y} ${tx},${cp2y} ${tx},${endY}`}
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
        {layout.map(({ node, x, y, h }) => {
          const color = NODE_COLORS[node.node_type] ?? "#6b7280";
          const isHovered = hoveredNode === node.id;
          const isRoot = node.id === graph.root_id;
          const columns = getNodeColumns(node);
          const hasColumns = columns.length > 0;
          const isExpanded = expandedNodes.has(node.id);

          return (
            <g
              key={node.id}
              transform={`translate(${x}, ${y})`}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() => handleNodeClick(node.id, node.node_type, hasColumns)}
              style={{
                cursor:
                  hasColumns || node.node_type === "agent"
                    ? "pointer"
                    : "default",
              }}
            >
              {/* Background rect */}
              <rect
                width={NODE_W}
                height={h}
                rx={6}
                fill={isHovered ? "#1f2937" : "#111827"}
                stroke={isRoot ? color : "#374151"}
                strokeWidth={isRoot ? 2 : 1}
              />
              {/* Left color bar */}
              <rect width={4} height={h} rx={2} fill={color} />
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
                {node.name.length > 16
                  ? node.name.slice(0, 14) + "..."
                  : node.name}
              </text>

              {/* Expand chevron for tables with columns */}
              {hasColumns && (
                <text
                  x={NODE_W - 16}
                  y={28}
                  fontSize={12}
                  fill="#6b7280"
                  fontFamily="sans-serif"
                  textAnchor="middle"
                >
                  {isExpanded ? "▾" : "▸"}
                </text>
              )}

              {/* Column rows when expanded */}
              {isExpanded &&
                columns.map((col, ci) => {
                  const cy = NODE_H + ci * COL_ROW_H + 4;
                  return (
                    <g key={col.name}>
                      {/* Separator line above first column */}
                      {ci === 0 && (
                        <line
                          x1={8}
                          y1={NODE_H - 1}
                          x2={NODE_W - 8}
                          y2={NODE_H - 1}
                          stroke="#374151"
                          strokeWidth={0.5}
                        />
                      )}
                      <text
                        x={14}
                        y={cy + 12}
                        fontSize={9}
                        fill="#d1d5db"
                        fontFamily="monospace"
                      >
                        {col.name.length > 14
                          ? col.name.slice(0, 12) + "…"
                          : col.name}
                      </text>
                      <text
                        x={NODE_W - 8}
                        y={cy + 12}
                        fontSize={8}
                        fill="#6b7280"
                        fontFamily="monospace"
                        textAnchor="end"
                      >
                        {col.type}
                      </text>
                    </g>
                  );
                })}

              {/* Tooltip on hover (only when collapsed) */}
              {isHovered && !isExpanded && (
                <g>
                  <rect
                    x={0}
                    y={NODE_H + 4}
                    width={Math.max(NODE_W, node.full_name.length * 7 + 16)}
                    height={hasColumns ? 44 : 28}
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
                  {hasColumns && (
                    <text
                      x={8}
                      y={NODE_H + 38}
                      fontSize={9}
                      fill="#6b7280"
                      fontFamily="sans-serif"
                    >
                      {columns.length} columns — click to expand
                    </text>
                  )}
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

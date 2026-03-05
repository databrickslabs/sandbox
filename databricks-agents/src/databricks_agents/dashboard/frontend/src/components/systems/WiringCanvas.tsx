/**
 * WiringCanvas — dagre auto-layout with custom AgentNode + WiringEdgeComponent.
 * Adapted from Tables-to-Genies graph-explorer dagre pattern.
 *
 * Features:
 *  - Dagre LR auto-layout with fitView on re-layout
 *  - Custom AgentNode + WiringEdgeComponent
 *  - Hover intent: dim unconnected nodes (via context, not node rebuild)
 *  - Dual coloring mode: "role" (supervisor/worker/tool) vs "capability"
 *  - selectedNodeId synced to ReactFlow selection state
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type Connection,
  type NodeChange,
  type EdgeChange,
  Position,
  BackgroundVariant,
  applyNodeChanges,
  applyEdgeChanges,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import type { WiringEdge } from "../../types/systems";
import { AgentNode, type AgentNodeData } from "./AgentNode";
import { WiringEdgeComponent } from "./WiringEdgeComponent";
import { WiringCanvasContext, type WiringCanvasContextValue } from "./WiringCanvasContext";

// Register custom types — module-level for stable references
const nodeTypes = { agentNode: AgentNode };
const edgeTypes = { wiring: WiringEdgeComponent };

// Dagre layout constants
const NODE_WIDTH = 220;
const NODE_HEIGHT = 90;

export type ColorMode = "role" | "capability";

interface AgentMeta {
  description?: string;
  capabilities?: string;
  role?: string;
}

interface Props {
  agents: string[];
  edges: WiringEdge[];
  onEdgesChange: (edges: WiringEdge[]) => void;
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  onSelectNode: (name: string | null) => void;
  onSelectEdge: (edgeId: string | null) => void;
  /** Optional agent metadata for richer node display */
  agentMeta?: Record<string, AgentMeta>;
  /** Deploy status per agent name */
  deployStatus?: Record<string, string>;
  /** Read-only mode (no edge drawing / deletion) */
  readOnly?: boolean;
  /** Show MiniMap */
  showMiniMap?: boolean;
  /** Color mode: "role" (default) or "capability" */
  colorMode?: ColorMode;
  /** Show color mode toggle */
  showColorToggle?: boolean;
}

/**
 * Apply dagre LR layout to nodes and edges, returning positioned nodes.
 */
function layoutWithDagre(
  agents: string[],
  wiringEdges: WiringEdge[],
): Record<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 80, ranksep: 200 });

  for (const name of agents) {
    g.setNode(name, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of wiringEdges) {
    g.setEdge(edge.source_agent, edge.target_agent);
  }

  dagre.layout(g);

  const positions: Record<string, { x: number; y: number }> = {};
  for (const name of agents) {
    const node = g.node(name);
    if (node) {
      positions[name] = {
        x: node.x - NODE_WIDTH / 2,
        y: node.y - NODE_HEIGHT / 2,
      };
    }
  }
  return positions;
}

// Stable empty defaults — prevents new object references on every render
const EMPTY_META: Record<string, AgentMeta> = {};
const EMPTY_STATUS: Record<string, string> = {};

/** Inner component — must be inside ReactFlowProvider to use useReactFlow */
function WiringCanvasInner({
  agents,
  edges: wiringEdges,
  onEdgesChange: onWiringEdgesChange,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  agentMeta = EMPTY_META,
  deployStatus = EMPTY_STATUS,
  readOnly = false,
  showMiniMap = false,
  colorMode: colorModeProp = "role",
  showColorToggle = false,
}: Props) {
  const { fitView } = useReactFlow();
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [colorMode, setColorMode] = useState<ColorMode>(colorModeProp);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout>>(null);
  const prevLayoutKey = useRef("");

  // Connected nodes for hover-dim — used by AgentNode via context
  const connectedToHovered = useMemo(() => {
    if (!hoveredNode) return new Set<string>();
    const connected = new Set<string>([hoveredNode]);
    for (const edge of wiringEdges) {
      if (edge.source_agent === hoveredNode) connected.add(edge.target_agent);
      if (edge.target_agent === hoveredNode) connected.add(edge.source_agent);
    }
    return connected;
  }, [hoveredNode, wiringEdges]);

  // Context value — AgentNode reads visual state from here instead of node data,
  // so node objects don't need rebuilding on hover/selection/colorMode changes.
  const ctxValue: WiringCanvasContextValue = useMemo(
    () => ({
      hoveredNode,
      connectedToHovered,
      colorMode,
      agentMeta,
      deployStatus,
    }),
    [hoveredNode, connectedToHovered, colorMode, agentMeta, deployStatus],
  );

  // Dagre positions — recompute when agents/edges change
  const dagrePositions = useMemo(
    () => layoutWithDagre(agents, wiringEdges),
    [agents, wiringEdges],
  );

  // fitView when layout changes (new agents/edges added)
  const layoutKey = agents.join(",") + "|" + wiringEdges.map((e) => `${e.source_agent}->${e.target_agent}`).join(",");
  useEffect(() => {
    if (prevLayoutKey.current && prevLayoutKey.current !== layoutKey) {
      const timer = setTimeout(() => fitView({ padding: 0.3, duration: 300 }), 50);
      return () => clearTimeout(timer);
    }
    prevLayoutKey.current = layoutKey;
  }, [layoutKey, fitView]);

  // ─── Node state ──────────────────────────────────────────────────────
  // Managed via useState. Only rebuilt when topology changes (agents + edges).
  // Visual state (dimming, colors) is provided via context — NOT in node data.
  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  const prevTopologyKeyRef = useRef("");

  useEffect(() => {
    const currentTopologyKey =
      agents.join(",") +
      "|" +
      wiringEdges.map((e) => `${e.source_agent}->${e.target_agent}`).join(",");
    const topologyChanged = prevTopologyKeyRef.current !== currentTopologyKey;
    prevTopologyKeyRef.current = currentTopologyKey;

    setFlowNodes((prev) =>
      agents.map((name) => {
        const existing = prev.find((n) => n.id === name);
        const pos =
          !existing || topologyChanged
            ? (dagrePositions[name] ?? { x: 0, y: 0 })
            : existing.position;

        // Minimal data — AgentNode reads visual state from context
        const nodeData: AgentNodeData = { label: name };

        return {
          id: name,
          type: "agentNode" as const,
          position: pos,
          data: nodeData,
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          // Preserve ReactFlow measurements to avoid re-measure loops
          ...(existing?.measured ? { measured: existing.measured } : {}),
        };
      }),
    );
  }, [agents, wiringEdges, dagrePositions]);

  // Sync selection from parent prop — lightweight update, no node rebuild
  useEffect(() => {
    setFlowNodes((prev) => {
      let changed = false;
      const next = prev.map((n) => {
        const shouldSelect = selectedNodeId === n.id;
        if (n.selected !== shouldSelect) {
          changed = true;
          return { ...n, selected: shouldSelect };
        }
        return n;
      });
      return changed ? next : prev;
    });
  }, [selectedNodeId]);

  // ─── Edge state ──────────────────────────────────────────────────────
  const flowEdges: Edge[] = useMemo(() => {
    return wiringEdges.map((edge) => {
      const edgeId = `${edge.source_agent}->${edge.target_agent}`;
      return {
        id: edgeId,
        source: edge.source_agent,
        target: edge.target_agent,
        type: "wiring",
        selected: selectedEdgeId === edgeId,
        data: {
          envVar: edge.env_var,
          isDeploying: deployStatus[edge.target_agent] === "deploying",
        },
      };
    });
  }, [wiringEdges, selectedEdgeId, deployStatus]);

  // ─── Change handlers ─────────────────────────────────────────────────
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setFlowNodes((nds) => applyNodeChanges(changes, nds));
    },
    [],
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (readOnly) return;
      const updated = applyEdgeChanges(changes, flowEdges);
      const newWiringEdges: WiringEdge[] = updated.map((fe) => {
        const existing = wiringEdges.find(
          (we) => `${we.source_agent}->${we.target_agent}` === fe.id,
        );
        return {
          source_agent: fe.source,
          target_agent: fe.target,
          env_var: existing?.env_var ?? "",
        };
      });
      onWiringEdgesChange(newWiringEdges);
    },
    [flowEdges, wiringEdges, onWiringEdgesChange, readOnly],
  );

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (readOnly) return;
      if (!connection.source || !connection.target) return;
      if (connection.source === connection.target) return;
      const exists = wiringEdges.some(
        (e) =>
          e.source_agent === connection.source &&
          e.target_agent === connection.target,
      );
      if (exists) return;

      const newEdge: WiringEdge = {
        source_agent: connection.source,
        target_agent: connection.target,
        env_var: `${connection.source.toUpperCase().replace(/-/g, "_")}_URL`,
      };
      onWiringEdgesChange([...wiringEdges, newEdge]);
      onSelectEdge(`${newEdge.source_agent}->${newEdge.target_agent}`);
    },
    [wiringEdges, onWiringEdgesChange, onSelectEdge, readOnly],
  );

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onSelectNode(node.id);
      onSelectEdge(null);
    },
    [onSelectNode, onSelectEdge],
  );

  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      onSelectEdge(edge.id);
      onSelectNode(null);
    },
    [onSelectEdge, onSelectNode],
  );

  const handlePaneClick = useCallback(() => {
    onSelectNode(null);
    onSelectEdge(null);
  }, [onSelectNode, onSelectEdge]);

  // Hover intent — debounce to avoid flicker
  const handleNodeMouseEnter = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = setTimeout(() => setHoveredNode(node.id), 150);
    },
    [],
  );

  const handleNodeMouseLeave = useCallback(() => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setHoveredNode(null), 100);
  }, []);

  // SVG defs for arrow marker
  const svgDefs = (
    <svg style={{ position: "absolute", width: 0, height: 0 }}>
      <defs>
        <marker
          id="sb-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerUnits="strokeWidth"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--muted)" />
        </marker>
      </defs>
    </svg>
  );

  return (
    <div className="sb-canvas">
      {svgDefs}

      {/* Color mode toggle */}
      {showColorToggle && agents.length > 0 && (
        <div className="sb-color-toggle">
          <button
            className={`sb-color-btn${colorMode === "role" ? " sb-color-btn--active" : ""}`}
            onClick={() => setColorMode("role")}
          >
            Role
          </button>
          <button
            className={`sb-color-btn${colorMode === "capability" ? " sb-color-btn--active" : ""}`}
            onClick={() => setColorMode("capability")}
          >
            Capability
          </button>
        </div>
      )}

      {agents.length === 0 ? (
        <div className="sb-muted-center" style={{ height: "100%" }}>
          <p>Add agents from the palette to start building a system.</p>
          <p>Then draw connections between them to define wiring.</p>
        </div>
      ) : (
        <WiringCanvasContext.Provider value={ctxValue}>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={readOnly ? undefined : handleConnect}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            onPaneClick={handlePaneClick}
            onNodeMouseEnter={handleNodeMouseEnter}
            onNodeMouseLeave={handleNodeMouseLeave}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.3}
            maxZoom={2}
            connectionDragThreshold={0}
            attributionPosition="bottom-left"
            deleteKeyCode={readOnly ? null : "Backspace"}
            colorMode="dark"
            nodesConnectable={!readOnly}
          >
            <Controls />
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
            {showMiniMap && (
              <MiniMap
                nodeColor={() => "var(--accent)"}
                maskColor="rgba(0,0,0,0.7)"
                style={{ background: "var(--surface)" }}
              />
            )}
          </ReactFlow>
        </WiringCanvasContext.Provider>
      )}
    </div>
  );
}

/** Wrapper — provides ReactFlowProvider so useReactFlow() works inside */
export function WiringCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <WiringCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

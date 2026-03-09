/**
 * Step 2: Wire Connections — full-width canvas with dagre + edge drawing.
 * Step is completed when >= 1 edge is drawn.
 */
import { useState } from "react";
import { WiringCanvas } from "../WiringCanvas";
import type { WiringEdge } from "../../../types/systems";

interface Props {
  agents: string[];
  edges: WiringEdge[];
  onEdgesChange: (edges: WiringEdge[]) => void;
  onEdgeUpdate: (edgeId: string, envVar: string) => void;
  agentMeta?: Record<string, { description?: string; capabilities?: string }>;
}

export default function WireStep({
  agents,
  edges,
  onEdgesChange,
  onEdgeUpdate,
  agentMeta = {},
}: Props) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);

  const selectedEdgeData = selectedEdge
    ? edges.find(
        (e) => `${e.source_agent}->${e.target_agent}` === selectedEdge,
      )
    : null;

  return (
    <div className="sb-step-content sb-step-wire">
      <div className="sb-step-wire-canvas">
        <div className="sb-step-header">
          <h3>Wire Connections</h3>
          <span className="sb-step-hint">
            {edges.length === 0
              ? "Draw connections between agents by dragging from one handle to another"
              : `${edges.length} connection${edges.length !== 1 ? "s" : ""} defined`}
          </span>
        </div>
        <WiringCanvas
          agents={agents}
          edges={edges}
          onEdgesChange={onEdgesChange}
          selectedNodeId={selectedNode}
          selectedEdgeId={selectedEdge}
          onSelectNode={setSelectedNode}
          onSelectEdge={setSelectedEdge}
          agentMeta={agentMeta}
          showMiniMap
          showColorToggle
        />
      </div>

      {/* Floating edge editor panel */}
      {selectedEdgeData && (
        <div className="sb-step-wire-panel">
          <div className="sb-section-title">
            {selectedEdgeData.source_agent} &rarr;{" "}
            {selectedEdgeData.target_agent}
          </div>
          <label className="sb-label">
            Env Var (injected into {selectedEdgeData.target_agent})
          </label>
          <input
            type="text"
            className="sb-input"
            value={selectedEdgeData.env_var}
            onChange={(e) => onEdgeUpdate(selectedEdge!, e.target.value)}
            placeholder="e.g. RESEARCH_AGENT_URL"
          />
          <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: 4 }}>
            Set to the URL of {selectedEdgeData.source_agent} on deploy.
          </div>
        </div>
      )}
    </div>
  );
}

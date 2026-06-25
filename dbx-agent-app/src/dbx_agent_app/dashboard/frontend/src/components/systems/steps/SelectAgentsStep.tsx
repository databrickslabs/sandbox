/**
 * Step 1: Select Agents — palette on left, mini canvas preview on right.
 * Step is completed when >= 2 agents are selected.
 */
import { AgentPalette } from "../AgentPalette";
import { WiringCanvas } from "../WiringCanvas";
import type { WiringEdge } from "../../../types/systems";

interface Props {
  agents: string[];
  edges: WiringEdge[];
  onAddAgent: (name: string) => void;
  onRemoveAgent: (name: string) => void;
}

export default function SelectAgentsStep({
  agents,
  edges,
  onAddAgent,
  onRemoveAgent,
}: Props) {
  return (
    <div className="sb-step-content sb-step-select">
      <div className="sb-step-select-palette">
        <AgentPalette
          onAddAgent={onAddAgent}
          addedAgents={new Set(agents)}
        />
      </div>
      <div className="sb-step-select-preview">
        <div className="sb-step-header">
          <h3>Preview</h3>
          <span className="sb-step-hint">
            {agents.length < 2
              ? `Select at least ${2 - agents.length} more agent${agents.length === 0 ? "s" : ""}`
              : `${agents.length} agents selected — proceed to wiring`}
          </span>
        </div>
        <div className="sb-step-canvas-mini">
          <WiringCanvas
            agents={agents}
            edges={edges}
            onEdgesChange={() => {}}
            selectedNodeId={null}
            selectedEdgeId={null}
            onSelectNode={(name) => {
              if (name) onRemoveAgent(name);
            }}
            onSelectEdge={() => {}}
            readOnly
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Step 3: Configure — split layout with canvas (60%) + config panel (40%).
 * Validates: all edges have env vars set.
 */
import { useState } from "react";
import { WiringCanvas } from "../WiringCanvas";
import type { WiringEdge, SystemDefinition } from "../../../types/systems";

interface Props {
  system: SystemDefinition;
  agents: string[];
  edges: WiringEdge[];
  onEdgeUpdate: (edgeId: string, envVar: string) => void;
  onSystemMetaChange: (field: string, value: string) => void;
  onSave: () => Promise<void>;
  saving: boolean;
}

export default function ConfigureStep({
  system,
  agents,
  edges,
  onEdgeUpdate,
  onSystemMetaChange,
  onSave,
  saving,
}: Props) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);

  const missingEnvVars = edges.filter((e) => !e.env_var.trim());
  const isValid = missingEnvVars.length === 0 && system.name.trim() !== "";

  return (
    <div className="sb-step-content sb-step-configure">
      <div className="sb-step-configure-canvas">
        <WiringCanvas
          agents={agents}
          edges={edges}
          onEdgesChange={() => {}}
          selectedNodeId={selectedNode}
          selectedEdgeId={selectedEdge}
          onSelectNode={setSelectedNode}
          onSelectEdge={setSelectedEdge}
          readOnly
        />
      </div>

      <div className="sb-step-configure-panel">
        <h3 style={{ marginBottom: 12 }}>System Configuration</h3>

        {/* System metadata */}
        <div className="sb-props-section">
          <label className="sb-label">System Name</label>
          <input
            type="text"
            className="sb-input"
            value={system.name}
            onChange={(e) => onSystemMetaChange("name", e.target.value)}
          />
          <label className="sb-label">Description</label>
          <textarea
            className="sb-input"
            value={system.description}
            onChange={(e) => onSystemMetaChange("description", e.target.value)}
            rows={2}
            style={{ resize: "vertical" }}
          />
          <label className="sb-label">UC Catalog</label>
          <input
            type="text"
            className="sb-input"
            value={system.uc_catalog}
            onChange={(e) => onSystemMetaChange("uc_catalog", e.target.value)}
            placeholder="Optional"
          />
          <label className="sb-label">UC Schema</label>
          <input
            type="text"
            className="sb-input"
            value={system.uc_schema}
            onChange={(e) => onSystemMetaChange("uc_schema", e.target.value)}
            placeholder="Optional"
          />
        </div>

        {/* Edge env vars table */}
        {edges.length > 0 && (
          <div className="sb-props-section">
            <div className="sb-section-title">Wiring Env Vars</div>
            <div className="sb-env-table">
              {edges.map((edge) => {
                const edgeId = `${edge.source_agent}->${edge.target_agent}`;
                const isMissing = !edge.env_var.trim();
                return (
                  <div key={edgeId} className="sb-env-row">
                    <span className="sb-env-agents">
                      {edge.source_agent} &rarr; {edge.target_agent}
                    </span>
                    <input
                      type="text"
                      className={`sb-input sb-env-input${isMissing ? " sb-input--error" : ""}`}
                      value={edge.env_var}
                      onChange={(e) => onEdgeUpdate(edgeId, e.target.value)}
                      placeholder="ENV_VAR_NAME"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Validation */}
        {!isValid && (
          <div className="sb-step-validation">
            {!system.name.trim() && <div>System name is required</div>}
            {missingEnvVars.length > 0 && (
              <div>
                {missingEnvVars.length} edge{missingEnvVars.length !== 1 ? "s" : ""} missing env var
                names
              </div>
            )}
          </div>
        )}

        <button
          className="btn btn-sm"
          style={{ background: "var(--accent)", color: "#fff", marginTop: 8 }}
          onClick={onSave}
          disabled={saving || !isValid}
        >
          {saving ? "Saving..." : "Save System"}
        </button>
      </div>
    </div>
  );
}

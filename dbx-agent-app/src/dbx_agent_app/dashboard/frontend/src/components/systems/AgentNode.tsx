/**
 * Custom @xyflow node for agents in the wiring canvas.
 * Adapted from Tables-to-Genies TableNode pattern — left color bar,
 * capability badges, status dot, source/target handles.
 *
 * Visual state (dimming, color mode) is read from WiringCanvasContext
 * so that node objects don't need to be rebuilt on hover/selection changes.
 */
import { memo, useContext } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { WiringCanvasContext } from "./WiringCanvasContext";

/** Role → left bar color mapping */
const ROLE_COLORS: Record<string, string> = {
  supervisor: "#a855f7",
  worker: "#3b82f6",
  tool: "#eab308",
  default: "#3b82f6",
};

/** Deploy status → dot color */
const STATUS_COLORS: Record<string, string> = {
  success: "var(--green)",
  failed: "var(--red)",
  pending: "var(--muted)",
  deploying: "var(--accent)",
};

/** Capability category → color */
const CAPABILITY_COLORS: Record<string, string> = {
  search: "#3b82f6",
  analysis: "#8b5cf6",
  sql: "#22c55e",
  generation: "#f59e0b",
  orchestration: "#ef4444",
};
const DEFAULT_CAP_COLOR = "#6b7280";

function getCapabilityColor(capabilities?: string): string {
  if (!capabilities) return DEFAULT_CAP_COLOR;
  const caps = capabilities.toLowerCase().split(",").map((c) => c.trim());
  for (const cap of caps) {
    for (const [key, color] of Object.entries(CAPABILITY_COLORS)) {
      if (cap.includes(key)) return color;
    }
  }
  return DEFAULT_CAP_COLOR;
}

export interface AgentNodeData {
  label: string;
  [key: string]: unknown;
}

function AgentNodeInner({ id, selected }: NodeProps) {
  const { hoveredNode, connectedToHovered, colorMode, agentMeta, deployStatus } =
    useContext(WiringCanvasContext);

  const meta = agentMeta[id];
  const status = deployStatus[id];
  const isDimmed = hoveredNode !== null && !connectedToHovered.has(id);

  const role = colorMode === "capability" ? undefined : meta?.role;
  const capColor =
    colorMode === "capability" ? getCapabilityColor(meta?.capabilities) : undefined;

  const barColor = capColor ?? ROLE_COLORS[role ?? "default"] ?? ROLE_COLORS.default;

  const caps = meta?.capabilities
    ?.split(",")
    .map((c) => c.trim())
    .filter(Boolean);

  return (
    <div
      className={`sb-agent-node${selected ? " sb-agent-node--highlighted" : ""}${isDimmed ? " sb-agent-node--dimmed" : ""}`}
    >
      {/* Left color bar */}
      <div className="sb-agent-node-bar" style={{ background: barColor }} />

      <div className="sb-agent-node-body">
        {/* Header row: name + status dot */}
        <div className="sb-agent-node-header">
          <span className="sb-agent-node-name">{id}</span>
          {status && (
            <span
              className={`sb-agent-node-status${status === "deploying" ? " sb-deploy-pulse" : ""}`}
              style={{
                background: STATUS_COLORS[status] ?? "var(--muted)",
              }}
            />
          )}
        </div>

        {/* Description (truncated) */}
        {meta?.description && (
          <div className="sb-agent-node-desc">{meta.description}</div>
        )}

        {/* Capability badges */}
        {caps && caps.length > 0 && (
          <div className="sb-agent-node-caps">
            {caps.slice(0, 3).map((cap) => (
              <span key={cap} className="sb-cap-badge">
                {cap}
              </span>
            ))}
            {caps.length > 3 && (
              <span className="sb-cap-badge">+{caps.length - 3}</span>
            )}
          </div>
        )}
      </div>

      {/* Handles for LR dagre layout */}
      <Handle id="target" type="target" position={Position.Left} />
      <Handle id="source" type="source" position={Position.Right} />
    </div>
  );
}

export const AgentNode = memo(AgentNodeInner);

/**
 * Custom @xyflow edge with env var label badge.
 * Adapted from Tables-to-Genies StructuralEdge pattern.
 */
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
} from "@xyflow/react";

export interface WiringEdgeData {
  envVar?: string;
  isDeploying?: boolean;
  [key: string]: unknown;
}

export function WiringEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
  data,
}: EdgeProps) {
  const d = (data ?? {}) as WiringEdgeData;
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 16,
  });

  const strokeColor = selected ? "var(--accent)" : "var(--muted)";

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: strokeColor,
          strokeWidth: selected ? 3 : 2,
          strokeDasharray: d.isDeploying ? "6 3" : undefined,
          animation: d.isDeploying ? "sb-edge-dash 1s linear infinite" : undefined,
        }}
        markerEnd="url(#sb-arrow)"
      />
      <EdgeLabelRenderer>
        <div
          className={`sb-edge-label${selected ? " sb-edge-label--selected" : ""}`}
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
        >
          {d.envVar || "click to set"}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

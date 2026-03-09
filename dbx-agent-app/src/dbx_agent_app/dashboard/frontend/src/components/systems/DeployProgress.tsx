/**
 * Deploy progress display — step-by-step with expandable details.
 * Enhanced with polling support: pulsing dots for in-progress steps.
 */
import { useState } from "react";
import type { DeployResult } from "../../types/systems";

const STATUS_COLORS: Record<string, string> = {
  success: "var(--green)",
  failed: "var(--red)",
  skipped: "var(--yellow)",
};

const ACTION_LABELS: Record<string, string> = {
  env_update: "Env Vars + Redeploy",
  redeploy: "Redeploy",
  grant_permission: "Permission Grant",
  uc_register: "UC Registration",
  resolve: "Resolve Agent",
  lookup: "System Lookup",
  deploy: "Deploy",
};

interface Props {
  result: DeployResult;
  /** When true, shows pulsing indicators for in-progress state */
  isPolling?: boolean;
}

export function DeployProgress({ result, isPolling = false }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const overallColor = STATUS_COLORS[result.status] ?? "var(--muted)";

  return (
    <div className="sb-deploy">
      <div className="sb-deploy-header">
        <span
          className={`sb-deploy-badge${isPolling ? " sb-deploy-pulse" : ""}`}
          style={{ background: overallColor }}
        >
          {result.status.toUpperCase()}
        </span>
        <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
          {result.steps.length} step{result.steps.length !== 1 ? "s" : ""}
          {isPolling && " (polling...)"}
        </span>
      </div>

      <div className="sb-deploy-steps">
        {result.steps.map((step, idx) => {
          const color = STATUS_COLORS[step.status] ?? "var(--muted)";
          const isExpanded = expandedIdx === idx;
          return (
            <div
              key={idx}
              className="sb-deploy-step"
              onClick={() => setExpandedIdx(isExpanded ? null : idx)}
            >
              <div className="sb-deploy-step-row">
                <span
                  className={`sb-deploy-dot${isPolling && step.status !== "success" && step.status !== "failed" ? " sb-deploy-pulse" : ""}`}
                  style={{ background: color }}
                />
                <span style={{ fontWeight: 500, minWidth: 80 }}>
                  {step.agent || "\u2014"}
                </span>
                <span style={{ color: "var(--muted)", flex: 1 }}>
                  {ACTION_LABELS[step.action] ?? step.action}
                </span>
                <span
                  style={{
                    fontWeight: 600,
                    fontSize: "0.7rem",
                    textTransform: "uppercase",
                    color,
                  }}
                >
                  {step.status}
                </span>
              </div>
              {isExpanded && step.detail && (
                <div className="sb-deploy-detail">{step.detail}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

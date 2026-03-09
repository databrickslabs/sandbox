/**
 * Step 4: Deploy — deploy button, polling progress, canvas with status dots.
 * Polls GET /api/systems/{id}/deploy/status every 2s while deploying.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { WiringCanvas } from "../WiringCanvas";
import { DeployProgress } from "../DeployProgress";
import { startDeploy, getDeployStatus } from "../../../api/systems";
import type { WiringEdge, DeployProgress as DeployProgressType } from "../../../types/systems";

interface Props {
  systemId: string | null;
  agents: string[];
  edges: WiringEdge[];
  onSave: () => Promise<void>;
  onDeployComplete?: () => void;
}

export default function DeployStep({ systemId, agents, edges, onSave, onDeployComplete }: Props) {
  const [progress, setProgress] = useState<DeployProgressType | null>(null);
  const [deploying, setDeploying] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>(null);

  // Find the entry-point agent (the orchestrator receives connections but doesn't send them)
  const sourceAgents = new Set(edges.map((e) => e.source_agent));
  const targetOnlyAgents = agents.filter((a) => !sourceAgents.has(a) && edges.some((e) => e.target_agent === a));
  const entryAgent = targetOnlyAgents[0] ?? agents[0] ?? "";

  // Build deploy status map for canvas nodes
  const deployStatusMap: Record<string, string> = {};
  if (progress) {
    for (const step of progress.steps) {
      if (step.agent && step.action === "resolve") {
        deployStatusMap[step.agent] = step.status === "success" ? "success" : "failed";
      }
    }
    if (progress.status === "deploying") {
      for (const name of agents) {
        if (!deployStatusMap[name]) deployStatusMap[name] = "deploying";
      }
    }
  }

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Poll deploy status
  useEffect(() => {
    if (!deploying || !systemId) return;

    const poll = async () => {
      try {
        const status = await getDeployStatus(systemId);
        setProgress(status);
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] Step ${status.current_step}/${status.total_steps}: ${status.status}`,
        ]);

        if (status.status !== "pending" && status.status !== "deploying") {
          setDeploying(false);
          stopPolling();
          onDeployComplete?.();
        }
      } catch {
        // status endpoint not ready yet — keep polling
      }
    };

    pollRef.current = setInterval(poll, 2000);
    // Initial poll after short delay
    const initial = setTimeout(poll, 500);

    return () => {
      stopPolling();
      clearTimeout(initial);
    };
  }, [deploying, systemId, stopPolling]);

  const handleDeploy = async () => {
    if (!systemId) {
      await onSave();
      return;
    }

    setDeploying(true);
    setProgress(null);
    setLogs([`[${new Date().toLocaleTimeString()}] Starting deploy...`]);

    try {
      const initial = await startDeploy(systemId);
      setProgress({
        deploy_id: initial.deploy_id,
        system_id: systemId,
        status: initial.status as DeployProgressType["status"],
        current_step: 0,
        total_steps: 0,
        steps: [],
      });
    } catch (e) {
      setDeploying(false);
      setLogs((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Deploy failed: ${e instanceof Error ? e.message : "Unknown error"}`,
      ]);
    }
  };

  const handleRedeploy = () => {
    setProgress(null);
    setLogs([]);
    handleDeploy();
  };

  return (
    <div className="sb-step-content sb-step-deploy">
      <div className="sb-step-deploy-canvas">
        <div className="sb-step-header">
          <h3>Deploy</h3>
          <span className="sb-step-hint">
            {progress?.status === "success"
              ? "Deployment complete"
              : progress?.status === "deploying"
                ? "Deploying..."
                : "Ready to deploy"}
          </span>
        </div>
        <WiringCanvas
          agents={agents}
          edges={edges}
          onEdgesChange={() => {}}
          selectedNodeId={null}
          selectedEdgeId={null}
          onSelectNode={() => {}}
          onSelectEdge={() => {}}
          deployStatus={deployStatusMap}
          readOnly
          showMiniMap
        />
      </div>

      <div className="sb-step-deploy-panel">
        {/* Deploy action */}
        <button
          className="btn btn-sm"
          style={{
            background: deploying ? "var(--muted)" : "var(--accent)",
            color: "#fff",
            width: "100%",
          }}
          onClick={handleDeploy}
          disabled={deploying || !systemId}
        >
          {deploying ? "Deploying..." : "Deploy System"}
        </button>

        {/* Progress */}
        {progress && progress.steps.length > 0 && (
          <DeployProgress
            result={{
              system_id: progress.system_id,
              steps: progress.steps,
              status: progress.status === "deploying" ? "partial" : progress.status as "success" | "partial" | "failed",
            }}
            isPolling={deploying}
          />
        )}

        {/* Post-deploy actions */}
        {progress &&
          progress.status !== "pending" &&
          progress.status !== "deploying" && (
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button
                className="btn btn-outline btn-sm"
                onClick={handleRedeploy}
              >
                Re-deploy
              </button>
              <a
                href={`#/agent/${entryAgent}`}
                className="btn btn-sm"
                style={{ background: "var(--green)", color: "#fff", textDecoration: "none" }}
              >
                Test in Chat
              </a>
            </div>
          )}

        {/* Expandable logs terminal */}
        <div style={{ marginTop: 12 }}>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => setShowLogs(!showLogs)}
            style={{ fontSize: "0.75rem" }}
          >
            {showLogs ? "Hide logs" : "View logs"}
          </button>
          {showLogs && (
            <div className="sb-deploy-terminal">
              {logs.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
              {logs.length === 0 && (
                <div style={{ color: "var(--muted)" }}>No logs yet.</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useAgents } from "../../hooks/useAgents";
import { AgentCard } from "./AgentCard";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";
import { EmptyState } from "../common/EmptyState";

export function AgentGrid() {
  const { agents, loading, error, scan } = useAgents();

  return (
    <>
      <div className="toolbar">
        <span className="status-text">
          {loading
            ? "Loading..."
            : `${agents.length} agent${agents.length !== 1 ? "s" : ""} discovered`}
        </span>
        <button className="btn btn-primary" onClick={scan} disabled={loading}>
          {loading ? (
            <>
              <Spinner /> Scanning...
            </>
          ) : (
            "Scan workspace"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {!loading && agents.length === 0 && !error && (
        <EmptyState
          title="No agents discovered"
          message="No agent-enabled Databricks Apps found in your workspace. Click Scan to retry."
        />
      )}

      {agents.length > 0 && (
        <div className="grid">
          {agents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      )}
    </>
  );
}

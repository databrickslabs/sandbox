import { useNavigate } from "react-router-dom";
import type { Agent } from "../../types";

interface Props {
  agent: Agent;
}

const SUPERVISOR_KEYWORDS = ["orchestration", "routing", "supervisor"];

export function AgentCard({ agent }: Props) {
  const navigate = useNavigate();

  const capabilities = agent.capabilities
    ? agent.capabilities.split(",").map((c) => c.trim())
    : [];

  const isSupervisor = capabilities.some((c) =>
    SUPERVISOR_KEYWORDS.includes(c.toLowerCase()),
  );

  return (
    <div className="card" onClick={() => navigate(`/agent/${agent.name}`)}>
      <div className="card-header-row">
        <h3>{agent.name}</h3>
        <span
          className={`badge ${isSupervisor ? "badge-yellow" : "badge-green"}`}
        >
          {isSupervisor ? "Supervisor" : "Worker"}
        </span>
      </div>
      <p>{agent.description ?? "No description"}</p>

      {capabilities.length > 0 && (
        <div className="meta">
          {capabilities.map((cap) => (
            <span key={cap} className="badge badge-blue">
              {cap}
            </span>
          ))}
        </div>
      )}

      <div className="card-footer">
        <span className="card-stat">App: {agent.app_name}</span>
        <div className="card-endpoints">
          <span className="badge badge-dim">/invocations</span>
          <span className="badge badge-dim">A2A</span>
          <span className="badge badge-dim">MCP</span>
        </div>
      </div>
    </div>
  );
}

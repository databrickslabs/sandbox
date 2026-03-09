import { useNavigate } from "react-router-dom";
import type { Agent } from "../../types";

interface Props {
  agent: Agent;
}

export function AgentCard({ agent }: Props) {
  const navigate = useNavigate();

  const capabilities = agent.capabilities
    ? agent.capabilities.split(",").map((c) => c.trim())
    : [];

  return (
    <div className="card" onClick={() => navigate(`/agent/${agent.name}`)}>
      <h3>{agent.name}</h3>
      <p>{agent.description ?? "No description"}</p>
      <div className="meta">
        <span>App: {agent.app_name}</span>
        {agent.protocol_version && (
          <span className="badge badge-green">{agent.protocol_version}</span>
        )}
      </div>
      {capabilities.length > 0 && (
        <div className="meta">
          {capabilities.map((cap) => (
            <span key={cap} className="badge badge-blue">
              {cap}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

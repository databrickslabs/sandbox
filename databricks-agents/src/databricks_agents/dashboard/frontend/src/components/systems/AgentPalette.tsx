import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import type { Agent } from "../../types";

interface Props {
  onAddAgent: (name: string) => void;
  addedAgents: Set<string>;
}

export function AgentPalette({ onAddAgent, addedAgents }: Props) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    apiFetch<Agent[]>("/api/agents")
      .then(setAgents)
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = agents.filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      (a.description ?? "").toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="sb-palette">
      <h3 className="sb-palette-title">Agents</h3>
      <input
        type="text"
        className="sb-input"
        placeholder="Search agents..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {loading ? (
        <div className="sb-muted-center">Loading agents...</div>
      ) : filtered.length === 0 ? (
        <div className="sb-muted-center">No agents found</div>
      ) : (
        <div className="sb-palette-list">
          {filtered.map((agent) => {
            const isAdded = addedAgents.has(agent.name);
            return (
              <div
                key={agent.name}
                className={`sb-palette-item${isAdded ? " sb-palette-item--added" : ""}`}
                onClick={() => !isAdded && onAddAgent(agent.name)}
              >
                <div className="sb-palette-name">{agent.name}</div>
                {agent.description && (
                  <div className="sb-palette-desc">{agent.description}</div>
                )}
                {agent.capabilities && (
                  <div className="sb-palette-caps">
                    {agent.capabilities
                      .split(",")
                      .map((c) => c.trim())
                      .filter(Boolean)
                      .map((cap) => (
                        <span key={cap} className="sb-cap-badge">
                          {cap}
                        </span>
                      ))}
                  </div>
                )}
                {isAdded && <span className="sb-palette-added">Added</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

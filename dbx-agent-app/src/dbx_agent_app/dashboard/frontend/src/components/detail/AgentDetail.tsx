import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAgents } from "../../hooks/useAgents";
import { useAgentCard } from "../../hooks/useAgentCard";
import { useMcp } from "../../hooks/useMcp";
import { TabBar } from "./TabBar";
import { OverviewTab } from "./OverviewTab";
import { ChatTab } from "./ChatTab";
import { ToolsTab } from "./ToolsTab";
import { McpTab } from "./McpTab";
import { LineageTab } from "./LineageTab";
import { GovernanceTab } from "./GovernanceTab";
import { Badge } from "../common/Badge";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "chat", label: "Chat" },
  { id: "tools", label: "Tools" },
  { id: "lineage", label: "Lineage" },
  { id: "governance", label: "Governance" },
  { id: "mcp", label: "MCP" },
];

export function AgentDetail() {
  const { name } = useParams<{ name: string }>();
  const { agents } = useAgents();
  const { card, loading: cardLoading, error: cardError } = useAgentCard(name!);
  const mcp = useMcp(name!);
  const [activeTab, setActiveTab] = useState("overview");

  const agent = agents.find((a) => a.name === name || a.app_name === name);

  if (!agent) {
    return (
      <div className="empty-state">
        <h2>Agent not found</h2>
        <p>
          No agent named "{name}" was found.{" "}
          <Link to="/">Back to agents</Link>
        </p>
      </div>
    );
  }

  const capabilities = agent.capabilities
    ? agent.capabilities.split(",").map((c) => c.trim())
    : [];

  return (
    <>
      <div className="detail-header">
        <Link to="/">&larr; All agents</Link>
        <h2>{agent.name}</h2>
        <p style={{ color: "var(--muted)" }}>
          {agent.description ?? "No description"}
        </p>
        <div className="meta" style={{ marginTop: "0.5rem" }}>
          <span>App: {agent.app_name}</span>
          {agent.protocol_version && (
            <Badge label={agent.protocol_version} variant="green" />
          )}
          {capabilities.map((cap) => (
            <Badge key={cap} label={cap} />
          ))}
        </div>
      </div>

      <TabBar tabs={TABS} active={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" && (
        <OverviewTab
          agent={agent}
          card={card}
          loading={cardLoading}
          error={cardError}
        />
      )}
      {activeTab === "chat" && <ChatTab agentName={agent.name} />}
      {activeTab === "tools" && (
        <ToolsTab
          tools={mcp.tools}
          loading={mcp.toolsLoading}
          error={mcp.toolsError}
          onLoad={mcp.loadTools}
        />
      )}
      {activeTab === "lineage" && <LineageTab agentName={agent.name} />}
      {activeTab === "governance" && <GovernanceTab agentName={agent.name} />}
      {activeTab === "mcp" && (
        <McpTab
          agentName={agent.name}
          lastResponse={mcp.lastResponse}
          sending={mcp.sendingMcp}
          onSendRaw={mcp.sendRaw}
        />
      )}
    </>
  );
}

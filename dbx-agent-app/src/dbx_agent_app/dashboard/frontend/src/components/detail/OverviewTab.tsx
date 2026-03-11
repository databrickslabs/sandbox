import type { Agent, AgentCard, AgentTool } from "../../types";
import { JsonViewer } from "../common/JsonViewer";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";
import "./OverviewTab.css";

interface Props {
  agent: Agent;
  card: AgentCard | null;
  loading: boolean;
  error: string | null;
  tools: AgentTool[];
}

const SUPERVISOR_KEYWORDS = ["orchestration", "routing", "supervisor"];

const CAPABILITY_MAP: Record<string, string> = {
  research: "Expert transcript search and analysis",
  search: "Full-text and semantic search",
  sql: "SQL warehouse query execution",
  orchestration: "Multi-agent routing and coordination",
  routing: "Query routing to sub-agents",
  expert_finder: "Find domain experts by topic",
  analytics: "Business metrics and analytics",
  compliance: "Compliance and conflict checks",
  greeting: "Simple greeting / hello-world",
};

function sanitizeName(name: string): string {
  return name.replace(/[^a-zA-Z0-9_]/g, "_");
}

export function OverviewTab({ agent, card, loading, error, tools }: Props) {
  const capabilities = agent.capabilities
    ? agent.capabilities.split(",").map((c) => c.trim())
    : [];

  const isSupervisor = capabilities.some((c) =>
    SUPERVISOR_KEYWORDS.includes(c.toLowerCase()),
  );

  const cardTools = card?.tools ?? card?.skills ?? [];
  const allTools = cardTools.length > 0 ? cardTools : tools;

  const baseUrl = agent.endpoint_url?.replace(/\/$/, "") ?? "";

  const endpoints = [
    { path: "/invocations", protocol: "A2A", desc: "Databricks Responses Agent protocol — send messages, receive streaming responses" },
    { path: "/.well-known/agent.json", protocol: "A2A", desc: "Agent discovery card — capabilities, tools, and metadata" },
    { path: "/health", protocol: "HTTP", desc: "Health check — returns 200 when agent is ready" },
  ];
  if (card?.endpoints && typeof card.endpoints === "object") {
    const ep = card.endpoints as Record<string, string>;
    if (ep.mcp) {
      endpoints.push({ path: ep.mcp, protocol: "MCP", desc: "JSON-RPC tool server — list and invoke tools programmatically" });
    }
  }

  return (
    <>
      {loading && (
        <div style={{ textAlign: "center", padding: "2rem" }}>
          <Spinner large /> Loading agent card...
        </div>
      )}

      {error && <ErrorBanner message={error} />}

      {/* Section A: Architecture Banner */}
      <div className={`overview-banner ${isSupervisor ? "supervisor" : "worker"}`}>
        <div className="overview-banner-icon">
          {isSupervisor ? "\u{1F3AF}" : "\u{26A1}"}
        </div>
        <div className="overview-banner-text">
          <h3>{isSupervisor ? "Supervisor Agent" : "Worker Agent"}</h3>
          <p>
            {isSupervisor
              ? "Routes queries to specialized sub-agents via LLM function calling"
              : "Independently deployed agent with dedicated tools and endpoints"}
          </p>
        </div>
        <div className="overview-banner-meta">
          {typeof card?.version === "string" && (
            <span className="badge badge-dim">v{card.version}</span>
          )}
          {agent.protocol_version && (
            <span className="badge badge-green">{agent.protocol_version}</span>
          )}
        </div>
      </div>

      {/* Section B: Endpoints + Agent Card JSON */}
      <div className="section">
        <h3>Endpoints</h3>
        <p className="section-subtitle">
          Every <code>@app_agent</code> automatically exposes these protocol endpoints:
        </p>
        <div className="endpoints-layout">
          {/* Left: endpoint table */}
          <div className="endpoints-table">
            <div className="endpoints-row endpoints-header">
              <span>Protocol</span>
              <span>Path</span>
              <span>Description</span>
            </div>
            {endpoints.map((ep) => (
              <div key={ep.path} className="endpoints-row">
                <span className="endpoint-protocol">
                  <span className="badge badge-dim">{ep.protocol}</span>
                </span>
                <div className="endpoint-paths">
                  <code className="endpoint-path">{ep.path}</code>
                  {baseUrl && (
                    <code className="endpoint-url">{baseUrl}{ep.path}</code>
                  )}
                </div>
                <span className="endpoint-desc">{ep.desc}</span>
              </div>
            ))}
          </div>

          {/* Right: live /.well-known/agent.json response */}
          {card && (
            <div className="agent-card-json">
              <div className="agent-card-json-header">
                <code>/.well-known/agent.json</code>
                <span className="badge badge-green">LIVE</span>
              </div>
              <pre className="agent-card-json-body">
                <JsonViewer data={card} />
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Section C: Tools Preview */}
      {allTools.length > 0 && (
        <div className="section">
          <h3>Registered Tools ({allTools.length})</h3>
          <div className="overview-tools-preview">
            {allTools.map((t) => {
              const name = t.name ?? t.id ?? "unknown";
              return (
                <div key={name} className="tool-preview-item">
                  <span className="tool-preview-name">{name}</span>
                  <span className="tool-preview-desc">
                    {t.description ?? ""}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Section D: Code Pattern Showcase */}
      <div className="section">
        <h3>Built with @app_agent</h3>
        <div className="overview-code-grid">
          <div className="code-block">
            <div className="code-block-header">app.py</div>
            <pre>
              <span className="kw">from</span> dbx_agent_app <span className="kw">import</span> app_agent, AgentRequest, AgentResponse{"\n"}
              {"\n"}
              <span className="kw">@</span><span className="fn">app_agent</span>({"\n"}
              {"    "}name=<span className="str">"{agent.name}"</span>,{"\n"}
              {"    "}description=<span className="str">"{agent.description ?? "..."}"</span>,{"\n"}
              {"    "}capabilities={formatList(capabilities)},{"\n"}
              ){"\n"}
              <span className="kw">async def</span> <span className="fn">{sanitizeName(agent.name)}</span>(request: <span className="type">AgentRequest</span>) -&gt; <span className="type">AgentResponse</span>:{"\n"}
              {"    "}<span className="comment"># Your agent logic here</span>{"\n"}
              {"    "}<span className="kw">return</span> AgentResponse.<span className="fn">text</span>(result)
            </pre>
          </div>
          <div className="code-block">
            <div className="code-block-header">app.yaml</div>
            <pre>
              <span className="kw">command</span>:{"\n"}
              {"  "}- <span className="str">"python"</span>{"\n"}
              {"  "}- <span className="str">"-m"</span>{"\n"}
              {"  "}- <span className="str">"uvicorn"</span>{"\n"}
              {"  "}- <span className="str">"app:app"</span>{"\n"}
              {"  "}- <span className="str">"--host"</span>{"\n"}
              {"  "}- <span className="str">"0.0.0.0"</span>{"\n"}
              {"  "}- <span className="str">"--port"</span>{"\n"}
              {"  "}- <span className="str">"8000"</span>{"\n"}
              {"\n"}
              <span className="kw">env</span>:{"\n"}
              {"  "}- <span className="type">name</span>: MODEL_ENDPOINT{"\n"}
              {"    "}<span className="type">value</span>: <span className="str">databricks-claude-sonnet-4-6</span>
            </pre>
          </div>
        </div>
      </div>

      {/* Section E: Capabilities */}
      {capabilities.length > 0 && (
        <div className="section">
          <h3>Capabilities</h3>
          <div className="overview-capabilities">
            {capabilities.map((cap) => (
              <div key={cap} className="capability-item">
                <div className="dot" />
                <span className="capability-label">{cap}</span>
                {CAPABILITY_MAP[cap.toLowerCase()] && (
                  <span className="capability-desc">
                    {CAPABILITY_MAP[cap.toLowerCase()]}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </>
  );
}

function formatList(items: string[]): string {
  if (items.length === 0) return "[]";
  return `[${items.map((i) => `"${i}"`).join(", ")}]`;
}

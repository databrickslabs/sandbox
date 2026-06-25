import { useEffect } from "react";
import type { AgentTool } from "../../types";
import { useObservedData } from "../../hooks/useChatObservability";
import { JsonViewer } from "../common/JsonViewer";
import { Badge } from "../common/Badge";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";
import { EmptyState } from "../common/EmptyState";

interface Props {
  tools: AgentTool[];
  loading: boolean;
  error: string | null;
  onLoad: () => void;
  agentName: string;
}

export function ToolsTab({ tools, loading, error, onLoad, agentName }: Props) {
  const observed = useObservedData(agentName);
  useEffect(() => {
    if (tools.length === 0 && !loading && !error) {
      onLoad();
    }
  }, [tools.length, loading, error, onLoad]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <Spinner large /> Loading tools...
      </div>
    );
  }

  if (error) return <ErrorBanner message={error} />;

  const hasObservedTools = observed && observed.tools.length > 0;

  if (tools.length === 0 && !hasObservedTools) {
    return (
      <EmptyState
        title="No tools found"
        message="This agent didn't return any tools via MCP tools/list. Chat with the agent to observe tool invocations at runtime."
      />
    );
  }

  return (
    <div>
      {/* MCP tool schemas */}
      {tools.length > 0 && (
        <div className="section">
          <h3>Tools ({tools.length})</h3>
          {tools.map((tool) => {
            const name = tool.name ?? tool.id ?? "unknown";
            return (
              <div key={name} className="tool-row">
                <div className="tool-name">{name}</div>
                {tool.description && (
                  <div className="tool-desc">{tool.description}</div>
                )}
                {tool.inputSchema && (
                  <details style={{ marginTop: "0.25rem" }}>
                    <summary
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.8rem",
                        cursor: "pointer",
                      }}
                    >
                      Input schema
                    </summary>
                    <pre style={{ marginTop: "0.5rem" }}>
                      <JsonViewer data={tool.inputSchema} defaultExpanded={false} />
                    </pre>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Recent invocations from chat */}
      {hasObservedTools && (
        <div className="section">
          <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            Recent Invocations
            <Badge label={`${observed.tools.length} call${observed.tools.length > 1 ? "s" : ""}`} variant="blue" />
          </h3>
          {observed.tools.map((inv) => (
            <div key={inv.id} className="tool-row">
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <div className="tool-name">{inv.toolName}</div>
                <Badge
                  label={inv.status}
                  variant={inv.status === "success" ? "green" : "red"}
                />
                {inv.durationMs != null && (
                  <span style={{ color: "var(--muted)", fontSize: "0.75rem" }}>
                    {inv.durationMs}ms
                  </span>
                )}
                <span style={{ color: "var(--muted)", fontSize: "0.75rem", marginLeft: "auto" }}>
                  {new Date(inv.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <details style={{ marginTop: "0.25rem" }}>
                <summary style={{ color: "var(--muted)", fontSize: "0.8rem", cursor: "pointer" }}>
                  Arguments &amp; result
                </summary>
                <div style={{ marginTop: "0.5rem" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginBottom: "0.25rem" }}>Args:</div>
                  <pre><JsonViewer data={inv.args} defaultExpanded={false} /></pre>
                  {inv.result !== undefined && (
                    <>
                      <div style={{ fontSize: "0.75rem", color: "var(--muted)", margin: "0.5rem 0 0.25rem" }}>Result:</div>
                      <pre><JsonViewer data={inv.result} defaultExpanded={false} /></pre>
                    </>
                  )}
                </div>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

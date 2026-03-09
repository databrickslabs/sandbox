import { useEffect } from "react";
import type { AgentTool } from "../../types";
import { JsonViewer } from "../common/JsonViewer";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";
import { EmptyState } from "../common/EmptyState";

interface Props {
  tools: AgentTool[];
  loading: boolean;
  error: string | null;
  onLoad: () => void;
}

export function ToolsTab({ tools, loading, error, onLoad }: Props) {
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

  if (tools.length === 0) {
    return (
      <EmptyState
        title="No tools found"
        message="This agent didn't return any tools via MCP tools/list."
      />
    );
  }

  return (
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
  );
}

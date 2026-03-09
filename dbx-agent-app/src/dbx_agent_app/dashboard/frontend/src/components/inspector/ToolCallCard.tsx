import type { ToolCallEntry } from "../../types";
import { JsonViewer } from "../common/JsonViewer";

interface Props {
  entry: ToolCallEntry;
}

export function ToolCallCard({ entry }: Props) {
  const duration =
    entry.endTime && entry.startTime
      ? `${entry.endTime - entry.startTime}ms`
      : "...";

  return (
    <div className={`tool-call-card ${entry.status}`}>
      <div className="tc-name">{entry.toolName}</div>
      <div className="tc-timing">{duration}</div>
      {Object.keys(entry.args).length > 0 && (
        <details style={{ marginTop: "0.25rem" }}>
          <summary style={{ color: "var(--muted)", fontSize: "0.75rem", cursor: "pointer" }}>
            Arguments
          </summary>
          <div style={{ marginTop: "0.25rem" }}>
            <JsonViewer data={entry.args} defaultExpanded={false} />
          </div>
        </details>
      )}
      {entry.result !== undefined && (
        <details style={{ marginTop: "0.25rem" }}>
          <summary style={{ color: "var(--muted)", fontSize: "0.75rem", cursor: "pointer" }}>
            Result
          </summary>
          <div style={{ marginTop: "0.25rem" }}>
            <JsonViewer data={entry.result} defaultExpanded={false} />
          </div>
        </details>
      )}
    </div>
  );
}

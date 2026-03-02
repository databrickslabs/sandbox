import { useState } from "react";
import type { Artifact, ArtifactType } from "../../types";
import { JsonViewer } from "../common/JsonViewer";

interface Props {
  artifacts: Artifact[];
}

const TYPE_ICONS: Record<ArtifactType, { symbol: string; color: string }> = {
  json: { symbol: "{}", color: "var(--accent)" },
  text: { symbol: "Aa", color: "var(--green)" },
  image: { symbol: "IMG", color: "#c084fc" },
  file: { symbol: "DL", color: "var(--yellow)" },
  table: { symbol: "TBL", color: "#f97316" },
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString();
}

function ArtifactDetail({ artifact }: { artifact: Artifact }) {
  switch (artifact.type) {
    case "image":
      return artifact.preview ? (
        <img
          src={artifact.preview}
          alt={artifact.label}
          style={{ maxWidth: "100%", borderRadius: 4 }}
        />
      ) : (
        <span style={{ color: "var(--muted)" }}>No preview available</span>
      );

    case "file":
      return artifact.url ? (
        <a
          href={artifact.url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-outline btn-sm"
        >
          Download file
        </a>
      ) : (
        <span style={{ color: "var(--muted)" }}>No download URL</span>
      );

    case "table": {
      const obj = artifact.data as Record<string, unknown>;
      const rows = (obj.rows ?? obj.data ?? []) as Array<Record<string, unknown>>;
      if (!Array.isArray(rows) || rows.length === 0) {
        return <JsonViewer data={artifact.data} defaultExpanded={false} />;
      }
      const columns = Object.keys(rows[0] as Record<string, unknown>);
      return (
        <div style={{ overflowX: "auto" }}>
          <table className="governance-table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 50).map((row, i) => (
                <tr key={i}>
                  {columns.map((col) => (
                    <td key={col}>{String(row[col] ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length > 50 && (
            <div style={{ color: "var(--muted)", fontSize: "0.75rem", marginTop: "0.5rem" }}>
              Showing 50 of {rows.length} rows
            </div>
          )}
        </div>
      );
    }

    case "text":
      return (
        <pre style={{ maxHeight: 300, overflow: "auto", fontSize: "0.8rem" }}>
          {String(artifact.data)}
        </pre>
      );

    case "json":
    default:
      return <JsonViewer data={artifact.data} defaultExpanded={false} />;
  }
}

export function ArtifactsPanel({ artifacts }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (artifacts.length === 0) {
    return (
      <div className="artifacts-empty">
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          Artifacts from tool results will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="artifacts-panel">
      {artifacts.map((art) => {
        const icon = TYPE_ICONS[art.type];
        const isExpanded = expandedId === art.id;
        return (
          <div key={art.id} className="artifact-card">
            <div
              className="artifact-header"
              onClick={() => setExpandedId(isExpanded ? null : art.id)}
            >
              <span
                className="artifact-icon"
                style={{ background: `${icon.color}20`, color: icon.color }}
              >
                {icon.symbol}
              </span>
              <div className="artifact-info">
                <span className="artifact-label">{art.label}</span>
                <span className="artifact-meta">
                  {formatTime(art.timestamp)}
                  {art.sizeBytes !== undefined && (
                    <> · {formatBytes(art.sizeBytes)}</>
                  )}
                </span>
              </div>
              <span className="trace-event-expand">{isExpanded ? "▼" : "▶"}</span>
            </div>
            {isExpanded && (
              <div className="artifact-body">
                <ArtifactDetail artifact={art} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

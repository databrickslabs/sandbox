import { useState } from "react";

interface Props {
  data: unknown;
  defaultExpanded?: boolean;
}

export function JsonViewer({ data, defaultExpanded = true }: Props) {
  return (
    <div className="json-viewer">
      <JsonNode value={data} depth={0} defaultExpanded={defaultExpanded} />
    </div>
  );
}

function JsonNode({
  value,
  depth,
  defaultExpanded,
}: {
  value: unknown;
  depth: number;
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded || depth < 2);

  if (value === null) {
    return <span className="json-null">null</span>;
  }

  if (typeof value === "boolean") {
    return <span className="json-bool">{String(value)}</span>;
  }

  if (typeof value === "number") {
    return <span className="json-number">{value}</span>;
  }

  if (typeof value === "string") {
    return <span className="json-string">"{value}"</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span>[]</span>;
    return (
      <span>
        <span className="json-toggle" onClick={() => setExpanded(!expanded)}>
          {expanded ? "▼" : "▶"} [{value.length}]
        </span>
        {expanded && (
          <div style={{ paddingLeft: "1.25rem" }}>
            {value.map((item, i) => (
              <div key={i}>
                <JsonNode
                  value={item}
                  depth={depth + 1}
                  defaultExpanded={defaultExpanded}
                />
                {i < value.length - 1 && ","}
              </div>
            ))}
          </div>
        )}
      </span>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return <span>{"{}"}</span>;
    return (
      <span>
        <span className="json-toggle" onClick={() => setExpanded(!expanded)}>
          {expanded ? "▼" : "▶"} {"{"}
          {entries.length}
          {"}"}
        </span>
        {expanded && (
          <div style={{ paddingLeft: "1.25rem" }}>
            {entries.map(([key, val], i) => (
              <div key={key}>
                <span className="json-key">"{key}"</span>:{" "}
                <JsonNode
                  value={val}
                  depth={depth + 1}
                  defaultExpanded={defaultExpanded}
                />
                {i < entries.length - 1 && ","}
              </div>
            ))}
          </div>
        )}
      </span>
    );
  }

  return <span>{String(value)}</span>;
}

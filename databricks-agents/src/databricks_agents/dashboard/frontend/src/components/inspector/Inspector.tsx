import { useState } from "react";
import type { ToolCallEntry, TraceTurn, Artifact } from "../../types";
import { ToolTimeline } from "./ToolTimeline";
import { TracePanel } from "./TracePanel";
import { ArtifactsPanel } from "./ArtifactsPanel";
import { RoutingPanel } from "./RoutingPanel";

type InspectorTab = "routing" | "trace" | "tools" | "artifacts";

interface Props {
  toolCalls: ToolCallEntry[];
  traces: TraceTurn[];
  artifacts: Artifact[];
  selectedTraceId: string | null;
  onSelectTrace: (traceId: string | null) => void;
}

export function Inspector({
  toolCalls,
  traces,
  artifacts,
  selectedTraceId,
  onSelectTrace,
}: Props) {
  const routingCount = traces.filter((t) => t.routing).length;
  const [tab, setTab] = useState<InspectorTab>(routingCount > 0 ? "routing" : "trace");

  return (
    <div className="inspector-panel">
      <div className="inspector-tabs">
        <button
          className={`inspector-tab ${tab === "routing" ? "active" : ""}`}
          onClick={() => setTab("routing")}
        >
          Routing
          {routingCount > 0 && (
            <span className="inspector-badge">{routingCount}</span>
          )}
        </button>
        <button
          className={`inspector-tab ${tab === "trace" ? "active" : ""}`}
          onClick={() => setTab("trace")}
        >
          Trace
          {traces.length > 0 && (
            <span className="inspector-badge">{traces.length}</span>
          )}
        </button>
        <button
          className={`inspector-tab ${tab === "tools" ? "active" : ""}`}
          onClick={() => setTab("tools")}
        >
          Tools
          {toolCalls.length > 0 && (
            <span className="inspector-badge">{toolCalls.length}</span>
          )}
        </button>
        <button
          className={`inspector-tab ${tab === "artifacts" ? "active" : ""}`}
          onClick={() => setTab("artifacts")}
        >
          Artifacts
          {artifacts.length > 0 && (
            <span className="inspector-badge">{artifacts.length}</span>
          )}
        </button>
      </div>

      <div className="inspector-content">
        {tab === "routing" && <RoutingPanel traces={traces} />}
        {tab === "trace" && (
          <TracePanel
            traces={traces}
            selectedTraceId={selectedTraceId}
            onSelectTrace={onSelectTrace}
          />
        )}
        {tab === "tools" && <ToolTimeline entries={toolCalls} />}
        {tab === "artifacts" && <ArtifactsPanel artifacts={artifacts} />}
      </div>
    </div>
  );
}

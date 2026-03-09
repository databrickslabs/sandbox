import { useState } from "react";
import type { TraceTurn, TraceEvent } from "../../types";
import { JsonViewer } from "../common/JsonViewer";

interface Props {
  traces: TraceTurn[];
  selectedTraceId: string | null;
  onSelectTrace: (traceId: string | null) => void;
}

const PROTOCOL_COLORS: Record<string, string> = {
  a2a: "var(--accent)",
  mcp_fallback: "var(--yellow)",
};

const EVENT_COLORS: Record<string, string> = {
  a2a_request: "var(--accent)",
  a2a_response: "var(--accent)",
  mcp_tools_list: "var(--green)",
  mcp_tools_call: "var(--yellow)",
  error: "var(--red)",
};

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString();
}

type DetailTab = "events" | "request" | "response";

function TraceDetail({ trace }: { trace: TraceTurn }) {
  const [tab, setTab] = useState<DetailTab>("events");
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  const toggleEvent = (id: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="trace-detail">
      <div className="trace-detail-tabs">
        {(["events", "request", "response"] as DetailTab[]).map((t) => (
          <button
            key={t}
            className={`trace-detail-tab ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "events" && (
        <div className="trace-events">
          {trace.events.map((ev) => (
            <EventRow
              key={ev.id}
              event={ev}
              expanded={expandedEvents.has(ev.id)}
              onToggle={() => toggleEvent(ev.id)}
            />
          ))}
        </div>
      )}

      {tab === "request" && (
        <div className="trace-payload">
          {trace.requestPayload ? (
            <JsonViewer data={trace.requestPayload} defaultExpanded />
          ) : (
            <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
              No request payload captured
            </span>
          )}
        </div>
      )}

      {tab === "response" && (
        <div className="trace-payload">
          {trace.responsePayload ? (
            <JsonViewer data={trace.responsePayload} defaultExpanded />
          ) : (
            <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
              No response payload captured
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function EventRow({
  event,
  expanded,
  onToggle,
}: {
  event: TraceEvent;
  expanded: boolean;
  onToggle: () => void;
}) {
  const color = EVENT_COLORS[event.type] ?? "var(--muted)";
  return (
    <div className="trace-event-row">
      <div className="trace-event-header" onClick={onToggle}>
        <span className="trace-event-dot" style={{ background: color }} />
        <span className="trace-event-label">{event.label}</span>
        {event.durationMs !== undefined && (
          <span className="trace-event-duration">{formatMs(event.durationMs)}</span>
        )}
        {event.payload != null && (
          <span className="trace-event-expand">{expanded ? "▼" : "▶"}</span>
        )}
      </div>
      {expanded && event.payload != null && (
        <div className="trace-event-payload">
          <JsonViewer data={event.payload} defaultExpanded={false} />
        </div>
      )}
    </div>
  );
}

export function TracePanel({ traces, selectedTraceId, onSelectTrace }: Props) {
  if (traces.length === 0) {
    return (
      <div className="trace-empty">
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          Trace data will appear here as you chat with the agent.
        </p>
      </div>
    );
  }

  const selectedTrace = selectedTraceId
    ? traces.find((t) => t.id === selectedTraceId)
    : null;

  return (
    <div className="trace-panel">
      <div className="trace-turn-list">
        {traces.map((trace, i) => {
          const isSelected = trace.id === selectedTraceId;
          const hasError = trace.events.some((e) => e.type === "error");
          return (
            <div
              key={trace.id}
              className={`trace-turn-row ${isSelected ? "selected" : ""} ${hasError ? "error" : ""}`}
              onClick={() => onSelectTrace(isSelected ? null : trace.id)}
            >
              <div className="trace-turn-header">
                <span className="trace-turn-label">Turn {i + 1}</span>
                <span
                  className="badge"
                  style={{
                    background: `${PROTOCOL_COLORS[trace.protocol]}20`,
                    color: PROTOCOL_COLORS[trace.protocol],
                    fontSize: "0.65rem",
                    padding: "1px 6px",
                  }}
                >
                  {trace.protocol === "a2a" ? "A2A" : "MCP"}
                </span>
              </div>
              <div className="trace-turn-meta">
                <span>{formatTime(trace.startTime)}</span>
                {trace.latencyMs !== undefined && (
                  <>
                    <span style={{ margin: "0 4px" }}>·</span>
                    <span>{formatMs(trace.latencyMs)}</span>
                  </>
                )}
                <span style={{ margin: "0 4px" }}>·</span>
                <span>{trace.events.length} events</span>
              </div>
              {trace.latencyMs !== undefined && (
                <div className="trace-latency-bar">
                  <div
                    className="trace-latency-fill"
                    style={{
                      width: `${Math.min(100, (trace.latencyMs / 5000) * 100)}%`,
                      background: hasError ? "var(--red)" : PROTOCOL_COLORS[trace.protocol],
                    }}
                  />
                </div>
              )}
              {trace.serverTiming && trace.latencyMs !== undefined && (
                <div className="trace-server-timing">
                  Server: {formatMs(trace.serverTiming.latencyMs)} / Client: {formatMs(trace.latencyMs)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedTrace && <TraceDetail trace={selectedTrace} />}
    </div>
  );
}

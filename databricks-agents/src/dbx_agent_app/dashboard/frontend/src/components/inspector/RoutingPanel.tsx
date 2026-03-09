import { useState } from "react";
import type { TraceTurn, RoutingInfo, SqlQueryTrace } from "../../types";

interface Props {
  traces: TraceTurn[];
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function DataSourceBadge({ source }: { source: string }) {
  const colors: Record<string, { bg: string; fg: string; label: string }> = {
    live: { bg: "rgba(34, 197, 94, 0.15)", fg: "var(--green)", label: "LIVE" },
    demo_fallback: {
      bg: "rgba(234, 179, 8, 0.15)",
      fg: "var(--yellow)",
      label: "DEMO",
    },
    llm_direct: {
      bg: "rgba(59, 130, 246, 0.15)",
      fg: "var(--accent)",
      label: "LLM DIRECT",
    },
  };
  const c = colors[source] ?? colors["live"];
  return (
    <span
      className="routing-badge"
      style={{ background: c!.bg, color: c!.fg }}
    >
      {c!.label}
    </span>
  );
}

function TimingBar({ timing }: { timing: RoutingInfo["timing"] }) {
  const total = timing.total_ms || 1;
  const networkMs = timing.network_ms ?? 0;
  const routingPct = (timing.routing_ms / total) * 100;
  const networkPct = (networkMs / total) * 100;
  const sqlPct = (timing.sql_total_ms / total) * 100;

  return (
    <div className="routing-timing">
      <div className="routing-timing-header">
        <span className="routing-timing-total">{formatMs(timing.total_ms)}</span>
        <span className="routing-timing-label">total</span>
      </div>
      <div className="routing-timing-bar">
        <div
          className="routing-timing-segment routing-timing-routing"
          style={{ width: `${routingPct}%` }}
          title={`LLM routing: ${formatMs(timing.routing_ms)}`}
        />
        {networkMs > 0 && (
          <div
            className="routing-timing-segment routing-timing-network"
            style={{ width: `${networkPct}%` }}
            title={`Network (MCP call): ${formatMs(networkMs)}`}
          />
        )}
        <div
          className="routing-timing-segment routing-timing-sql"
          style={{ width: `${sqlPct}%` }}
          title={`SQL execution: ${formatMs(timing.sql_total_ms)}`}
        />
      </div>
      <div className="routing-timing-legend">
        <span>
          <span className="routing-legend-dot" style={{ background: "var(--accent)" }} />
          Routing {formatMs(timing.routing_ms)}
        </span>
        {networkMs > 0 && (
          <span>
            <span className="routing-legend-dot" style={{ background: "var(--yellow)" }} />
            Network {formatMs(networkMs)}
          </span>
        )}
        <span>
          <span className="routing-legend-dot" style={{ background: "var(--green)" }} />
          SQL {formatMs(timing.sql_total_ms)}
        </span>
      </div>
    </div>
  );
}

function SqlQueryCard({ query, index }: { query: SqlQueryTrace; index: number }) {
  const [expanded, setExpanded] = useState(false);

  if (query.error) {
    return (
      <div className="routing-sql-card routing-sql-error">
        <div className="routing-sql-header">
          <span className="routing-sql-label">Query {index + 1} — ERROR</span>
          <span className="routing-sql-duration" style={{ color: "var(--red)" }}>
            {query.fallback_reason}
          </span>
        </div>
        <div className="routing-sql-error-msg">{query.error}</div>
      </div>
    );
  }

  return (
    <div className="routing-sql-card">
      <div className="routing-sql-header" onClick={() => setExpanded(!expanded)}>
        <div className="routing-sql-meta">
          <span className="routing-sql-rows">{query.row_count} rows</span>
          <span className="routing-sql-sep" />
          <span className="routing-sql-duration">{formatMs(query.duration_ms)}</span>
          <span className="routing-sql-sep" />
          <span className="routing-sql-wh" title={query.warehouse_id}>
            wh:{query.warehouse_id.slice(0, 8)}
          </span>
        </div>
        <span className="routing-sql-expand">{expanded ? "▼" : "▶"}</span>
      </div>

      {expanded && (
        <div className="routing-sql-detail">
          <div className="routing-sql-statement">{query.statement}</div>

          {query.parameters.length > 0 && (
            <div className="routing-sql-params">
              <span className="routing-sql-params-label">Parameters:</span>
              {query.parameters.map((p, i) => (
                <span key={i} className="routing-sql-param">
                  <span className="routing-sql-param-name">{p.name}</span>
                  <span className="routing-sql-param-eq">=</span>
                  <span className="routing-sql-param-value">{p.value}</span>
                </span>
              ))}
            </div>
          )}

          {query.columns.length > 0 && (
            <div className="routing-sql-schema">
              <span className="routing-sql-params-label">Schema:</span>
              <div className="routing-sql-columns">
                {query.columns.map((c, i) => (
                  <span key={i} className="routing-sql-column">
                    <span className="routing-sql-col-name">{c.name}</span>
                    <span className="routing-sql-col-type">{c.type}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RoutingCard({ routing, turnIndex }: { routing: RoutingInfo; turnIndex: number }) {
  const [showQueries, setShowQueries] = useState(false);

  return (
    <div className="routing-card">
      {/* Header: turn number + sub-agent + data source */}
      <div className="routing-card-header">
        <div className="routing-card-title">
          <span className="routing-card-turn">Turn {turnIndex + 1}</span>
          <span className="routing-card-arrow">→</span>
          <span className="routing-card-agent">{routing.sub_agent ?? "none"}</span>
        </div>
        <DataSourceBadge source={routing.data_source} />
      </div>

      {/* Routing decision */}
      <div className="routing-decision-row">
        <div className="routing-decision-model">
          <span className="routing-label">Model</span>
          <span className="routing-value">{routing.routing_decision.model}</span>
        </div>
        <div className="routing-decision-tool">
          <span className="routing-label">Tool</span>
          <span className="routing-value routing-value-mono">
            {routing.routing_decision.tool_selected ?? "—"}
          </span>
        </div>
      </div>

      {/* Agent endpoint (MCP target) */}
      {routing.agent_endpoint && (
        <div className="routing-endpoint">
          <span className="routing-label">Endpoint</span>
          <span className="routing-value routing-value-mono routing-value-url">
            {routing.agent_endpoint}
          </span>
        </div>
      )}

      {/* Keywords */}
      {routing.keywords_extracted.length > 0 && (
        <div className="routing-keywords">
          <span className="routing-label">Keywords</span>
          <div className="routing-keyword-list">
            {routing.keywords_extracted.map((kw, i) => (
              <span key={i} className="routing-keyword">{kw}</span>
            ))}
          </div>
        </div>
      )}

      {/* Tables accessed */}
      {routing.tables_accessed.length > 0 && (
        <div className="routing-tables">
          <span className="routing-label">Tables</span>
          <div className="routing-table-list">
            {routing.tables_accessed.map((t, i) => (
              <span key={i} className="routing-table">{t}</span>
            ))}
          </div>
        </div>
      )}

      {/* Timing breakdown */}
      {routing.timing && <TimingBar timing={routing.timing} />}

      {/* SQL queries (expandable) */}
      {routing.sql_queries.length > 0 && (
        <div className="routing-sql-section">
          <button
            className="routing-sql-toggle"
            onClick={() => setShowQueries(!showQueries)}
          >
            {showQueries ? "▼" : "▶"} {routing.sql_queries.length} SQL{" "}
            {routing.sql_queries.length === 1 ? "query" : "queries"}
          </button>
          {showQueries &&
            routing.sql_queries.map((q, i) => (
              <SqlQueryCard key={i} query={q} index={i} />
            ))}
        </div>
      )}
    </div>
  );
}

export function RoutingPanel({ traces }: Props) {
  const routingTraces = traces.filter((t) => t.routing);

  if (routingTraces.length === 0) {
    return (
      <div className="trace-empty">
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          Routing data will appear here as the supervisor routes queries to
          sub-agents.
        </p>
      </div>
    );
  }

  return (
    <div className="routing-panel">
      {routingTraces.map((trace) => (
        <RoutingCard
          key={trace.id}
          routing={trace.routing!}
          turnIndex={traces.indexOf(trace)}
        />
      ))}
    </div>
  );
}

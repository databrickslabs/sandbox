import { useGovernance } from "../../hooks/useGovernance";
import { useObservedData } from "../../hooks/useChatObservability";
import type { DeclaredResource } from "../../types/lineage";
import { Badge } from "../common/Badge";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";

interface Props {
  agentName: string;
}

function resourceDetail(r: DeclaredResource): string {
  switch (r.type) {
    case "uc_securable":
      return r.securable_full_name ?? "—";
    case "sql_warehouse":
      return r.id ?? "—";
    case "job":
      return r.id ?? "—";
    case "secret":
      return [r.scope, r.key].filter(Boolean).join("/") || "—";
    case "serving_endpoint":
      return (r.name_value as string) ?? r.name ?? "—";
    case "database":
      return [r.instance_name, r.database_name].filter(Boolean).join("/") || "—";
    case "genie_space":
      return r.id ?? "—";
    default:
      return "—";
  }
}

const TYPE_LABELS: Record<string, string> = {
  uc_securable: "UC Securable",
  sql_warehouse: "SQL Warehouse",
  job: "Job",
  secret: "Secret",
  serving_endpoint: "Serving Endpoint",
  database: "Database",
  genie_space: "Genie Space",
};

export function GovernanceTab({ agentName }: Props) {
  const { status, loading, error } = useGovernance(agentName);
  const observed = useObservedData(agentName);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <Spinner large /> Loading governance status...
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} />;
  }

  if (!status) {
    return (
      <div className="empty-state">
        <p>Could not retrieve governance information.</p>
      </div>
    );
  }

  const { declared_resources, connected_tables, connected_table_count } = status;

  return (
    <div>
      {/* App status */}
      <div className="section">
        <h3>App Status</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <Badge
            label={status.app_running ? "Running" : "Not Running"}
            variant={status.app_running ? "green" : "red"}
          />
          {status.app_name && (
            <code className="governance-path">{status.app_name}</code>
          )}
        </div>
      </div>

      {/* Declared resources */}
      <div className="section">
        <h3>Declared Resources ({declared_resources.length})</h3>
        {declared_resources.length > 0 ? (
          <table className="governance-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Detail</th>
                <th>Permission</th>
              </tr>
            </thead>
            <tbody>
              {declared_resources.map((r) => (
                <tr key={r.name}>
                  <td><code>{r.name}</code></td>
                  <td>
                    <Badge label={TYPE_LABELS[r.type] ?? r.type} variant="blue" />
                    {r.securable_type && (
                      <span style={{ marginLeft: "0.5rem", fontSize: "0.8rem", color: "var(--muted)" }}>
                        {r.securable_type}
                      </span>
                    )}
                  </td>
                  <td>
                    <code style={{ fontSize: "0.8rem" }}>{resourceDetail(r)}</code>
                  </td>
                  <td>
                    {r.permission ? (
                      <Badge label={r.permission} />
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: "var(--muted)", fontSize: "0.875rem" }}>
            No resources declared on this app. Add resources in your{" "}
            <code className="governance-path">agents.yaml</code> to declare UC tables,
            warehouses, and other dependencies.
          </p>
        )}
      </div>

      {/* Connected UC tables */}
      {connected_tables && connected_tables.length > 0 && (
        <div className="section">
          <h3>Connected UC Tables ({connected_table_count})</h3>
          <table className="governance-table">
            <thead>
              <tr>
                <th>Table</th>
                <th>Schema</th>
                <th>Relationship</th>
              </tr>
            </thead>
            <tbody>
              {connected_tables.map((tbl) => (
                <tr key={tbl.full_name}>
                  <td><code>{tbl.full_name}</code></td>
                  <td>{tbl.schema}</td>
                  <td>
                    <Badge label={tbl.relationship.replace("_", " ")} variant="blue" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* No connections message */}
      {declared_resources.length === 0 && (!connected_tables || connected_tables.length === 0) && !observed?.turnCount && (
        <div className="section">
          <h3>UC Asset Connections</h3>
          <p style={{ color: "var(--muted)", fontSize: "0.875rem" }}>
            No UC tables or functions connected to this agent. Start the dashboard
            with <code className="governance-path">--catalog your_catalog</code> to
            enable UC asset discovery, or chat with the agent to observe runtime connections.
          </p>
        </div>
      )}

      {/* Observed at runtime from chat interactions */}
      {observed && observed.turnCount > 0 && (
        <div className="section">
          <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            Observed at Runtime
            <Badge label={`${observed.turnCount} turn${observed.turnCount > 1 ? "s" : ""}`} variant="blue" />
          </h3>

          {observed.tables.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <h4 style={{ color: "var(--muted)", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                Tables Accessed
              </h4>
              <table className="governance-table">
                <thead>
                  <tr>
                    <th>Table</th>
                    <th>Relationship</th>
                  </tr>
                </thead>
                <tbody>
                  {observed.tables.map((t) => (
                    <tr key={t}>
                      <td><code>{t}</code></td>
                      <td><Badge label="observed reads" variant="green" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {observed.agents.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <h4 style={{ color: "var(--muted)", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                Sub-Agents Called
              </h4>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {observed.agents.map((a) => (
                  <Badge key={a} label={a} variant="green" />
                ))}
              </div>
            </div>
          )}

          {observed.sqlQueries.length > 0 && (
            <div>
              <h4 style={{ color: "var(--muted)", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                SQL Queries ({observed.sqlQueries.length})
              </h4>
              {observed.sqlQueries.map((q, i) => (
                <details key={i} style={{ marginBottom: "0.5rem" }}>
                  <summary style={{ color: "var(--muted)", fontSize: "0.8rem", cursor: "pointer" }}>
                    {q.row_count} rows · {q.duration_ms}ms · {q.warehouse_id?.slice(0, 8)}...
                  </summary>
                  <pre style={{
                    marginTop: "0.25rem",
                    padding: "0.5rem",
                    background: "#0d1117",
                    border: "1px solid var(--border)",
                    borderRadius: "4px",
                    fontSize: "0.75rem",
                    overflow: "auto",
                  }}>
                    {q.statement}
                  </pre>
                </details>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

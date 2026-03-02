import { useState } from "react";
import { useGovernance } from "../../hooks/useGovernance";
import { useAgents } from "../../hooks/useAgents";
import { registerAllAgents } from "../../api/governance";
import type { UCRegistrationResult } from "../../types/lineage";
import { Badge } from "../common/Badge";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";

interface Props {
  agentName: string;
}

export function GovernanceTab({ agentName }: Props) {
  const { status, loading, error, refetch } = useGovernance(agentName);
  const { agents } = useAgents();
  const [registering, setRegistering] = useState(false);
  const [regResult, setRegResult] = useState<UCRegistrationResult | null>(null);

  const handleRegisterAll = async () => {
    setRegistering(true);
    setRegResult(null);
    try {
      const result = await registerAllAgents();
      setRegResult(result);
      refetch();
    } catch (e) {
      setRegResult({
        registered: [],
        failed: [{ name: "all", error: e instanceof Error ? e.message : "Registration failed" }],
        total: 0,
        error: e instanceof Error ? e.message : "Registration failed",
      });
    } finally {
      setRegistering(false);
    }
  };

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

  const connectedTables = status.connected_tables;
  const tableCount = status.connected_table_count;

  return (
    <div>
      {/* Registration status */}
      <div className="section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>UC Registration</h3>
          {agents.length > 0 && (
            <button
              className="btn btn-outline btn-sm register-all-btn"
              onClick={handleRegisterAll}
              disabled={registering}
            >
              {registering ? <><span className="spinner" /> Registering...</> : "Register All in UC"}
            </button>
          )}
        </div>

        {/* Registration result banner */}
        {regResult && (
          <div className={`register-result-banner ${regResult.error ? "register-result-error" : regResult.failed.length > 0 ? "register-result-partial" : "register-result-success"}`}>
            {regResult.error ? (
              <span>{regResult.error}</span>
            ) : (
              <span>
                Registered {regResult.registered.length}/{regResult.total} agents
                {regResult.failed.length > 0 && (
                  <span className="register-failures">
                    {" — "}Failed: {regResult.failed.map((f) => `${f.name}: ${f.error}`).join(", ")}
                  </span>
                )}
              </span>
            )}
          </div>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <Badge
            label={status.registered ? "Registered" : "Not Registered"}
            variant={status.registered ? "green" : "blue"}
          />
          {status.registered && status.full_name && (
            <code className="governance-path">{status.full_name}</code>
          )}
        </div>

        {!status.registered && (
          <p style={{ color: "var(--muted)", fontSize: "0.875rem" }}>
            This agent is not registered in Unity Catalog. Register it to enable
            governance, permissions, and lineage tracking across the workspace.
          </p>
        )}
      </div>

      {/* Tags table */}
      {status.registered && Object.keys(status.tags).length > 0 && (
        <div className="section">
          <h3>UC Tags</h3>
          <table className="governance-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(status.tags).map(([key, value]) => (
                <tr key={key}>
                  <td>
                    <code>{key}</code>
                  </td>
                  <td>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Registration details */}
      {status.registered && (
        <div className="section">
          <h3>Details</h3>
          <div className="governance-details">
            <div className="governance-row">
              <span className="governance-label">Catalog</span>
              <span>{status.catalog ?? "—"}</span>
            </div>
            <div className="governance-row">
              <span className="governance-label">Schema</span>
              <span>{status.schema ?? "—"}</span>
            </div>
            <div className="governance-row">
              <span className="governance-label">Endpoint</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                {status.endpoint_url ?? "—"}
              </span>
            </div>
            {status.capabilities && (
              <div className="governance-row">
                <span className="governance-label">Capabilities</span>
                <span>
                  {status.capabilities.map((cap) => (
                    <Badge key={cap} label={cap} />
                  ))}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Connected UC tables */}
      {connectedTables && connectedTables.length > 0 && (
        <div className="section">
          <h3>Connected UC Tables ({tableCount})</h3>
          <table className="governance-table">
            <thead>
              <tr>
                <th>Table</th>
                <th>Schema</th>
                <th>Relationship</th>
              </tr>
            </thead>
            <tbody>
              {connectedTables.map((tbl) => (
                <tr key={tbl.full_name}>
                  <td>
                    <code>{tbl.full_name}</code>
                  </td>
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

      {/* No UC assets message */}
      {!status.registered && (!connectedTables || connectedTables.length === 0) && (
        <div className="section">
          <h3>UC Asset Connections</h3>
          <p style={{ color: "var(--muted)", fontSize: "0.875rem" }}>
            No UC tables or functions connected to this agent. Start the dashboard
            with <code className="governance-path">--catalog your_catalog</code> to
            enable UC asset discovery.
          </p>
        </div>
      )}
    </div>
  );
}

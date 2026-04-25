import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useLineage } from "../hooks/useLineage";
import { LineageGraphView } from "../components/lineage/LineageGraph";
import { Spinner } from "../components/common/Spinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import type { NodeType } from "../types/lineage";

const ALL_TYPES: NodeType[] = ["agent", "tool", "uc_function", "table", "model"];

const TYPE_LABELS: Record<NodeType, string> = {
  agent: "Agents",
  tool: "Tools",
  uc_function: "UC Functions",
  table: "Tables",
  model: "Models",
};

export function LineagePage() {
  const { graph, loading, error, refresh } = useLineage();
  const [hiddenTypes, setHiddenTypes] = useState<Set<NodeType>>(new Set());
  const navigate = useNavigate();

  const toggleType = useCallback((t: NodeType) => {
    setHiddenTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }, []);

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      if (nodeId.startsWith("agent:")) {
        const name = nodeId.replace("agent:", "");
        navigate(`/agent/${encodeURIComponent(name)}`);
      }
    },
    [navigate],
  );

  // Filter graph by hidden types
  const filteredGraph = graph
    ? {
        ...graph,
        nodes: graph.nodes.filter((n) => !hiddenTypes.has(n.node_type)),
        edges: graph.edges.filter((e) => {
          const srcHidden = graph.nodes.find((n) => n.id === e.source && hiddenTypes.has(n.node_type));
          const tgtHidden = graph.nodes.find((n) => n.id === e.target && hiddenTypes.has(n.node_type));
          return !srcHidden && !tgtHidden;
        }),
      }
    : null;

  return (
    <>
      <div className="detail-header">
        <h2>Workspace Lineage</h2>
        <p style={{ color: "var(--muted)" }}>
          Agent interconnections across the workspace
        </p>
      </div>

      <div className="lineage-toolbar">
        <div className="lineage-filters">
          {ALL_TYPES.map((t) => {
            const count = graph?.nodes.filter((n) => n.node_type === t).length ?? 0;
            if (count === 0) return null;
            return (
              <label key={t} className="lineage-filter-label">
                <input
                  type="checkbox"
                  checked={!hiddenTypes.has(t)}
                  onChange={() => toggleType(t)}
                />
                {TYPE_LABELS[t]} ({count})
              </label>
            );
          })}
        </div>
        <button className="btn btn-outline btn-sm" onClick={refresh} disabled={loading}>
          {loading ? <><span className="spinner" /> Scanning...</> : "Refresh"}
        </button>
      </div>

      {loading && !graph && (
        <div style={{ textAlign: "center", padding: "3rem" }}>
          <Spinner large /> Loading workspace lineage...
        </div>
      )}

      {error && <ErrorBanner message={error} />}

      {filteredGraph && filteredGraph.nodes.length > 0 && (
        <div style={{ marginTop: "1rem" }}>
          <LineageGraphView graph={filteredGraph} onNodeClick={handleNodeClick} />
        </div>
      )}

      {filteredGraph && filteredGraph.nodes.length === 0 && !loading && (
        <div className="empty-state">
          <p>No lineage data available. Scan for agents first.</p>
        </div>
      )}
    </>
  );
}

import { useLineage } from "../../hooks/useLineage";
import { LineageGraphView } from "../lineage/LineageGraph";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";

interface Props {
  agentName: string;
}

export function LineageTab({ agentName }: Props) {
  const { graph, loading, error, refresh } = useLineage(agentName);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <Spinner large /> Loading lineage...
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} />;
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="empty-state">
        <p>No lineage data available for this agent.</p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <span className="status-text">
          {graph.nodes.length} nodes, {graph.edges.length} edges
        </span>
        <button className="btn btn-outline btn-sm" onClick={refresh}>
          Refresh
        </button>
      </div>
      <LineageGraphView graph={graph} />
    </div>
  );
}

import type { Agent, AgentCard } from "../../types";
import { JsonViewer } from "../common/JsonViewer";
import { Spinner } from "../common/Spinner";
import { ErrorBanner } from "../common/ErrorBanner";

interface Props {
  agent: Agent;
  card: AgentCard | null;
  loading: boolean;
  error: string | null;
}

export function OverviewTab({ agent, card, loading, error }: Props) {
  return (
    <>
      <div className="section">
        <h3>Endpoint</h3>
        <code>{agent.endpoint_url}</code>
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: "2rem" }}>
          <Spinner large /> Loading agent card...
        </div>
      )}

      {error && <ErrorBanner message={error} />}

      {card && (
        <div className="section">
          <h3>Agent Card</h3>
          <pre>
            <JsonViewer data={card} />
          </pre>
        </div>
      )}
    </>
  );
}

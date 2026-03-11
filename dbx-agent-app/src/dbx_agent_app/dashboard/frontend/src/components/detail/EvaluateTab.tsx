import { useState } from "react";
import { useEvaluate } from "../../hooks/useEvaluate";
import type { EvalRun } from "../../hooks/useEvaluate";
import { Spinner } from "../common/Spinner";
import { Badge } from "../common/Badge";

interface Props {
  agentName: string;
}

function RunCard({ run }: { run: EvalRun }) {
  const [showRaw, setShowRaw] = useState(false);
  const userMsg = run.messages.find((m) => m.role === "user");

  return (
    <div className="eval-run">
      <div className="eval-run-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          {run.error ? (
            <Badge label="Error" variant="red" />
          ) : (
            <Badge label="Success" variant="green" />
          )}
          {run.latencyMs != null && (
            <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
              {run.latencyMs}ms
            </span>
          )}
        </div>
        <button
          className="btn btn-outline btn-sm"
          onClick={() => setShowRaw((v) => !v)}
        >
          {showRaw ? "Hide raw" : "Show raw"}
        </button>
      </div>

      <div className="eval-run-query">
        <strong>Input:</strong> {userMsg?.content ?? "—"}
      </div>

      {run.error ? (
        <div className="eval-run-error">{run.error}</div>
      ) : (
        <div className="eval-run-response">
          <strong>Response:</strong>
          <p style={{ whiteSpace: "pre-wrap", margin: "0.25rem 0 0" }}>
            {run.result?.response}
          </p>
        </div>
      )}

      {showRaw && run.result && (
        <pre className="eval-run-raw">
          {JSON.stringify(run.result.output, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function EvaluateTab({ agentName }: Props) {
  const { runs, loading, evaluate, clear } = useEvaluate(agentName);
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    evaluate([{ role: "user", content: input.trim() }]);
    setInput("");
  };

  return (
    <div>
      <div className="section">
        <h3>Evaluate Agent</h3>
        <p style={{ color: "var(--muted)", fontSize: "0.875rem", marginBottom: "1rem" }}>
          Send a test message through the eval bridge and inspect the structured response.
        </p>

        <form onSubmit={handleSubmit} className="eval-form">
          <textarea
            className="eval-input"
            placeholder="Type a test message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={3}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                handleSubmit(e);
              }
            }}
          />
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!input.trim() || loading}
            >
              {loading ? (
                <>
                  <Spinner /> Running...
                </>
              ) : (
                "Run Evaluation"
              )}
            </button>
            {runs.length > 0 && (
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={clear}
              >
                Clear results
              </button>
            )}
            <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
              Cmd+Enter to submit
            </span>
          </div>
        </form>
      </div>

      {runs.length > 0 && (
        <div className="section">
          <h3>Results ({runs.length})</h3>
          <div className="eval-runs">
            {runs.map((run) => (
              <RunCard key={run.id} run={run} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

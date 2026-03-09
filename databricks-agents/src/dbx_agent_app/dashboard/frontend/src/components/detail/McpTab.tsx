import { useState } from "react";
import { JsonViewer } from "../common/JsonViewer";
import { Spinner } from "../common/Spinner";
import type { JsonRpcResponse } from "../../types";

interface Props {
  agentName: string;
  lastResponse: JsonRpcResponse | null;
  sending: boolean;
  onSendRaw: (method: string, params: Record<string, unknown>) => Promise<void>;
}

const DEFAULT_PAYLOAD = JSON.stringify(
  { jsonrpc: "2.0", id: "1", method: "tools/list", params: {} },
  null,
  2,
);

export function McpTab({ agentName: _agentName, lastResponse, sending, onSendRaw }: Props) {
  const [input, setInput] = useState(DEFAULT_PAYLOAD);
  const [parseError, setParseError] = useState<string | null>(null);

  function setTemplate(method: string) {
    const payload = JSON.stringify(
      { jsonrpc: "2.0", id: "1", method, params: {} },
      null,
      2,
    );
    setInput(payload);
    setParseError(null);
  }

  async function handleSend() {
    setParseError(null);
    try {
      const parsed = JSON.parse(input);
      await onSendRaw(parsed.method, parsed.params ?? {});
    } catch (e) {
      setParseError(
        e instanceof SyntaxError ? "Invalid JSON" : String(e),
      );
    }
  }

  return (
    <div className="section">
      <h3>MCP Test Panel</h3>
      <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "0.75rem" }}>
        Send a JSON-RPC request to this agent's <code>/api/mcp</code> endpoint.
      </p>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
        <button className="btn btn-outline btn-sm" onClick={() => setTemplate("tools/list")}>
          tools/list
        </button>
        <button className="btn btn-outline btn-sm" onClick={() => setTemplate("tools/call")}>
          tools/call
        </button>
        <button className="btn btn-outline btn-sm" onClick={() => setTemplate("resources/list")}>
          resources/list
        </button>
      </div>

      <textarea
        rows={8}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        spellCheck={false}
      />

      {parseError && (
        <div style={{ color: "var(--red)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
          {parseError}
        </div>
      )}

      <button
        className="btn btn-primary"
        style={{ marginTop: "0.5rem" }}
        onClick={handleSend}
        disabled={sending}
      >
        {sending ? <><Spinner /> Sending...</> : "Send request"}
      </button>

      {lastResponse && (
        <div style={{ marginTop: "0.75rem" }}>
          <pre>
            <JsonViewer data={lastResponse} />
          </pre>
        </div>
      )}
    </div>
  );
}

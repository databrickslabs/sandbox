import { apiFetch } from "./client";

export interface ChatResponse {
  result: {
    messageId?: string;
    contextId?: string;
    role?: string;
    parts?: Array<{ text?: string; [key: string]: unknown }>;
    _trace?: {
      request_sent_at: string;
      response_received_at: string;
      latency_ms: number;
      protocol: "a2a" | "mcp_fallback";
      request_payload?: unknown;
      response_payload?: unknown;
      sub_events?: Array<{
        type: string;
        label: string;
        duration_ms: number;
        request?: unknown;
        response?: unknown;
      }>;
    };
    [key: string]: unknown;
  };
}

export function sendMessage(
  agentName: string,
  message: string,
  contextId?: string,
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>(
    `/api/agents/${encodeURIComponent(agentName)}/chat`,
    {
      method: "POST",
      body: JSON.stringify({ message, context_id: contextId }),
    },
  );
}

/**
 * Send a streaming chat message — yields SSE lines.
 * Falls back to non-streaming if /chat/stream returns an error.
 */
export async function* sendStreamingMessage(
  agentName: string,
  message: string,
): AsyncGenerator<string> {
  const response = await fetch(
    `/api/agents/${encodeURIComponent(agentName)}/chat/stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    },
  );

  if (!response.ok || !response.body) {
    throw new Error(`Stream failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        yield line.slice(6);
      }
    }
  }
}

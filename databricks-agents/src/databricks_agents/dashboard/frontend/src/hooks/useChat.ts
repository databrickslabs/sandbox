import { useState, useCallback, useRef, useEffect } from "react";
import type {
  ChatMessage,
  MessagePart,
  ToolCallEntry,
  TraceTurn,
  TraceEvent,
  Artifact,
  ArtifactType,
  ChatSession,
  SessionIndex,
} from "../types";
import { sendMessage } from "../api/chat";
import { observeTrace } from "../api/governance";
import { useSessionStorage } from "./useSessionStorage";

export interface UseChatResult {
  messages: ChatMessage[];
  toolCalls: ToolCallEntry[];
  traces: TraceTurn[];
  artifacts: Artifact[];
  sending: boolean;
  error: string | null;
  contextId: string | null;
  selectedTraceId: string | null;
  highlightedMessageId: string | null;
  selectTrace: (traceId: string | null) => void;
  send: (text: string) => Promise<void>;
  clear: () => void;
  // Session management
  sessions: SessionIndex;
  activeSession: ChatSession | null;
  createSession: (name?: string) => void;
  switchSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  renameSession: (sessionId: string, name: string) => void;
}

let msgCounter = 0;

function extractParts(
  result: Record<string, unknown>,
): { parts: MessagePart[]; toolCalls: ToolCallEntry[] } {
  const parts: MessagePart[] = [];
  const toolCalls: ToolCallEntry[] = [];
  const now = Date.now();

  const rawParts = (result.parts as Array<Record<string, unknown>>) ?? [];

  if (rawParts.length === 0 && typeof result.text === "string") {
    parts.push({ type: "text", text: result.text as string });
    return { parts, toolCalls };
  }

  for (const p of rawParts) {
    if (p.text) {
      parts.push({ type: "text", text: p.text as string });
    }
    if (p.toolCallId && p.toolName) {
      const entry: ToolCallEntry = {
        id: p.toolCallId as string,
        toolName: p.toolName as string,
        args: (p.args as Record<string, unknown>) ?? {},
        startTime: now,
        endTime: now,
        status: "success",
      };
      toolCalls.push(entry);
      parts.push({
        type: "tool-call",
        toolCallId: entry.id,
        toolName: entry.toolName,
        args: entry.args,
      });
    }
    if (p.toolCallId && p.result !== undefined && !p.toolName) {
      parts.push({
        type: "tool-result",
        toolCallId: p.toolCallId as string,
        result: p.result,
      });
    }
  }

  if (parts.length === 0) {
    parts.push({ type: "text", text: JSON.stringify(result, null, 2) });
  }

  return { parts, toolCalls };
}

function detectArtifactType(data: unknown): ArtifactType | null {
  if (data === null || data === undefined) return null;
  if (typeof data === "object" && !Array.isArray(data)) {
    const obj = data as Record<string, unknown>;
    if (typeof obj.image === "string" && (obj.image as string).startsWith("data:image")) {
      return "image";
    }
    if (typeof obj.url === "string") return "file";
    if (Array.isArray(obj.rows) || Array.isArray(obj.data)) return "table";
    return "json";
  }
  if (typeof data === "string" && data.length > 200) return "text";
  return null;
}

function extractArtifacts(
  toolCalls: ToolCallEntry[],
  parts: MessagePart[],
): Artifact[] {
  const artifacts: Artifact[] = [];

  // Check tool results from parts
  for (const part of parts) {
    if (part.type !== "tool-result") continue;
    const resultData = part.result;
    const artType = detectArtifactType(resultData);
    if (!artType) continue;

    const art: Artifact = {
      id: crypto.randomUUID(),
      type: artType,
      label: `Result from ${part.toolCallId}`,
      timestamp: Date.now(),
      sourceToolCallId: part.toolCallId,
      data: resultData,
    };

    if (artType === "image") {
      art.preview = (resultData as Record<string, unknown>).image as string;
    }
    if (artType === "file") {
      art.url = (resultData as Record<string, unknown>).url as string;
    }
    if (artType === "json") {
      art.sizeBytes = new Blob([JSON.stringify(resultData)]).size;
    }

    // Try to get a better label from the matching tool call
    const matchingTc = toolCalls.find((tc) => tc.id === part.toolCallId);
    if (matchingTc) {
      art.label = `${matchingTc.toolName} output`;
    }

    artifacts.push(art);
  }

  // Also check tool call results directly
  for (const tc of toolCalls) {
    if (tc.result === undefined) continue;
    // Skip if already captured via parts
    if (artifacts.some((a) => a.sourceToolCallId === tc.id)) continue;
    const artType = detectArtifactType(tc.result);
    if (!artType) continue;

    const art: Artifact = {
      id: crypto.randomUUID(),
      type: artType,
      label: `${tc.toolName} output`,
      timestamp: Date.now(),
      sourceToolCallId: tc.id,
      data: tc.result,
    };
    if (artType === "json") {
      art.sizeBytes = new Blob([JSON.stringify(tc.result)]).size;
    }
    artifacts.push(art);
  }

  return artifacts;
}

function buildTrace(
  userMsgId: string,
  agentMsgId: string,
  startTime: number,
  endTime: number,
  serverTrace?: Record<string, unknown>,
): TraceTurn {
  const events: TraceEvent[] = [];
  const protocol = (serverTrace?.protocol as string) === "mcp_fallback" ? "mcp_fallback" : "a2a";

  // Request event
  events.push({
    id: crypto.randomUUID(),
    type: protocol === "a2a" ? "a2a_request" : "mcp_tools_list",
    label: protocol === "a2a" ? "A2A request sent" : "MCP fallback started",
    timestamp: startTime,
  });

  // Sub-events from server trace
  if (serverTrace?.sub_events && Array.isArray(serverTrace.sub_events)) {
    for (const sub of serverTrace.sub_events as Array<Record<string, unknown>>) {
      events.push({
        id: crypto.randomUUID(),
        type: sub.type as TraceEvent["type"],
        label: sub.label as string,
        timestamp: startTime,
        durationMs: sub.duration_ms as number,
        payload: { request: sub.request, response: sub.response },
      });
    }
  }

  // Response event
  events.push({
    id: crypto.randomUUID(),
    type: protocol === "a2a" ? "a2a_response" : "mcp_tools_call",
    label: "Response received",
    timestamp: endTime,
    durationMs: endTime - startTime,
  });

  const turn: TraceTurn = {
    id: crypto.randomUUID(),
    userMessageId: userMsgId,
    agentMessageId: agentMsgId,
    startTime,
    endTime,
    latencyMs: endTime - startTime,
    events,
    protocol: protocol as "a2a" | "mcp_fallback",
    requestPayload: serverTrace?.request_payload,
    responsePayload: serverTrace?.response_payload,
  };

  if (serverTrace) {
    turn.serverTiming = {
      requestSentAt: serverTrace.request_sent_at as string,
      responseReceivedAt: serverTrace.response_received_at as string,
      latencyMs: serverTrace.latency_ms as number,
      subEvents: (serverTrace.sub_events ?? undefined) as NonNullable<TraceTurn["serverTiming"]>["subEvents"],
    };
  }

  return turn;
}

export function useChat(agentName: string): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEntry[]>([]);
  const [traces, setTraces] = useState<TraceTurn[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [highlightedMessageId, setHighlightedMessageId] = useState<string | null>(null);
  const contextIdRef = useRef<string | null>(null);
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sessionStorage = useSessionStorage(agentName);

  // Load active session on mount or when switching
  useEffect(() => {
    const session = sessionStorage.activeSession;
    if (session) {
      setMessages(session.messages);
      setToolCalls(session.toolCalls);
      setTraces(session.traces);
      contextIdRef.current = session.contextId;
    }
  }, [sessionStorage.activeSession?.id]);

  const selectTrace = useCallback((traceId: string | null) => {
    setSelectedTraceId(traceId);
    if (traceId) {
      // Find the trace and highlight its user message
      setTraces((prev) => {
        const trace = prev.find((t) => t.id === traceId);
        if (trace) {
          if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
          setHighlightedMessageId(trace.userMessageId);
          highlightTimerRef.current = setTimeout(() => {
            setHighlightedMessageId(null);
          }, 2000);
        }
        return prev;
      });
    }
  }, []);

  const saveCurrentSession = useCallback(
    (msgs: ChatMessage[], tcs: ToolCallEntry[], trs: TraceTurn[]) => {
      const session = sessionStorage.activeSession;
      if (!session) return;
      sessionStorage.saveSession({
        ...session,
        messages: msgs,
        toolCalls: tcs,
        traces: trs,
        contextId: contextIdRef.current,
      });
    },
    [sessionStorage.activeSession?.id],
  );

  const send = useCallback(
    async (text: string) => {
      // Auto-create session if none active
      if (!sessionStorage.activeSession) {
        sessionStorage.createSession();
      }

      const userMsg: ChatMessage = {
        id: `msg-${++msgCounter}`,
        role: "user",
        parts: [{ type: "text", text }],
        timestamp: Date.now(),
      };
      const sendStartTime = Date.now();

      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError(null);

      try {
        const resp = await sendMessage(
          agentName,
          text,
          contextIdRef.current ?? undefined,
        );

        const result = resp.result ?? ({} as Record<string, unknown>);
        if (result.contextId) {
          contextIdRef.current = result.contextId as string;
        }

        const { parts, toolCalls: newToolCalls } = extractParts(result);

        const agentMsg: ChatMessage = {
          id: `msg-${++msgCounter}`,
          role: "agent",
          parts,
          timestamp: Date.now(),
        };

        // Build trace from timing data
        const serverTrace = result._trace as Record<string, unknown> | undefined;
        const trace = buildTrace(
          userMsg.id,
          agentMsg.id,
          sendStartTime,
          Date.now(),
          serverTrace,
        );

        // Fire-and-forget: send trace to observe endpoint for runtime lineage
        if (serverTrace) {
          observeTrace(agentName, serverTrace);
        }

        // Extract artifacts from tool results
        const newArtifacts = extractArtifacts(newToolCalls, parts);

        setMessages((prev) => {
          const updated = [...prev, agentMsg];
          setToolCalls((prevTc) => {
            const updatedTc = [...prevTc, ...newToolCalls];
            setTraces((prevTr) => {
              const updatedTr = [...prevTr, trace];
              // Save session after state updates
              setTimeout(() => saveCurrentSession(updated, updatedTc, updatedTr), 0);
              return updatedTr;
            });
            return updatedTc;
          });
          return updated;
        });

        if (newArtifacts.length > 0) {
          setArtifacts((prev) => [...prev, ...newArtifacts]);
        }
      } catch (e) {
        const errTrace: TraceTurn = {
          id: crypto.randomUUID(),
          userMessageId: userMsg.id,
          startTime: sendStartTime,
          endTime: Date.now(),
          latencyMs: Date.now() - sendStartTime,
          events: [{
            id: crypto.randomUUID(),
            type: "error",
            label: e instanceof Error ? e.message : "Unknown error",
            timestamp: Date.now(),
          }],
          protocol: "a2a",
        };
        setTraces((prev) => [...prev, errTrace]);
        setError(e instanceof Error ? e.message : "Failed to send message");
      } finally {
        setSending(false);
      }
    },
    [agentName, sessionStorage.activeSession?.id],
  );

  const clear = useCallback(() => {
    setMessages([]);
    setToolCalls([]);
    setTraces([]);
    setArtifacts([]);
    setError(null);
    setSelectedTraceId(null);
    setHighlightedMessageId(null);
    contextIdRef.current = null;

    // Reset current session data
    const session = sessionStorage.activeSession;
    if (session) {
      sessionStorage.saveSession({
        ...session,
        messages: [],
        toolCalls: [],
        traces: [],
        contextId: null,
      });
    }
  }, [sessionStorage.activeSession?.id]);

  const handleCreateSession = useCallback((name?: string) => {
    // Save current before switching
    if (sessionStorage.activeSession && messages.length > 0) {
      saveCurrentSession(messages, toolCalls, traces);
    }
    sessionStorage.createSession(name);
    setMessages([]);
    setToolCalls([]);
    setTraces([]);
    setArtifacts([]);
    setError(null);
    setSelectedTraceId(null);
    contextIdRef.current = null;
  }, [sessionStorage.activeSession?.id, messages, toolCalls, traces]);

  const handleSwitchSession = useCallback((sessionId: string) => {
    // Save current before switching
    if (sessionStorage.activeSession && messages.length > 0) {
      saveCurrentSession(messages, toolCalls, traces);
    }
    sessionStorage.switchSession(sessionId);
    setArtifacts([]);
    setSelectedTraceId(null);
    setHighlightedMessageId(null);
    setError(null);
  }, [sessionStorage.activeSession?.id, messages, toolCalls, traces]);

  return {
    messages,
    toolCalls,
    traces,
    artifacts,
    sending,
    error,
    contextId: contextIdRef.current,
    selectedTraceId,
    highlightedMessageId,
    selectTrace,
    send,
    clear,
    sessions: sessionStorage.sessions,
    activeSession: sessionStorage.activeSession,
    createSession: handleCreateSession,
    switchSession: handleSwitchSession,
    deleteSession: sessionStorage.deleteSession,
    renameSession: sessionStorage.renameSession,
  };
}

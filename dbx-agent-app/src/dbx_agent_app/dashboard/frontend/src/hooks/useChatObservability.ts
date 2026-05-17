import {
  createContext,
  useContext,
  useState,
  useCallback,
  createElement,
  type ReactNode,
} from "react";
import type {
  TraceTurn,
  ToolCallEntry,
  ObservedRuntimeData,
  ToolInvocation,
} from "../types";

interface ChatObservabilityContextValue {
  getObserved: (agentName: string) => ObservedRuntimeData | null;
  publish: (
    agentName: string,
    trace: TraceTurn,
    toolCalls: ToolCallEntry[],
  ) => void;
}

const ChatObservabilityContext =
  createContext<ChatObservabilityContextValue | null>(null);

export function ChatObservabilityProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [store, setStore] = useState<Map<string, ObservedRuntimeData>>(
    new Map(),
  );

  const publish = useCallback(
    (agentName: string, trace: TraceTurn, toolCalls: ToolCallEntry[]) => {
      setStore((prev) => {
        const existing = prev.get(agentName) ?? {
          tables: [],
          agents: [],
          tools: [],
          sqlQueries: [],
          lastUpdatedAt: 0,
          turnCount: 0,
        };

        const newTables = new Set(existing.tables);
        if (trace.routing?.tables_accessed) {
          for (const t of trace.routing.tables_accessed) newTables.add(t);
        }

        const newAgents = new Set(existing.agents);
        if (trace.routing?.sub_agent) newAgents.add(trace.routing.sub_agent);

        const newInvocations: ToolInvocation[] = toolCalls.map((tc) => ({
          id: tc.id,
          toolName: tc.toolName,
          args: tc.args,
          result: tc.result,
          durationMs: tc.endTime ? tc.endTime - tc.startTime : undefined,
          timestamp: tc.startTime,
          turnId: trace.id,
          status: tc.status === "error" ? ("error" as const) : ("success" as const),
        }));

        const next = new Map(prev);
        next.set(agentName, {
          tables: Array.from(newTables),
          agents: Array.from(newAgents),
          tools: [...newInvocations, ...existing.tools].slice(0, 100),
          sqlQueries: [
            ...(trace.routing?.sql_queries ?? []),
            ...existing.sqlQueries,
          ].slice(0, 50),
          lastUpdatedAt: Date.now(),
          turnCount: existing.turnCount + 1,
        });
        return next;
      });
    },
    [],
  );

  const getObserved = useCallback(
    (agentName: string) => {
      return store.get(agentName) ?? null;
    },
    [store],
  );

  return createElement(
    ChatObservabilityContext.Provider,
    { value: { getObserved, publish } },
    children,
  );
}

export function useChatObservability(): ChatObservabilityContextValue {
  const ctx = useContext(ChatObservabilityContext);
  if (!ctx)
    throw new Error(
      "useChatObservability must be used inside ChatObservabilityProvider",
    );
  return ctx;
}

export function useObservedData(agentName: string): ObservedRuntimeData | null {
  const { getObserved } = useChatObservability();
  return getObserved(agentName);
}

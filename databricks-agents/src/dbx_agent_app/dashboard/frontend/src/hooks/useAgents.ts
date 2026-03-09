import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { createElement } from "react";
import type { Agent } from "../types";
import { fetchAgents, triggerScan } from "../api/agents";

interface AgentContextValue {
  agents: Agent[];
  loading: boolean;
  error: string | null;
  scan: () => Promise<void>;
  refresh: () => Promise<void>;
  lastScanTimestamp: number;
}

const AgentContext = createContext<AgentContextValue | null>(null);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastScanTimestamp, setLastScanTimestamp] = useState(0);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAgents();
      setAgents(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, []);

  const scan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await triggerScan();
      const data = await fetchAgents();
      setAgents(data);
      setLastScanTimestamp(Date.now());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return createElement(
    AgentContext.Provider,
    { value: { agents, loading, error, scan, refresh, lastScanTimestamp } },
    children,
  );
}

export function useAgents(): AgentContextValue {
  const ctx = useContext(AgentContext);
  if (!ctx) throw new Error("useAgents must be used within AgentProvider");
  return ctx;
}

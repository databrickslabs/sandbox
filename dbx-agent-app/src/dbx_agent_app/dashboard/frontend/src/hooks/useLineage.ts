import { useState, useEffect, useCallback } from "react";
import type { LineageGraph } from "../types/lineage";
import { fetchAgentLineage, fetchWorkspaceLineage } from "../api/governance";
import { useAgents } from "./useAgents";

interface UseLineageResult {
  graph: LineageGraph | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useLineage(agentName?: string): UseLineageResult {
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const { lastScanTimestamp } = useAgents();

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const fetcher = agentName
      ? fetchAgentLineage(agentName)
      : fetchWorkspaceLineage();

    fetcher
      .then((data) => {
        if (!cancelled) setGraph(data);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load lineage");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [agentName, tick, lastScanTimestamp]);

  return { graph, loading, error, refresh };
}

import { useState, useEffect, useCallback } from "react";
import type { GovernanceStatus } from "../types/lineage";
import { fetchAgentGovernance } from "../api/governance";
import { useAgents } from "./useAgents";

interface UseGovernanceResult {
  status: GovernanceStatus | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useGovernance(agentName: string): UseGovernanceResult {
  const [status, setStatus] = useState<GovernanceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const { lastScanTimestamp } = useAgents();

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAgentGovernance(agentName)
      .then((data) => {
        if (!cancelled) setStatus(data);
      })
      .catch((e) => {
        if (!cancelled)
          setError(
            e instanceof Error ? e.message : "Failed to load governance status",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [agentName, tick, lastScanTimestamp]);

  return { status, loading, error, refetch };
}

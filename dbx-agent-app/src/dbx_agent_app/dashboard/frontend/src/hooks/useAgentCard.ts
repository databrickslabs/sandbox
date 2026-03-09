import { useState, useEffect } from "react";
import type { AgentCard } from "../types";
import { fetchAgentCard } from "../api/agents";

interface UseAgentCardResult {
  card: AgentCard | null;
  loading: boolean;
  error: string | null;
}

export function useAgentCard(name: string): UseAgentCardResult {
  const [card, setCard] = useState<AgentCard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAgentCard(name)
      .then((data) => {
        if (!cancelled) setCard(data);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load card");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [name]);

  return { card, loading, error };
}

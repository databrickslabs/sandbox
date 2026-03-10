import { useState, useCallback } from "react";
import type { EvalResult } from "../types/lineage";
import { evaluateAgent } from "../api/governance";

export interface EvalRun {
  id: number;
  messages: Array<{ role: string; content: string }>;
  result: EvalResult | null;
  error: string | null;
  latencyMs: number | null;
}

interface UseEvaluateResult {
  runs: EvalRun[];
  loading: boolean;
  evaluate: (messages: Array<{ role: string; content: string }>) => Promise<void>;
  clear: () => void;
}

let nextId = 1;

export function useEvaluate(agentName: string): UseEvaluateResult {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(false);

  const evaluate = useCallback(
    async (messages: Array<{ role: string; content: string }>) => {
      const id = nextId++;
      setLoading(true);

      const start = performance.now();
      try {
        const result = await evaluateAgent(agentName, messages);
        const latencyMs = Math.round(performance.now() - start);
        setRuns((prev) => [
          { id, messages, result, error: null, latencyMs },
          ...prev,
        ]);
      } catch (e) {
        const latencyMs = Math.round(performance.now() - start);
        setRuns((prev) => [
          {
            id,
            messages,
            result: null,
            error: e instanceof Error ? e.message : "Evaluation failed",
            latencyMs,
          },
          ...prev,
        ]);
      } finally {
        setLoading(false);
      }
    },
    [agentName],
  );

  const clear = useCallback(() => setRuns([]), []);

  return { runs, loading, evaluate, clear };
}

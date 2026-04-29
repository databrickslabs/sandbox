import { useState, useEffect, useCallback } from "react";
import { api } from "../api";

const REFRESH_MS = 30 * 1000; // 30 seconds

interface Entry {
  player_name: string;
  mystery: string;
  score: number;
  root_cause_score: number;
  evidence_score: number;
  recommendation_score: number;
  submitted_at: string;
}

export default function Leaderboard() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.getLeaderboard();
      setEntries(data);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  const handleClear = useCallback(async () => {
    if (!confirm("Clear all scores from the leaderboard?")) return;
    setClearing(true);
    try {
      await api.clearScores();
      setEntries([]);
    } catch {}
    setClearing(false);
  }, []);

  if (loading) return <p className="text-muted text-center">Loading leaderboard...</p>;

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {entries.length === 0 ? (
        <p className="text-muted text-center" style={{ padding: "24px" }}>
          No scores yet.
        </p>
      ) : (
        <table className="leaderboard-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Detective</th>
              <th>Mystery</th>
              <th style={{ textAlign: "center" }}>Root Cause</th>
              <th style={{ textAlign: "center" }}>Evidence</th>
              <th style={{ textAlign: "center" }}>Rec.</th>
              <th style={{ textAlign: "right" }}>Total</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, idx) => (
              <tr key={`${entry.player_name}-${idx}`}>
                <td>{idx + 1}</td>
                <td>{entry.player_name}</td>
                <td style={{ fontSize: "0.85rem" }}>{entry.mystery}</td>
                <td style={{ textAlign: "center" }}>{entry.root_cause_score ?? 0}</td>
                <td style={{ textAlign: "center" }}>{entry.evidence_score ?? 0}</td>
                <td style={{ textAlign: "center" }}>{entry.recommendation_score ?? 0}</td>
                <td style={{ textAlign: "right", fontWeight: 600, color: "#d4a853" }}>{entry.score ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div style={{ padding: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p className="text-muted" style={{ margin: 0, fontSize: "0.8rem" }}>
          Refreshes every 30 seconds.
        </p>
        <button
          onClick={handleClear}
          disabled={clearing}
          style={{
            background: "transparent",
            border: "1px solid #666",
            color: "#999",
            padding: "4px 12px",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "0.8rem",
          }}
        >
          {clearing ? "Clearing..." : "Clear Scores"}
        </button>
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { api } from "../api";
import { Submission, EvidenceItem } from "../types";

interface Props {
  accountId: string;
  nickname: string;
  mystery: string;
}

export default function CaseFile({ accountId, nickname, mystery }: Props) {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.getLatestSubmission(accountId);
        if (!cancelled) setSubmission(data);
      } catch {}
      if (!cancelled) setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, [accountId]);

  if (loading) return <p className="text-muted text-center">Opening case file...</p>;

  if (!submission) {
    return (
      <div className="card text-center">
        <h2>Case File</h2>
        <p className="text-muted" style={{ fontStyle: "italic" }}>
          No evidence submitted yet. Return to the investigation and submit your findings.
        </p>
      </div>
    );
  }

  const evidence = submission.evidence || [];

  return (
    <div>
      <div className="card" style={{ borderLeft: "3px solid #d4a853" }}>
        <div style={{ textAlign: "center", marginBottom: 16 }}>
          <p className="divider">&#9830; &#9830; &#9830;</p>
          <h1 style={{ marginBottom: 4 }}>Case File</h1>
          <p className="text-muted" style={{ fontStyle: "italic" }}>
            Detective: <strong>{nickname}</strong>
          </p>
          <p className="text-muted" style={{ fontSize: "0.9rem" }}>
            Mystery: <strong style={{ color: "#d4a853" }}>{mystery}</strong>
          </p>
          <p className="divider" style={{ marginTop: 8 }}>&#9830; &#9830; &#9830;</p>
        </div>
      </div>

      {/* Evidence Board */}
      {evidence.length > 0 && (
        <div className="card">
          <h2>Collected Evidence</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {evidence.map((ev: EvidenceItem, idx: number) => (
              <div
                key={idx}
                style={{
                  background: "#1e1a30",
                  border: "1px solid #3a3250",
                  borderLeft: `3px solid ${idx < 5 ? "#d4a853" : "#4a3f35"}`,
                  borderRadius: 6,
                  padding: 14,
                }}
              >
                <div className="flex-row mb-8" style={{ justifyContent: "space-between" }}>
                  <span style={{ fontWeight: 600, fontSize: "0.85rem", color: "#d4a853" }}>
                    Clue #{idx + 1}
                  </span>
                  <span className="text-muted" style={{ fontSize: "0.75rem", textTransform: "uppercase" }}>
                    {ev.type}
                    {idx >= 5 && " (unscored)"}
                  </span>
                </div>
                {ev.type === "text" && (
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{ev.content}</p>
                )}
                {ev.type === "image" && ev.content && (
                  <img
                    src={ev.content}
                    alt={`Clue ${idx + 1}`}
                    style={{ maxWidth: "100%", maxHeight: 250, borderRadius: 4 }}
                  />
                )}
                {ev.type === "csv" && (
                  <pre style={{
                    margin: 0,
                    padding: 8,
                    background: "#1a1a2e",
                    borderRadius: 4,
                    fontSize: "0.8rem",
                    maxHeight: 200,
                    overflow: "auto",
                    color: "#c4b89a",
                  }}>
                    {ev.content}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deduction */}
      {submission.solution && (
        <div className="card">
          <h2>Your Deduction</h2>
          <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{submission.solution}</p>
        </div>
      )}

      {/* Recommendation */}
      {submission.recommendation && (
        <div className="card">
          <h2>Business Recommendation</h2>
          <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{submission.recommendation}</p>
        </div>
      )}

      {/* Score */}
      <div className="card text-center" style={{ borderLeft: "3px solid #d4a853" }}>
        <p className="text-muted" style={{ fontSize: "0.85rem" }}>Current Score</p>
        <p style={{ fontSize: "2rem", fontFamily: "'Playfair Display', Georgia, serif", color: "#d4a853", margin: 0 }}>
          {submission.score} <span style={{ fontSize: "1rem", color: "#8a7e6a" }}>/ 500</span>
        </p>
      </div>
    </div>
  );
}

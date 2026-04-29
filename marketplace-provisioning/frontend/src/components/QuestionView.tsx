import { useState, useEffect, useCallback } from "react";
import { api } from "../api";
import { EvidenceItem } from "../types";
import EvidenceField from "./EvidenceField";

const MAX_EVIDENCE = 10;
const DRAFT_KEY = "dd_draft";

const MYSTERY_BRIEFINGS: Record<string, string> = {
  "HR — The Talent Drain":
    "Voluntary turnover increased 34% in Q3. The CHRO needs to understand what's driving it before the board meeting.",
  "Marketing — The Budget Drain":
    "Digital ad spend increased 40% last quarter but net new customer acquisition is flat. The VP of Marketing needs to understand where the budget went.",
  "Operations — The Late Shipments":
    "Customer satisfaction scores dropped 18 points in Q2. The COO suspects a fulfillment issue, but aggregate on-time delivery rates appear normal.",
  "Financial Planning — The Budget Overrun":
    "Operating expenses came in 18% over budget in Q3, but department heads are reporting their individual teams finished on or under target. The CFO needs to reconcile the gap before the audit committee meeting.",
};

interface AnswerData {
  root_cause: string;
  sample_recommendation: string;
  query_path: string[];
}

interface Props {
  accountId: string;
  nickname: string;
  mystery: string;
  genieUrl: string;
}

export default function QuestionView({ accountId, nickname, mystery, genieUrl }: Props) {
  const [showRubric, setShowRubric] = useState(false);

  // Load draft from localStorage if available (keyed by mystery)
  const draftKey = `${DRAFT_KEY}_${mystery}`;
  const savedDraft = (() => {
    try {
      const raw = localStorage.getItem(draftKey);
      if (raw) return JSON.parse(raw);
    } catch {}
    return null;
  })();

  const [solution, setSolution] = useState(savedDraft?.solution || "");
  const [recommendation, setRecommendation] = useState(savedDraft?.recommendation || "");
  const [evidence, setEvidence] = useState<EvidenceItem[]>(
    savedDraft?.evidence?.length
      ? savedDraft.evidence
      : [
          { field_order: 1, type: "text", content: "" },
          { field_order: 2, type: "text", content: "" },
          { field_order: 3, type: "text", content: "" },
        ]
  );
  const [submitting, setSubmitting] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [lastScore, setLastScore] = useState<number | null>(null);
  const [rcScore, setRcScore] = useState<number | null>(null);
  const [evScore, setEvScore] = useState<number | null>(null);
  const [recScore, setRecScore] = useState<number | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [hasScored, setHasScored] = useState(false);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState<AnswerData | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);
  const [workspaceHost, setWorkspaceHost] = useState("");

  // Auto-save draft to localStorage on every change (keyed by mystery)
  useEffect(() => {
    localStorage.setItem(
      draftKey,
      JSON.stringify({ solution, recommendation, evidence })
    );
  }, [draftKey, solution, recommendation, evidence]);

  // Load latest submission on mount (for resubmit flow)
  useEffect(() => {
    api.getLatestSubmission(accountId).then((sub) => {
      if (sub) {
        if (!solution && !recommendation) {
          setSolution(sub.solution || "");
          setRecommendation(sub.recommendation || "");
          if (sub.evidence?.length) {
            setEvidence(
              sub.evidence.map((e: any) => ({
                field_order: e.field_order,
                type: e.type,
                content: e.content,
              }))
            );
          }
        }
        setHasSubmitted(true);
        setLastScore(sub.score);
        setRcScore(sub.root_cause_score ?? null);
        setEvScore(sub.evidence_score ?? null);
        setRecScore(sub.recommendation_score ?? null);
        if (sub.root_cause_score > 0 || sub.recommendation_score > 0) {
          setHasScored(true);
        }
      }
    }).catch(() => {});
  }, [accountId]);

  // Fetch workspace host for leaderboard form
  useEffect(() => {
    api.getConfig().then((cfg) => setWorkspaceHost(cfg.workspace_host)).catch(() => {});
  }, []);

  function addEvidence() {
    if (evidence.length >= MAX_EVIDENCE) return;
    setEvidence([
      ...evidence,
      { field_order: evidence.length + 1, type: "text", content: "" },
    ]);
  }

  function updateEvidence(idx: number, updated: EvidenceItem) {
    const next = [...evidence];
    next[idx] = { ...updated, field_order: idx + 1 };
    setEvidence(next);
  }

  function removeEvidence(idx: number) {
    const next = evidence.filter((_, i) => i !== idx).map((e, i) => ({
      ...e,
      field_order: i + 1,
    }));
    setEvidence(next);
  }

  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    setMessage("");
    try {
      const result = await api.submitAnswer({
        account_id: accountId,
        solution,
        recommendation,
        evidence: evidence.map((e) => ({
          field_order: e.field_order,
          type: e.type,
          content: e.content,
        })),
      });
      setLastScore(result.score);
      setRcScore(result.root_cause_score);
      setEvScore(result.evidence_score);
      setRecScore(result.recommendation_score);
      setHasSubmitted(true);
      setHasScored(true);
      setMessage("Scored!");
    } catch (err: any) {
      setMessage(err.message || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }, [accountId, solution, recommendation, evidence]);

  const handleScore = useCallback(async () => {
    setScoring(true);
    setMessage("");
    try {
      const result = await api.scoreMySubmission(accountId);
      setLastScore(result.score);
      setRcScore(result.root_cause_score);
      setEvScore(result.evidence_score);
      setRecScore(result.recommendation_score);
      setHasScored(true);
      setMessage("Scored!");
    } catch (err: any) {
      setMessage(err.message || "Scoring failed");
    } finally {
      setScoring(false);
    }
  }, [accountId]);

  const handleRevealAnswer = useCallback(async () => {
    try {
      const data = await api.getAnswer(mystery);
      setAnswer(data);
      setShowAnswer(true);
    } catch {}
  }, [mystery]);

  function buildFormUrl(score: number) {
    const base = "https://docs.google.com/forms/d/e/1FAIpQLSeGD-4oP9__ssCtqNSaD-Us2NfaXDWL4siIimDoKuwtBlFCSQ/viewform";
    const params = new URLSearchParams({
      "usp": "pp_url",
      "entry.38613187": nickname,
      "entry.444755536": String(score),
      "entry.1289628757": workspaceHost,
    });
    return `${base}?${params.toString()}`;
  }

  const hasScreenshot = evidence.some((e) =>
    e.type === "image" && e.filename && /screenshot/i.test(e.filename)
  );

  return (
    <div>
      <div className="flex-row mb-16" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <span className="text-muted">Playing as <strong>{nickname}</strong></span>
        <button
          className="btn-secondary btn-small"
          onClick={() => setShowRubric(true)}
          style={{ fontSize: "0.8rem", padding: "4px 12px" }}
        >
          Scoring Rubric
        </button>
      </div>

      {/* Scoring Rubric Modal */}
      {showRubric && (
        <div
          style={{
            position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
            background: "rgba(0,0,0,0.7)", display: "flex",
            alignItems: "center", justifyContent: "center", zIndex: 1000,
          }}
          onClick={() => setShowRubric(false)}
        >
          <div
            style={{
              background: "#1a1a2e", border: "1px solid #d4a853", borderRadius: 12,
              padding: 24, maxWidth: 420, width: "90%",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex-row mb-16" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ margin: 0, color: "#d4a853" }}>Scoring Rubric</h2>
              <button
                onClick={() => setShowRubric(false)}
                style={{ background: "none", border: "none", color: "#8a7e6a", fontSize: "1.2rem", cursor: "pointer" }}
              >
                x
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #3a3250" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>Clues & Evidence</div>
                  <div className="text-muted" style={{ fontSize: "0.8rem" }}>+30 pts per piece, first 5 count</div>
                </div>
                <span style={{ color: "#d4a853", fontWeight: 600, whiteSpace: "nowrap" }}>up to 150 pts</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #3a3250" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>Root Cause Deduction</div>
                  <div className="text-muted" style={{ fontSize: "0.8rem" }}>AI-judged match to correct answer</div>
                </div>
                <span style={{ color: "#d4a853", fontWeight: 600, whiteSpace: "nowrap" }}>up to 100 pts</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #3a3250" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>Business Recommendation</div>
                  <div className="text-muted" style={{ fontSize: "0.8rem" }}>Relevance, actionability, business value</div>
                </div>
                <span style={{ color: "#d4a853", fontWeight: 600, whiteSpace: "nowrap" }}>up to 250 pts</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", fontWeight: 700 }}>
                <span>Maximum Total</span>
                <span style={{ color: "#d4a853" }}>500 pts</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mb-16" style={{ textAlign: "center" }}>
        <span className="text-muted" style={{ fontSize: "0.9rem" }}>
          Mystery: <strong style={{ color: "#d4a853" }}>{mystery}</strong>
        </span>
      </div>

      {/* Open Genie Space button */}
      {genieUrl && (
        <div className="card text-center" style={{ borderLeft: "3px solid #6abf7b", padding: "16px 24px" }}>
          <a
            href={genieUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-genie"
          >
            Open Genie Space
          </a>
          <p className="text-muted" style={{ fontSize: "0.8rem", marginTop: 8 }}>
            Opens in a new tab. Ask questions to investigate the data.
          </p>
        </div>
      )}

      <div className="card card-instructions">
        <h2>Your Briefing</h2>
        <p style={{ fontSize: "1.05rem", lineHeight: 1.6 }}>
          {MYSTERY_BRIEFINGS[mystery] || "Investigate the data to uncover what went wrong."}
        </p>
        <p className="text-muted" style={{ fontStyle: "italic", fontSize: "0.85rem", marginTop: 12 }}>
          Ask questions in your Genie space to discover the root cause. Copy text or
          visualizations into the supporting evidence. Finally, draft your business
          recommendation. You can score as many times as you like.
        </p>
      </div>

      {/* 1. Clues & Evidence */}
      <div className="card">
        <div className="flex-row mb-8" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
          <h2 style={{ marginBottom: 0 }}>Clues &amp; Evidence</h2>
          <span style={{ fontSize: "0.85rem" }}>
            <span className="text-muted">{evidence.length}/{MAX_EVIDENCE}</span>
            {evScore !== null && (
              <span style={{ color: "#d4a853", marginLeft: 12 }}>{evScore}/150</span>
            )}
          </span>
        </div>
        <p className="text-muted mb-16" style={{ fontSize: "0.85rem" }}>
          First 5 pieces of evidence count toward your score.
        </p>

        {hasScreenshot && (
          <div style={{
            background: "#2a1a1a", border: "1px solid #c0392b", borderRadius: 6,
            padding: "10px 14px", marginBottom: 16, fontSize: "0.85rem", color: "#e74c3c",
          }}>
            It looks like you uploaded a screenshot. For better evidence, go back to your
            Genie space and <strong>download</strong> the chart or table directly instead of
            screenshotting it.
          </div>
        )}

        {evidence.map((item, idx) => (
          <EvidenceField
            key={idx}
            index={idx}
            item={item}
            onChange={(updated) => updateEvidence(idx, updated)}
            onRemove={() => removeEvidence(idx)}
            canRemove={evidence.length > 1}
          />
        ))}

        {evidence.length < MAX_EVIDENCE && (
          <button type="button" className="btn-secondary mt-8" onClick={addEvidence}>
            + Add Evidence
          </button>
        )}
      </div>

      {/* 2. Root Cause Deduction */}
      <div className="card">
        <div className="flex-row mb-8" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
          <h2 style={{ marginBottom: 0 }}>Your Deduction</h2>
          {rcScore !== null && (
            <span style={{ color: "#d4a853", fontSize: "0.85rem" }}>{rcScore}/100</span>
          )}
        </div>
        <textarea
          placeholder="State your theory..."
          value={solution}
          onChange={(e) => setSolution(e.target.value)}
          rows={3}
        />
      </div>

      {/* 3. Business Recommendation */}
      <div className="card">
        <div className="flex-row mb-8" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
          <h2 style={{ marginBottom: 0 }}>Business Recommendation</h2>
          {recScore !== null && (
            <span style={{ color: "#d4a853", fontSize: "0.85rem" }}>{recScore}/250</span>
          )}
        </div>
        <textarea
          placeholder="What course of action do you recommend?"
          value={recommendation}
          onChange={(e) => setRecommendation(e.target.value)}
          rows={3}
        />
      </div>

      {/* Action buttons */}
      <div className="mt-16" style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
        <button
          className="btn-primary"
          style={{ padding: "12px 40px", fontSize: "1.1rem" }}
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? "Scoring..." : "Score My Submission"}
        </button>

        {lastScore !== null && (
          <div className="mt-8" style={{ textAlign: "center" }}>
            <p className="text-muted" style={{ fontSize: "0.85rem", marginBottom: 4 }}>Current Score</p>
            <p style={{ fontSize: "2.2rem", fontFamily: "'Playfair Display', Georgia, serif", color: "#d4a853", margin: 0 }}>
              {lastScore} <span style={{ fontSize: "1rem", color: "#8a7e6a" }}>/ 500</span>
            </p>
            <a
              href={buildFormUrl(lastScore)}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-genie"
              style={{ display: "inline-block", marginTop: 12, fontSize: "0.9rem", padding: "8px 24px" }}
            >
              Submit to Leaderboard
            </a>
          </div>
        )}
        {message && (
          <p className={`mt-8 ${message.includes("fail") ? "text-error" : "text-success"}`}>
            {message}
          </p>
        )}
      </div>

      {/* Show Answer button */}
      {!showAnswer && (
        <div className="mt-16" style={{ textAlign: "center" }}>
          <button
            className="btn-secondary"
            style={{ padding: "10px 32px", opacity: 0.7 }}
            onClick={handleRevealAnswer}
          >
            Show Answer
          </button>
        </div>
      )}

      {/* Case Closed — appears AFTER clicking Show Answer */}
      {showAnswer && answer && (
        <div style={{ marginTop: 24 }}>
          <div className="card" style={{ borderLeft: "3px solid #6abf7b", background: "linear-gradient(145deg, #1a2a1e, #1a1a2e)" }}>
            <h2 style={{ color: "#6abf7b" }}>Case Closed — The Answer</h2>

            <div style={{ marginBottom: 20 }}>
              <label style={{ color: "#6abf7b", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Correct Root Cause
              </label>
              <p style={{ lineHeight: 1.7, marginTop: 4 }}>{answer.root_cause}</p>
            </div>

            {answer.sample_recommendation && (
              <div style={{ marginBottom: 20 }}>
                <label style={{ color: "#6abf7b", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Sample Business Recommendation
                </label>
                <p style={{ lineHeight: 1.7, marginTop: 4 }}>{answer.sample_recommendation}</p>
              </div>
            )}

            {answer.query_path.length > 0 && (
              <div>
                <label style={{ color: "#6abf7b", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Query Path to the Answer
                </label>
                <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 10 }}>
                  {answer.query_path.map((step, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        gap: 12,
                        alignItems: "flex-start",
                        padding: "10px 14px",
                        background: "#1e1a30",
                        border: "1px solid #3a3250",
                        borderRadius: 6,
                      }}
                    >
                      <span style={{
                        flexShrink: 0,
                        width: 28,
                        height: 28,
                        borderRadius: "50%",
                        background: "linear-gradient(135deg, #8b1a1a, #6b0f0f)",
                        color: "#f0e6d3",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        fontFamily: "'Playfair Display', Georgia, serif",
                      }}>
                        {idx + 1}
                      </span>
                      <p style={{ margin: 0, lineHeight: 1.6, fontSize: "0.92rem" }}>{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {lastScore !== null && (
            <div className="card text-center" style={{ borderLeft: "3px solid #d4a853" }}>
              <p className="text-muted" style={{ fontSize: "0.85rem" }}>Your Final Score</p>
              <p style={{ fontSize: "2rem", fontFamily: "'Playfair Display', Georgia, serif", color: "#d4a853", margin: 0 }}>
                {lastScore} <span style={{ fontSize: "1rem", color: "#8a7e6a" }}>/ 500</span>
              </p>
              <a
                href={buildFormUrl(lastScore)}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-genie"
                style={{ display: "inline-block", marginTop: 12, fontSize: "0.9rem", padding: "8px 24px" }}
              >
                Submit to Leaderboard
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

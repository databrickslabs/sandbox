import { useState } from "react";
import { api } from "../api";
import { containsProfanity } from "../profanityFilter";

const MYSTERIES = [
  "HR — The Talent Drain",
  "Marketing — The Budget Drain",
  "Operations — The Late Shipments",
  "Financial Planning — The Budget Overrun",
];

interface Props {
  onCreated: (
    id: string,
    nickname: string,
    mystery: string,
    provisioningStatus: string,
    genieUrl: string | null
  ) => void;
  existingNickname?: string;
}

export default function NicknameEntry({ onCreated, existingNickname }: Props) {
  const [nickname, setNickname] = useState(existingNickname || "");
  const [mystery, setMystery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!nickname.trim() || !mystery) return;
    if (containsProfanity(nickname)) {
      setError("That alias contains inappropriate language. Please choose another.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const acct = await api.createAccount(nickname.trim(), mystery);
      onCreated(acct.id, acct.nickname, acct.mystery, acct.provisioning_status, acct.genie_url);
    } catch (err: any) {
      setError(err.message || "Failed to create account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card text-center" style={{ marginTop: "12vh" }}>
      <p className="divider" style={{ marginBottom: 12 }}>&#9830; &#9830; &#9830;</p>
      <h1>Data Detective</h1>
      <p className="text-muted mb-16" style={{ fontStyle: "italic" }}>
        {existingNickname
          ? `Welcome back, ${existingNickname}. Pick your next case.`
          : "Every great detective needs a name. What shall we call you?"}
      </p>
      <form onSubmit={handleSubmit}>
        {!existingNickname && (
          <input
            type="text"
            placeholder="Enter your alias..."
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            maxLength={50}
            autoFocus
          />
        )}
        <div className="mt-16" style={{ textAlign: "left" }}>
          <label style={{ display: "block", marginBottom: 8, fontWeight: 600 }}>
            Choose Your Mystery
          </label>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {MYSTERIES.map((m) => (
              <label
                key={m}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "10px 14px",
                  background: mystery === m ? "#2a2445" : "#1e1a30",
                  border: mystery === m ? "1px solid #d4a853" : "1px solid #3a3250",
                  borderRadius: 6,
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                <input
                  type="radio"
                  name="mystery"
                  value={m}
                  checked={mystery === m}
                  onChange={() => setMystery(m)}
                  style={{ accentColor: "#d4a853" }}
                />
                <span>{m}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="mt-16">
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !nickname.trim() || !mystery}
          >
            {loading ? "Opening the case file..." : "Enter the Study"}
          </button>
        </div>
        {error && <p className="text-error mt-8">{error}</p>}
      </form>
      <p className="divider" style={{ marginTop: 16 }}>&#9830; &#9830; &#9830;</p>
    </div>
  );
}

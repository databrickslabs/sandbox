import { useState, useRef, useEffect } from "react";
import type { SessionIndex } from "../../types";

interface Props {
  sessions: SessionIndex;
  onCreateSession: (name?: string) => void;
  onSwitchSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, name: string) => void;
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

export function SessionBar({
  sessions,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
  onRenameSession,
}: Props) {
  const [open, setOpen] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const active = sessions.sessions.find((s) => s.id === sessions.activeSessionId);

  // Close dropdown on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
        setRenamingId(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Focus rename input
  useEffect(() => {
    if (renamingId) renameInputRef.current?.focus();
  }, [renamingId]);

  const handleRenameSubmit = (id: string) => {
    if (renameValue.trim()) {
      onRenameSession(id, renameValue.trim());
    }
    setRenamingId(null);
  };

  return (
    <div className="session-bar" ref={dropdownRef}>
      <button className="session-bar-toggle" onClick={() => setOpen(!open)}>
        <span className="session-bar-name">
          {active?.name ?? "No session"}
        </span>
        {active && (
          <span className="session-bar-count">
            {active.messageCount} msgs
          </span>
        )}
        <span className="session-bar-chevron">{open ? "▲" : "▼"}</span>
      </button>

      <button
        className="btn btn-outline btn-sm"
        onClick={() => { onCreateSession(); setOpen(false); }}
        style={{ marginLeft: "0.5rem" }}
      >
        + New
      </button>

      {open && (
        <div className="session-dropdown">
          {sessions.sessions.length === 0 ? (
            <div className="session-dropdown-empty">No sessions yet</div>
          ) : (
            sessions.sessions.map((s) => (
              <div
                key={s.id}
                className={`session-dropdown-item ${s.id === sessions.activeSessionId ? "active" : ""}`}
              >
                {renamingId === s.id ? (
                  <input
                    ref={renameInputRef}
                    className="session-rename-input"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => handleRenameSubmit(s.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRenameSubmit(s.id);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                  />
                ) : (
                  <div
                    className="session-dropdown-info"
                    onClick={() => { onSwitchSession(s.id); setOpen(false); }}
                  >
                    <span className="session-dropdown-name">{s.name}</span>
                    <span className="session-dropdown-meta">
                      {s.messageCount} msgs · {relativeTime(s.updatedAt)}
                    </span>
                  </div>
                )}
                <div className="session-dropdown-actions">
                  <button
                    className="session-action-btn"
                    title="Rename"
                    onClick={(e) => {
                      e.stopPropagation();
                      setRenamingId(s.id);
                      setRenameValue(s.name);
                    }}
                  >
                    ✎
                  </button>
                  <button
                    className="session-action-btn session-action-delete"
                    title="Delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(s.id);
                    }}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

import { useState, useCallback, useRef } from "react";
import type { ChatSession, SessionIndex, SessionMeta } from "../types";

const MAX_SESSIONS = 10;
const MAX_MESSAGES = 100;

function indexKey(agentName: string) {
  return `dashboard:session-index:${agentName}`;
}
function dataKey(agentName: string, sessionId: string) {
  return `dashboard:session:${agentName}:${sessionId}`;
}

function loadIndex(agentName: string): SessionIndex {
  try {
    const raw = localStorage.getItem(indexKey(agentName));
    if (raw) return JSON.parse(raw);
  } catch { /* corrupt data */ }
  return { activeSessionId: null, sessions: [] };
}

function saveIndex(agentName: string, index: SessionIndex) {
  localStorage.setItem(indexKey(agentName), JSON.stringify(index));
}

function loadSession(agentName: string, sessionId: string): ChatSession | null {
  try {
    const raw = localStorage.getItem(dataKey(agentName, sessionId));
    if (raw) return JSON.parse(raw);
  } catch { /* corrupt data */ }
  return null;
}

function persistSession(agentName: string, session: ChatSession) {
  const trimmed = {
    ...session,
    messages: session.messages.slice(-MAX_MESSAGES),
  };
  localStorage.setItem(dataKey(agentName, session.id), JSON.stringify(trimmed));
}

function removeSession(agentName: string, sessionId: string) {
  localStorage.removeItem(dataKey(agentName, sessionId));
}

function makeSession(name?: string): ChatSession {
  const id = crypto.randomUUID();
  const now = Date.now();
  return {
    id,
    name: name ?? `Session ${new Date(now).toLocaleTimeString()}`,
    messages: [],
    toolCalls: [],
    traces: [],
    contextId: null,
    createdAt: now,
    updatedAt: now,
  };
}

export interface UseSessionStorageResult {
  sessions: SessionIndex;
  activeSession: ChatSession | null;
  createSession: (name?: string) => ChatSession;
  switchSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  renameSession: (sessionId: string, name: string) => void;
  saveSession: (session: ChatSession) => void;
}

export function useSessionStorage(agentName: string): UseSessionStorageResult {
  const [sessions, setSessions] = useState<SessionIndex>(() => loadIndex(agentName));
  const [activeSession, setActiveSession] = useState<ChatSession | null>(() => {
    const idx = loadIndex(agentName);
    if (idx.activeSessionId) {
      return loadSession(agentName, idx.activeSessionId);
    }
    return null;
  });
  const agentRef = useRef(agentName);
  agentRef.current = agentName;

  const createSession = useCallback((name?: string): ChatSession => {
    const session = makeSession(name);
    const agent = agentRef.current;

    setSessions((prev) => {
      let updated = [...prev.sessions];
      // Prune oldest if at limit
      while (updated.length >= MAX_SESSIONS) {
        const oldest = updated.reduce((a, b) => (a.updatedAt < b.updatedAt ? a : b));
        removeSession(agent, oldest.id);
        updated = updated.filter((s) => s.id !== oldest.id);
      }
      const meta: SessionMeta = {
        id: session.id,
        name: session.name,
        createdAt: session.createdAt,
        updatedAt: session.updatedAt,
        messageCount: 0,
      };
      const newIndex: SessionIndex = {
        activeSessionId: session.id,
        sessions: [meta, ...updated],
      };
      saveIndex(agent, newIndex);
      return newIndex;
    });

    persistSession(agent, session);
    setActiveSession(session);
    return session;
  }, []);

  const switchSession = useCallback((sessionId: string) => {
    const agent = agentRef.current;
    const session = loadSession(agent, sessionId);
    if (!session) return;

    setSessions((prev) => {
      const newIndex = { ...prev, activeSessionId: sessionId };
      saveIndex(agent, newIndex);
      return newIndex;
    });
    setActiveSession(session);
  }, []);

  const deleteSession = useCallback((sessionId: string) => {
    const agent = agentRef.current;
    removeSession(agent, sessionId);

    setSessions((prev) => {
      const filtered = prev.sessions.filter((s) => s.id !== sessionId);
      const newActiveId = prev.activeSessionId === sessionId
        ? (filtered[0]?.id ?? null)
        : prev.activeSessionId;
      const newIndex: SessionIndex = { activeSessionId: newActiveId, sessions: filtered };
      saveIndex(agent, newIndex);

      if (newActiveId && newActiveId !== sessionId) {
        setActiveSession(loadSession(agent, newActiveId));
      } else {
        setActiveSession(null);
      }
      return newIndex;
    });
  }, []);

  const renameSession = useCallback((sessionId: string, name: string) => {
    const agent = agentRef.current;

    setSessions((prev) => {
      const updated = prev.sessions.map((s) =>
        s.id === sessionId ? { ...s, name } : s,
      );
      const newIndex = { ...prev, sessions: updated };
      saveIndex(agent, newIndex);
      return newIndex;
    });

    setActiveSession((prev) => {
      if (prev && prev.id === sessionId) {
        const renamed = { ...prev, name };
        persistSession(agent, renamed);
        return renamed;
      }
      return prev;
    });
  }, []);

  const saveSessionCb = useCallback((session: ChatSession) => {
    const agent = agentRef.current;
    const updated = { ...session, updatedAt: Date.now() };
    persistSession(agent, updated);

    setSessions((prev) => {
      const updatedSessions = prev.sessions.map((s) =>
        s.id === session.id
          ? { ...s, updatedAt: updated.updatedAt, messageCount: updated.messages.length }
          : s,
      );
      const newIndex = { ...prev, sessions: updatedSessions };
      saveIndex(agent, newIndex);
      return newIndex;
    });

    setActiveSession(updated);
  }, []);

  return {
    sessions,
    activeSession,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    saveSession: saveSessionCb,
  };
}

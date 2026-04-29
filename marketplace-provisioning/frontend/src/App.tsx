import { useState, useEffect, useCallback } from "react";
import { api } from "./api";
import NicknameEntry from "./components/NicknameEntry";
import ProvisioningStatus from "./components/ProvisioningStatus";
import QuestionView from "./components/QuestionView";
import CaseFile from "./components/CaseFile";
type Page = "nickname" | "provisioning" | "question" | "casefile";

const SESSION_KEY = "dd_session";

interface Session {
  accountId: string;
  nickname: string;
  mystery: string;
  genieUrl: string;
}

function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed.accountId && parsed.nickname && parsed.mystery) return parsed;
  } catch {}
  return null;
}

function saveSession(session: Session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export default function App() {
  const saved = loadSession();
  const [page, setPage] = useState<Page>(saved ? "question" : "nickname");
  const [accountId, setAccountId] = useState<string>(saved?.accountId || "");
  const [nickname, setNickname] = useState<string>(saved?.nickname || "");
  const [mystery, setMystery] = useState<string>(saved?.mystery || "");
  const [genieUrl, setGenieUrl] = useState<string>(saved?.genieUrl || "");

  function handleAccountCreated(
    id: string,
    nick: string,
    myst: string,
    provisioningStatus: string,
    gUrl: string | null
  ) {
    setAccountId(id);
    setNickname(nick);
    setMystery(myst);

    if (provisioningStatus === "completed" && gUrl) {
      setGenieUrl(gUrl);
      saveSession({ accountId: id, nickname: nick, mystery: myst, genieUrl: gUrl });
      setPage("question");
    } else {
      saveSession({ accountId: id, nickname: nick, mystery: myst, genieUrl: "" });
      setPage("provisioning");
    }
  }

  const handleProvisioningComplete = useCallback((gUrl: string) => {
    setGenieUrl(gUrl);
    const session: Session = { accountId, nickname, mystery, genieUrl: gUrl };
    saveSession(session);
    setPage("question");
  }, [accountId, nickname, mystery]);

  function handleSwitchMystery() {
    localStorage.removeItem(SESSION_KEY);
    setAccountId("");
    setMystery("");
    setGenieUrl("");
    setPage("nickname");
  }

  // Verify account still exists on load; silently re-create if DB was reset
  useEffect(() => {
    if (!accountId || !nickname || !mystery) return;
    api.getAccount(accountId).catch(async () => {
      try {
        const acct = await api.createAccount(nickname, mystery);
        setAccountId(acct.id);
        const gUrl = acct.genie_url || genieUrl;
        if (gUrl) setGenieUrl(gUrl);
        saveSession({ accountId: acct.id, nickname, mystery, genieUrl: gUrl });
      } catch {
        // nickname conflict — append a random suffix and retry
        try {
          const retryNick = nickname + Math.floor(Math.random() * 1000);
          const acct = await api.createAccount(retryNick, mystery);
          setAccountId(acct.id);
          setNickname(retryNick);
          const gUrl = acct.genie_url || genieUrl;
          if (gUrl) setGenieUrl(gUrl);
          saveSession({ accountId: acct.id, nickname: retryNick, mystery, genieUrl: gUrl });
        } catch {
          handleSwitchMystery();
        }
      }
    });
  }, [accountId]);

  return (
    <div className="container">
      {page !== "nickname" && page !== "provisioning" && (
        <div className="nav-tabs">
          <button
            className={page === "question" ? "active" : ""}
            onClick={() => setPage("question")}
          >
            Answer
          </button>
          <button
            className={page === "casefile" ? "active" : ""}
            onClick={() => setPage("casefile")}
          >
            Case File
          </button>
          <button
            className="btn-danger btn-small"
            onClick={handleSwitchMystery}
            style={{ marginLeft: "auto" }}
          >
            Switch Mystery
          </button>
        </div>
      )}

      {page === "nickname" && (
        <NicknameEntry onCreated={handleAccountCreated} existingNickname={nickname || undefined} />
      )}
      {page === "provisioning" && (
        <ProvisioningStatus
          accountId={accountId}
          onComplete={handleProvisioningComplete}
        />
      )}
      {page === "question" && (
        <QuestionView
          accountId={accountId}
          nickname={nickname}
          mystery={mystery}
          genieUrl={genieUrl}
        />
      )}
      {page === "casefile" && (
        <CaseFile accountId={accountId} nickname={nickname} mystery={mystery} />
      )}
    </div>
  );
}

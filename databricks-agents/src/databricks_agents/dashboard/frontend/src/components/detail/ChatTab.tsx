import { useChat } from "../../hooks/useChat";
import { MessageList } from "../chat/MessageList";
import { MessageInput } from "../chat/MessageInput";
import { SessionBar } from "../chat/SessionBar";
import { Inspector } from "../inspector/Inspector";
import { ErrorBanner } from "../common/ErrorBanner";

interface Props {
  agentName: string;
}

export function ChatTab({ agentName }: Props) {
  const {
    messages,
    toolCalls,
    traces,
    artifacts,
    sending,
    error,
    selectedTraceId,
    highlightedMessageId,
    selectTrace,
    send,
    clear,
    sessions,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
  } = useChat(agentName);

  return (
    <>
      {error && <ErrorBanner message={error} />}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.5rem",
        }}
      >
        <SessionBar
          sessions={sessions}
          onCreateSession={createSession}
          onSwitchSession={switchSession}
          onDeleteSession={deleteSession}
          onRenameSession={renameSession}
        />
        <button
          className="btn btn-outline btn-sm"
          onClick={clear}
          disabled={messages.length === 0}
        >
          Clear chat
        </button>
      </div>

      <div className="chat-layout">
        <div className="chat-main">
          <MessageList
            messages={messages}
            sending={sending}
            highlightedMessageId={highlightedMessageId}
          />
          <MessageInput onSend={send} disabled={sending} />
        </div>
        <Inspector
          toolCalls={toolCalls}
          traces={traces}
          artifacts={artifacts}
          selectedTraceId={selectedTraceId}
          onSelectTrace={selectTrace}
        />
      </div>
    </>
  );
}

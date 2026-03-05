import type { ChatMessage } from "../../types";

interface Props {
  message: ChatMessage;
  isHighlighted?: boolean;
}

export function MessageBubble({ message, isHighlighted }: Props) {
  const isUser = message.role === "user";

  const textContent = message.parts
    .filter((p) => p.type === "text")
    .map((p) => (p as { type: "text"; text: string }).text)
    .join("\n");

  const toolCallParts = message.parts.filter((p) => p.type === "tool-call");

  return (
    <div
      id={message.id}
      className={`message-bubble ${message.role}${isHighlighted ? " highlighted" : ""}`}
    >
      <div className="role-label">{isUser ? "You" : "Agent"}</div>
      <div className="content">
        {textContent && <div>{textContent}</div>}
        {toolCallParts.length > 0 && (
          <div style={{ marginTop: textContent ? "0.5rem" : 0 }}>
            {toolCallParts.map((p) => {
              const tc = p as {
                type: "tool-call";
                toolCallId: string;
                toolName: string;
              };
              return (
                <span
                  key={tc.toolCallId}
                  className="badge badge-blue"
                  style={{ marginRight: "0.25rem" }}
                >
                  {tc.toolName}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

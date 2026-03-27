import { useRef, useEffect } from "react";
import type { ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";
import { EmptyState } from "../common/EmptyState";

interface Props {
  messages: ChatMessage[];
  sending: boolean;
  highlightedMessageId?: string | null;
}

export function MessageList({ messages, sending, highlightedMessageId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, sending]);

  // Scroll highlighted message into view
  useEffect(() => {
    if (highlightedMessageId) {
      const el = document.getElementById(highlightedMessageId);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightedMessageId]);

  if (messages.length === 0) {
    return (
      <div className="message-list">
        <EmptyState
          title="Start a conversation"
          message="Send a message to chat with this agent via A2A protocol."
        />
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          isHighlighted={msg.id === highlightedMessageId}
        />
      ))}
      {sending && (
        <div className="message-bubble agent">
          <div className="role-label">Agent</div>
          <div className="content">
            <span className="spinner" /> Thinking...
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

import { ReactNode, useEffect, useRef } from 'react'
import { Message } from '../../types'
import './MessageList.css'

interface MessageListProps {
  messages: Message[]
  loading: boolean
  emptyState?: ReactNode
}

export default function MessageList({ messages, loading, emptyState }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="message-list">
      {messages.length === 0 && !loading && (
        emptyState || (
          <div className="chat-empty">
            <p>Start a conversation with the supervisor...</p>
          </div>
        )
      )}

      {messages.map((message) => (
        <div key={message.id} className={`message message-${message.role}`}>
          <div className="message-avatar">
            {message.role === 'user' ? 'U' : 'A'}
          </div>
          <div className="message-body">
            <div className="message-header">
              <strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong>
              <span className="message-time">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">{message.content}</div>
            {message.trace_id && (
              <div className="message-trace">Trace ID: {message.trace_id}</div>
            )}
          </div>
        </div>
      ))}

      {loading && (
        <div className="message message-assistant">
          <div className="message-avatar">A</div>
          <div className="message-body">
            <div className="message-header">
              <strong>Assistant</strong>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  )
}

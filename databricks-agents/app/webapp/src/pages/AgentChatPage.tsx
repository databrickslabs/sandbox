import { useState, useEffect, useRef, useCallback } from 'react'
import ThreePanel from '../components/chat/ThreePanel'
import MessageInput from '../components/chat/MessageInput'
import RoutingBadges from '../components/agent-chat/RoutingBadges'
import QueryConstructionPanel from '../components/agent-chat/QueryConstructionPanel'
import ProcessingPipelinePanel from '../components/agent-chat/ProcessingPipelinePanel'
import { agentChatApi } from '../api/agentChat'
import {
  AgentChatMessage,
  AgentChatEndpoint,
  SlotFillingInfo,
} from '../types'
import './AgentChatPage.css'

const EXAMPLE_QUERIES = [
  'What do healthcare experts say about AI adoption?',
  'What are the main challenges in supply chain optimization?',
  'Tell me about recent trends in digital transformation',
]

export default function AgentChatPage() {
  const [messages, setMessages] = useState<AgentChatMessage[]>([])
  const [endpoints, setEndpoints] = useState<AgentChatEndpoint[]>([])
  const [selectedEndpoint, setSelectedEndpoint] = useState('')
  const [currentSlotFilling, setCurrentSlotFilling] = useState<SlotFillingInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    agentChatApi.getEndpoints().then((data) => {
      setEndpoints(data.endpoints)
      if (data.endpoints.length > 0) {
        setSelectedEndpoint(data.endpoints[0].name)
      }
    }).catch(() => {
      setError('Failed to load endpoints')
    })
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(async (content: string) => {
    if (!content.trim() || loading || !selectedEndpoint) return

    const userMessage: AgentChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setLoading(true)
    setError(null)

    try {
      const response = await agentChatApi.queryEndpoint(selectedEndpoint, content)

      const assistantMessage: AgentChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.content,
        timestamp: response.timestamp,
        endpoint: response.endpoint,
        routing: response.routing ?? undefined,
        slotFilling: response.slotFilling ?? undefined,
        pipeline: response.pipeline ?? undefined,
      }

      setMessages((prev) => [...prev, assistantMessage])

      if (response.slotFilling) {
        setCurrentSlotFilling(response.slotFilling)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setLoading(false)
    }
  }, [loading, selectedEndpoint])

  const handleClear = () => {
    setMessages([])
    setCurrentSlotFilling(null)
    setError(null)
  }

  // Find last assistant message with pipeline data for right sidebar
  const lastPipelineMessage = [...messages]
    .reverse()
    .find((m) => m.role === 'assistant' && !!m.pipeline)

  return (
    <div className="agent-chat-page">
      {/* Header */}
      <div className="agent-chat-header">
        <h2>Agent Chat</h2>
        <div className="agent-chat-controls">
          <select
            value={selectedEndpoint}
            onChange={(e) => setSelectedEndpoint(e.target.value)}
            disabled={loading}
            className="endpoint-select"
          >
            {endpoints.length === 0 && (
              <option value="" disabled>No endpoints available</option>
            )}
            {endpoints.map((ep) => (
              <option key={ep.name} value={ep.name}>
                {ep.displayName}{ep.type === 'supervisor' ? ' (Routes to sub-agents)' : ''}
              </option>
            ))}
          </select>
          <button
            className="clear-btn"
            onClick={handleClear}
            disabled={loading || messages.length === 0}
          >
            Clear
          </button>
        </div>
      </div>

      {error && (
        <div className="agent-chat-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      {/* Main 3-panel layout */}
      <ThreePanel
        left={<QueryConstructionPanel slotFilling={currentSlotFilling} />}
        center={
          <div className="agent-chat-center">
            <div className="agent-chat-messages">
              {messages.length === 0 && (
                <div className="agent-chat-welcome">
                  <h3>Welcome to Agent Chat</h3>
                  <p>Ask questions about expert insights and research.</p>
                  <div className="example-queries">
                    <span className="example-label">Example queries:</span>
                    {EXAMPLE_QUERIES.map((q, idx) => (
                      <button
                        key={idx}
                        className="example-query-btn"
                        onClick={() => handleSend(q)}
                        disabled={!selectedEndpoint}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`agent-chat-bubble ${message.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}
                >
                  <div className="bubble-inner">
                    <div className="bubble-meta">
                      <span className="bubble-role">
                        {message.role === 'user' ? 'You' : 'Agent'}
                      </span>
                      <span className="bubble-time">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    {message.routing && <RoutingBadges routing={message.routing} />}

                    <div className="bubble-content">{message.content}</div>

                    {message.endpoint && (
                      <div className="bubble-endpoint">
                        <span className="endpoint-badge">{message.endpoint}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="agent-chat-bubble bubble-assistant">
                  <div className="bubble-inner bubble-loading">
                    <span className="loading-dot" />
                    <span className="loading-dot" />
                    <span className="loading-dot" />
                    <span className="loading-text">Thinking...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
            <MessageInput onSend={handleSend} disabled={loading || !selectedEndpoint} />
          </div>
        }
        right={<ProcessingPipelinePanel pipeline={lastPipelineMessage?.pipeline ?? null} />}
      />
    </div>
  )
}

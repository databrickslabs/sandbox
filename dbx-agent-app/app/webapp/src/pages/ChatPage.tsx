import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { supervisorApi } from '../api/supervisor'
import { registryApi } from '../api/registry'
import { Message, TraceEvent, Span, Collection, Conversation } from '../types'
import ThreePanel from '../components/chat/ThreePanel'
import TraceTimeline from '../components/chat/TraceTimeline'
import ConversationSidebar from '../components/chat/ConversationSidebar'
import MessageList from '../components/chat/MessageList'
import MessageInput from '../components/chat/MessageInput'
import WelcomeScreen from '../components/chat/WelcomeScreen'
import Inspector from '../components/chat/Inspector'
import Button from '../components/common/Button'
import './ChatPage.css'

export default function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [messages, setMessages] = useState<Message[]>([])
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [selectedEvent, setSelectedEvent] = useState<TraceEvent | null>(null)
  const [spans, setSpans] = useState<Span[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sseConnection, setSseConnection] = useState<EventSource | null>(null)
  const [collections, setCollections] = useState<Collection[]>([])
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null)

  // Conversation state
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])

  useEffect(() => {
    const paramId = searchParams.get('collection')
    if (paramId) {
      setSelectedCollectionId(Number(paramId))
    }
    registryApi.getCollections().then(setCollections)
    loadConversations()
  }, [])

  useEffect(() => {
    return () => {
      disconnectSSE()
    }
  }, [])

  useEffect(() => {
    if (selectedEvent) {
      loadSpans(selectedEvent.trace_id)
    }
  }, [selectedEvent])

  // Auto-send question from URL ?q= param (e.g., from Discover page "Ask AI")
  useEffect(() => {
    const question = searchParams.get('q')
    if (question && messages.length === 0 && !loading) {
      setSearchParams({}, { replace: true })
      handleSend(question)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const loadConversations = async () => {
    try {
      const result = await supervisorApi.getConversations()
      setConversations(result.conversations)
    } catch {
      // Conversation list load failed silently
    }
  }

  const disconnectSSE = useCallback(() => {
    if (sseConnection) {
      sseConnection.close()
      setSseConnection(null)
    }
  }, [sseConnection])

  const connectSSE = useCallback((traceId: string) => {
    disconnectSSE()

    const baseUrl = import.meta.env.VITE_SUPERVISOR_URL || '/api'
    const eventSource = new EventSource(`${baseUrl}/events?trace_id=${traceId}`)

    const eventTypes: Array<TraceEvent['type']> = [
      'request.started',
      'tool.called',
      'tool.output',
      'response.delta',
      'response.done'
    ]

    eventTypes.forEach((type) => {
      eventSource.addEventListener(type, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data)
          const newEvent: TraceEvent = {
            id: crypto.randomUUID(),
            trace_id: traceId,
            type,
            timestamp: new Date().toISOString(),
            data
          }
          setEvents((prev) => [...prev, newEvent])

          if (type === 'response.done') {
            setTimeout(() => disconnectSSE(), 1000)
          }
        } catch {
          // Ignore malformed SSE events
        }
      })
    })

    eventSource.onerror = () => {
      if (eventSource.readyState === EventSource.CLOSED) {
        return
      }
      setError('SSE connection error')
      disconnectSSE()
    }

    setSseConnection(eventSource)
  }, [disconnectSSE])

  const loadSpans = async (traceId: string) => {
    try {
      const response = await supervisorApi.getTrace(traceId)
      setSpans(response.spans)
    } catch {
      // Span loading failed silently
    }
  }

  const handleSend = async (content: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }

    setMessages((prev) => [...prev, userMessage])
    setLoading(true)
    setError(null)
    setEvents([])
    setSelectedEvent(null)
    setSpans([])

    try {
      const response = await supervisorApi.chat({
        text: content,
        server_urls: [],
        ...(selectedCollectionId ? { collection_id: selectedCollectionId } : {}),
        ...(conversationId ? { conversation_id: conversationId } : {}),
      })

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.text,
        timestamp: new Date().toISOString(),
        trace_id: response.trace_id
      }

      setMessages((prev) => [...prev, assistantMessage])

      // Update conversation ID from response (server creates it if new)
      if (response.conversation_id) {
        setConversationId(response.conversation_id)
      }

      // Refresh conversation list to show new/updated conversation
      loadConversations()

      connectSSE(response.trace_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectConversation = async (id: string) => {
    try {
      const conv = await supervisorApi.getConversation(id)
      setConversationId(id)
      setMessages(
        conv.messages.map((m) => ({
          id: String(m.id),
          role: m.role,
          content: m.content,
          timestamp: m.created_at ?? new Date().toISOString(),
          trace_id: m.trace_id ?? undefined,
        }))
      )
      setEvents([])
      setSelectedEvent(null)
      setSpans([])
      disconnectSSE()
    } catch {
      setError('Failed to load conversation')
    }
  }

  const handleNewChat = () => {
    setConversationId(null)
    setMessages([])
    setEvents([])
    setSelectedEvent(null)
    setSpans([])
    disconnectSSE()
  }

  const handleDeleteConversation = async (id: string) => {
    try {
      await supervisorApi.deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (conversationId === id) {
        handleNewChat()
      }
    } catch {
      setError('Failed to delete conversation')
    }
  }

  const handleCollectionChange = (value: string) => {
    const id = value ? Number(value) : null
    setSelectedCollectionId(id)
    if (id) {
      setSearchParams({ collection: String(id) })
    } else {
      setSearchParams({})
    }
  }

  const handleClearChat = () => {
    handleNewChat()
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div>
          <h2>Chat</h2>
          <p className="chat-subtitle">
            {selectedCollectionId
              ? `Testing: ${collections.find((c) => c.id === selectedCollectionId)?.name ?? 'Collection'}`
              : 'Interact with multi-agent supervisors'}
          </p>
        </div>
        <div className="chat-actions">
          <select
            className="collection-picker"
            value={selectedCollectionId ?? ''}
            onChange={(e) => handleCollectionChange(e.target.value)}
          >
            <option value="">All Tools</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {messages.length > 0 && (
            <Button variant="secondary" size="small" onClick={handleClearChat}>
              Clear Chat
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="chat-error-banner">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <ThreePanel
        left={
          <ConversationSidebar
            conversations={conversations}
            activeConversationId={conversationId}
            onSelectConversation={handleSelectConversation}
            onNewChat={handleNewChat}
            onDeleteConversation={handleDeleteConversation}
          />
        }
        center={
          <>
            <MessageList
              messages={messages}
              loading={loading}
              emptyState={<WelcomeScreen onSelectQuestion={handleSend} />}
            />
            <MessageInput onSend={handleSend} disabled={loading} />
          </>
        }
        right={
          <>
            <Inspector selectedEvent={selectedEvent} spans={spans} />
            {events.length > 0 && (
              <TraceTimeline
                events={events}
                selectedEvent={selectedEvent}
                onSelectEvent={setSelectedEvent}
              />
            )}
          </>
        }
      />
    </div>
  )
}

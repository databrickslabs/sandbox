import { useState } from 'react'
import { Conversation } from '../../types'
import './ConversationSidebar.css'

interface ConversationSidebarProps {
  conversations: Conversation[]
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
  onDeleteConversation: (id: string) => void
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return ''
  const date = new Date(ts)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString()
}

export default function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
}: ConversationSidebarProps) {
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (pendingDelete === id) {
      onDeleteConversation(id)
      setPendingDelete(null)
    } else {
      setPendingDelete(id)
      // Auto-clear confirmation after 3s
      setTimeout(() => setPendingDelete(null), 3000)
    }
  }

  return (
    <div className="conversation-sidebar">
      <div className="conversation-sidebar-header">
        <h3>Conversations</h3>
        <button className="new-chat-btn" onClick={onNewChat}>
          + New
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="conversation-empty">
            No conversations yet. Start a new chat!
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === activeConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-item-content">
                <div className="conversation-item-title">{conv.title}</div>
                <div className="conversation-item-meta">
                  <span>{conv.message_count} msgs</span>
                  <span>{formatTimestamp(conv.updated_at)}</span>
                </div>
              </div>
              <button
                className="conversation-delete-btn"
                onClick={(e) => handleDelete(e, conv.id)}
                title={pendingDelete === conv.id ? 'Click again to confirm' : 'Delete conversation'}
              >
                {pendingDelete === conv.id ? '?' : '×'}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { registryApi } from '../api/registry'
import { Agent, AgentCreate, Collection, A2AAgentCard, A2ATask } from '../types'
import AgentCard from '../components/agents/AgentCard'
import CreateAgentModal from '../components/agents/CreateAgentModal'
import Button from '../components/common/Button'
import Badge from '../components/common/Badge'
import Spinner from '../components/common/Spinner'
import './AgentsPage.css'

const statusVariant: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  active: 'success',
  draft: 'warning',
  error: 'danger',
  inactive: 'default',
}

const taskStatusVariant: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  completed: 'success',
  working: 'warning',
  submitted: 'default',
  failed: 'danger',
  canceled: 'danger',
}

export default function AgentsPage() {
  const navigate = useNavigate()
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [agentCard, setAgentCard] = useState<A2AAgentCard | null>(null)
  const [a2aTasks, setA2aTasks] = useState<A2ATask[]>([])
  const [showCardJson, setShowCardJson] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (selectedAgent) {
      loadAgentDetail(selectedAgent.id)
    } else {
      setAgentCard(null)
      setA2aTasks([])
    }
  }, [selectedAgent?.id])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [agentsData, collectionsData] = await Promise.all([
        registryApi.getAgents(),
        registryApi.getCollections()
      ])
      setAgents(agentsData)
      setCollections(collectionsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadAgentDetail = async (agentId: number) => {
    try {
      const [agent, card, tasks] = await Promise.all([
        registryApi.getAgent(agentId),
        registryApi.getAgentCard(agentId).catch(() => null),
        registryApi.getA2ATasks(agentId).catch(() => []),
      ])
      setSelectedAgent(agent)
      setAgentCard(card)
      setA2aTasks(tasks)
    } catch {
      // keep current selection on error
    }
  }

  const handleCreateAgent = async (data: AgentCreate) => {
    await registryApi.createAgent(data)
    await loadData()
  }

  const handleDeleteAgent = async () => {
    if (!selectedAgent) return
    if (!confirm(`Are you sure you want to delete "${selectedAgent.name}"?`)) return

    try {
      await registryApi.deleteAgent(selectedAgent.id)
      setSelectedAgent(null)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent')
    }
  }

  const getCollectionName = (collectionId: number | null) => {
    if (!collectionId) return null
    const collection = collections.find((c) => c.id === collectionId)
    return collection?.name || `Collection #${collectionId}`
  }

  if (loading && !agents.length) {
    return (
      <div className="agents-page">
        <div className="agents-loading">
          <Spinner size="large" />
          <p>Loading agents...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="agents-page">
      <div className="agents-header">
        <div className="agents-title">
          <h2>Agents</h2>
          <p className="agents-subtitle">Discover and manage registered agents</p>
        </div>
        <Button onClick={() => setCreateModalOpen(true)}>
          Create Agent
        </Button>
      </div>

      {error && (
        <div className="agents-error-banner">
          {error}
          <button onClick={() => setError(null)}>x</button>
        </div>
      )}

      <div className="agents-layout">
        <aside className="agents-sidebar">
          <h3>Agents ({agents.length})</h3>
          <div className="agent-list">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                isActive={selectedAgent?.id === agent.id}
                onClick={() => setSelectedAgent(agent)}
              />
            ))}
            {agents.length === 0 && (
              <div className="empty-state">
                <p>No agents registered yet.</p>
                <Button size="small" onClick={() => setCreateModalOpen(true)}>
                  Create Your First Agent
                </Button>
              </div>
            )}
          </div>
        </aside>

        <main className="agents-main">
          {selectedAgent ? (
            <div className="agent-detail">
              <div className="agent-detail-header">
                <div>
                  <div className="agent-detail-title-row">
                    <h3>{selectedAgent.name}</h3>
                    <Badge variant={statusVariant[selectedAgent.status] || 'default'}>
                      {selectedAgent.status}
                    </Badge>
                    {selectedAgent.protocol_version && (
                      <Badge variant="default">{`A2A v${selectedAgent.protocol_version}`}</Badge>
                    )}
                  </div>
                  <p>{selectedAgent.description || 'No description'}</p>
                </div>
                <div className="agent-actions">
                  {selectedAgent.collection_id && (
                    <Button
                      size="small"
                      onClick={() => navigate(`/chat?collection=${selectedAgent.collection_id}`)}
                    >
                      Chat
                    </Button>
                  )}
                  <Button
                    size="small"
                    variant="danger"
                    onClick={handleDeleteAgent}
                  >
                    Delete
                  </Button>
                </div>
              </div>

              <div className="agent-detail-body">
                {selectedAgent.capabilities && (
                  <div className="agent-detail-section">
                    <h4>Capabilities</h4>
                    <div className="agent-capabilities-list">
                      {selectedAgent.capabilities.split(',').map((cap) => (
                        <span key={cap.trim()} className="capability-badge">{cap.trim()}</span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedAgent.system_prompt && (
                  <div className="agent-detail-section">
                    <h4>System Prompt</h4>
                    <pre className="agent-system-prompt">{selectedAgent.system_prompt}</pre>
                  </div>
                )}

                {selectedAgent.collection_id && (
                  <div className="agent-detail-section">
                    <h4>Linked Collection</h4>
                    <p className="agent-detail-value">
                      {getCollectionName(selectedAgent.collection_id)}
                    </p>
                  </div>
                )}

                {selectedAgent.endpoint_url && (
                  <div className="agent-detail-section">
                    <h4>Endpoint</h4>
                    <p className="agent-detail-endpoint">{selectedAgent.endpoint_url}</p>
                  </div>
                )}

                {/* A2A Agent Card section */}
                {agentCard && (
                  <div className="agent-detail-section">
                    <div className="agent-detail-section-header">
                      <h4>Agent Card</h4>
                      <button
                        className="toggle-json-btn"
                        onClick={() => setShowCardJson(!showCardJson)}
                      >
                        {showCardJson ? 'Hide JSON' : 'Show JSON'}
                      </button>
                    </div>
                    <div className="agent-card-info">
                      <p className="agent-detail-meta">
                        Protocol: A2A v{agentCard.protocolVersion}
                      </p>
                      <p className="agent-detail-meta">
                        URL: <code>{agentCard.url}</code>
                      </p>
                      {agentCard.capabilities && (
                        <div className="agent-card-caps">
                          <Badge variant={agentCard.capabilities.streaming ? 'success' : 'default'}>
                            {`Streaming: ${agentCard.capabilities.streaming ? 'Yes' : 'No'}`}
                          </Badge>
                          <Badge variant={agentCard.capabilities.pushNotifications ? 'success' : 'default'}>
                            {`Push: ${agentCard.capabilities.pushNotifications ? 'Yes' : 'No'}`}
                          </Badge>
                        </div>
                      )}
                      {agentCard.skills.length > 0 && (
                        <div className="agent-card-skills">
                          <p className="agent-detail-meta">Skills:</p>
                          <div className="agent-capabilities-list">
                            {agentCard.skills.map((skill) => (
                              <span key={skill.id} className="capability-badge" title={skill.description || ''}>
                                {skill.name}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {showCardJson && (
                        <pre className="agent-card-json">
                          {JSON.stringify(agentCard, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                )}

                {/* A2A Tasks section */}
                {a2aTasks.length > 0 && (
                  <div className="agent-detail-section">
                    <h4>A2A Tasks ({a2aTasks.length})</h4>
                    <div className="a2a-tasks-list">
                      {a2aTasks.map((task) => (
                        <div key={task.id} className="a2a-task-item">
                          <div className="a2a-task-header">
                            <code className="a2a-task-id">{task.id.slice(0, 8)}...</code>
                            <Badge variant={taskStatusVariant[task.status.state] || 'default'}>
                              {task.status.state}
                            </Badge>
                          </div>
                          {task.messages.length > 0 && (
                            <p className="a2a-task-preview">
                              {task.messages[0].parts[0]?.text?.slice(0, 100) || 'No content'}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="agent-detail-section">
                  <h4>Timestamps</h4>
                  <div className="agent-timestamps">
                    {selectedAgent.created_at && (
                      <p className="agent-detail-meta">Created: {new Date(selectedAgent.created_at).toLocaleString()}</p>
                    )}
                    {selectedAgent.updated_at && (
                      <p className="agent-detail-meta">Updated: {new Date(selectedAgent.updated_at).toLocaleString()}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="agent-empty">
              <p>Select an agent to view details</p>
            </div>
          )}
        </main>
      </div>

      <CreateAgentModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreate={handleCreateAgent}
      />
    </div>
  )
}

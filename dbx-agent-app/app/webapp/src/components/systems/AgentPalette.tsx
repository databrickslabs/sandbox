import { useEffect, useState } from 'react'
import { registryClient } from '../../api/client'
import './AgentPalette.css'

interface DiscoveredAgent {
  name: string
  endpoint_url: string
  app_name: string
  description: string
  capabilities: string
}

interface AgentPaletteProps {
  onAddAgent: (agentName: string) => void
  addedAgents: Set<string>
}

export default function AgentPalette({ onAddAgent, addedAgents }: AgentPaletteProps) {
  const [agents, setAgents] = useState<DiscoveredAgent[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await registryClient.get('/agents')
        const data = Array.isArray(response.data) ? response.data : []
        setAgents(data)
      } catch {
        setAgents([])
      } finally {
        setLoading(false)
      }
    }
    fetchAgents()
  }, [])

  const filtered = agents.filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    (a.description || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="agent-palette">
      <h3 className="palette-title">Agents</h3>
      <input
        type="text"
        className="palette-search"
        placeholder="Search agents..."
        value={search}
        onChange={e => setSearch(e.target.value)}
      />
      {loading ? (
        <div className="palette-loading">Loading agents...</div>
      ) : filtered.length === 0 ? (
        <div className="palette-empty">No agents found</div>
      ) : (
        <div className="palette-list">
          {filtered.map(agent => {
            const isAdded = addedAgents.has(agent.name)
            return (
              <div
                key={agent.name}
                className={`palette-agent ${isAdded ? 'palette-agent-added' : ''}`}
                onClick={() => !isAdded && onAddAgent(agent.name)}
              >
                <div className="palette-agent-name">{agent.name}</div>
                {agent.description && (
                  <div className="palette-agent-desc">{agent.description}</div>
                )}
                {agent.capabilities && (
                  <div className="palette-agent-caps">
                    {agent.capabilities.split(',').map(c => c.trim()).filter(Boolean).map(cap => (
                      <span key={cap} className="palette-cap-badge">{cap}</span>
                    ))}
                  </div>
                )}
                {isAdded && <span className="palette-added-badge">Added</span>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

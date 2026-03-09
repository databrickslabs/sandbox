import { Agent } from '../../types'
import Card from '../common/Card'
import Badge from '../common/Badge'
import './AgentCard.css'

interface AgentCardProps {
  agent: Agent
  isActive: boolean
  onClick: () => void
}

const statusVariant: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  active: 'success',
  draft: 'warning',
  error: 'danger',
  inactive: 'default',
}

export default function AgentCard({ agent, isActive, onClick }: AgentCardProps) {
  return (
    <Card className={`agent-card ${isActive ? 'active' : ''}`} onClick={onClick}>
      <div className="agent-card-header">
        <h4>{agent.name}</h4>
        <Badge variant={statusVariant[agent.status] || 'default'}>
          {agent.status}
        </Badge>
      </div>
      <p className="agent-card-description">{agent.description || 'No description'}</p>
      {agent.capabilities && (
        <div className="agent-card-capabilities">
          {agent.capabilities.split(',').map((cap) => (
            <span key={cap.trim()} className="capability-tag">{cap.trim()}</span>
          ))}
        </div>
      )}
    </Card>
  )
}

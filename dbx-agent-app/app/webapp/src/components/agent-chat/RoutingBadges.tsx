import { RoutingInfo } from '../../types'
import './RoutingBadges.css'

interface RoutingBadgesProps {
  routing: RoutingInfo
}

export default function RoutingBadges({ routing }: RoutingBadgesProps) {
  if (!routing.usedSupervisor && (!routing.toolCalls || routing.toolCalls.length === 0)) {
    return null
  }

  return (
    <div className="routing-badges">
      {routing.usedSupervisor && (
        <div className="routing-flow">
          <span className="routing-badge routing-badge-primary">Supervisor Agent</span>
          {routing.subAgent && (
            <>
              <span className="routing-arrow">&rarr;</span>
              <span className="routing-badge routing-badge-secondary">{routing.subAgent}</span>
            </>
          )}
        </div>
      )}

      {routing.toolCalls.length > 0 && (
        <div className="routing-tools">
          {routing.toolCalls.map((tool, idx) => (
            <span key={idx} className="routing-badge routing-badge-outlined">
              {tool.tool}: {tool.description}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

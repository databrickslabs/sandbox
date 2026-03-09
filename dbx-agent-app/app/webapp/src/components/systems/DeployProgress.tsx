import { useState } from 'react'
import { DeployResult } from '../../types'
import './DeployProgress.css'

interface DeployProgressProps {
  result: DeployResult
}

const STATUS_COLORS: Record<string, string> = {
  success: '#34a853',
  failed: '#ea4335',
  skipped: '#f9ab00',
}

const ACTION_LABELS: Record<string, string> = {
  env_update: 'Env Vars + Redeploy',
  redeploy: 'Redeploy',
  grant_permission: 'Permission Grant',
  uc_register: 'UC Registration',
  resolve: 'Resolve Agent',
  lookup: 'System Lookup',
}

export default function DeployProgress({ result }: DeployProgressProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  const overallColor = STATUS_COLORS[result.status] || '#999'

  return (
    <div className="deploy-progress">
      <div className="deploy-progress-header">
        <span
          className="deploy-status-badge"
          style={{ backgroundColor: overallColor }}
        >
          {result.status.toUpperCase()}
        </span>
        <span className="deploy-step-count">
          {result.steps.length} step{result.steps.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="deploy-steps">
        {result.steps.map((step, idx) => {
          const color = STATUS_COLORS[step.status] || '#999'
          const isExpanded = expandedIdx === idx
          return (
            <div
              key={idx}
              className="deploy-step"
              onClick={() => setExpandedIdx(isExpanded ? null : idx)}
            >
              <div className="deploy-step-row">
                <span
                  className="deploy-step-indicator"
                  style={{ backgroundColor: color }}
                />
                <span className="deploy-step-agent">{step.agent || '—'}</span>
                <span className="deploy-step-action">
                  {ACTION_LABELS[step.action] || step.action}
                </span>
                <span
                  className="deploy-step-status"
                  style={{ color }}
                >
                  {step.status}
                </span>
              </div>
              {isExpanded && step.detail && (
                <div className="deploy-step-detail">{step.detail}</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

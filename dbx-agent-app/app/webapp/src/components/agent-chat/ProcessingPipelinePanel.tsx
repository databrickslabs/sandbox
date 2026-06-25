import { PipelineInfo } from '../../types'
import './ProcessingPipelinePanel.css'

interface ProcessingPipelinePanelProps {
  pipeline: PipelineInfo | null
}

export default function ProcessingPipelinePanel({ pipeline }: ProcessingPipelinePanelProps) {
  if (!pipeline) {
    return (
      <div className="pipeline-panel">
        <h3 className="pipeline-panel-title">Processing Pipeline</h3>
        <p className="pipeline-panel-empty">Send a message to see processing pipeline...</p>
      </div>
    )
  }

  const { metrics } = pipeline

  return (
    <div className="pipeline-panel">
      <h3 className="pipeline-panel-title">Processing Pipeline</h3>
      <p className="pipeline-panel-subtitle">All Steps &amp; Tools</p>

      {/* Summary Stats */}
      <div className="pipeline-stats">
        <div className="stat-card">
          <span className="stat-value">{pipeline.totalSteps}</span>
          <span className="stat-label">Steps</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{pipeline.totalDuration}ms</span>
          <span className="stat-label">Total Time</span>
        </div>
        {metrics && (
          <>
            <div className="stat-card">
              <span className="stat-value">{metrics.totalTokens.toLocaleString()}</span>
              <span className="stat-label">Tokens</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{metrics.costBreakdown.total}</span>
              <span className="stat-label">Est. Cost</span>
            </div>
          </>
        )}
      </div>

      {/* Cost Breakdown */}
      {metrics && (
        <details className="pipeline-details" open>
          <summary className="pipeline-details-summary">Cost Breakdown</summary>
          <table className="cost-table">
            <tbody>
              <tr>
                <td>Input</td>
                <td className="cost-value">{metrics.costBreakdown.input}</td>
                <td className="cost-tokens">{metrics.inputTokens.toLocaleString()} tok</td>
              </tr>
              <tr>
                <td>Output</td>
                <td className="cost-value">{metrics.costBreakdown.output}</td>
                <td className="cost-tokens">{metrics.outputTokens.toLocaleString()} tok</td>
              </tr>
              <tr className="cost-total-row">
                <td><strong>Total</strong></td>
                <td className="cost-value"><strong>{metrics.costBreakdown.total}</strong></td>
                <td className="cost-tokens">{metrics.tokensPerSecond.toLocaleString()} tok/s</td>
              </tr>
            </tbody>
          </table>
        </details>
      )}

      {/* Latency Breakdown */}
      {metrics?.latencyBreakdown && (
        <details className="pipeline-details" open>
          <summary className="pipeline-details-summary">Latency Breakdown</summary>
          <div className="latency-bars">
            {(['preprocessing', 'search', 'llm', 'postprocessing'] as const).map((phase) => {
              const value = metrics.latencyBreakdown[phase]
              const pct = metrics.latencyBreakdown.total > 0
                ? (value / metrics.latencyBreakdown.total) * 100
                : 0
              return (
                <div key={phase} className="latency-item">
                  <div className="latency-header">
                    <span className="latency-phase">{phase}</span>
                    <span className="latency-value">{value}ms ({pct.toFixed(1)}%)</span>
                  </div>
                  <div className="latency-bar">
                    <div className="latency-fill" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
            <div className="latency-total">
              <span><strong>Total</strong></span>
              <span>
                <strong>{metrics.latencyBreakdown.total}ms</strong>{' '}
                ({(metrics.latencyBreakdown.total / 1000).toFixed(2)}s)
              </span>
            </div>
          </div>
        </details>
      )}

      {/* Pipeline Steps */}
      <div className="pipeline-steps-section">
        <span className="pipeline-steps-label">Steps</span>
        <div className="pipeline-steps">
          {pipeline.steps.map((step, idx) => (
            <div key={step.id} className="pipeline-step">
              {/* Step number with connector */}
              <div className="step-indicator">
                <span className="step-number">#{step.id}</span>
                {idx < pipeline.steps.length - 1 && <div className="step-connector" />}
              </div>

              {/* Step content */}
              <div className="step-content">
                <div className="step-header">
                  <div className="step-name-row">
                    <span className="step-name">{step.name}</span>
                    <span className="step-check">&#10003;</span>
                  </div>
                  <span className="step-duration">{step.duration}ms</span>
                </div>

                {/* Tools */}
                {step.tools.length > 0 && (
                  <div className="step-tools">
                    {step.tools.map((tool, toolIdx) => (
                      <span key={toolIdx} className="step-tool-chip">{tool}</span>
                    ))}
                  </div>
                )}

                {/* Step Metrics */}
                {step.metrics && (
                  <div className="step-metrics">
                    {step.metrics.latency != null && (
                      <span className="metric-chip">{step.metrics.latency}ms</span>
                    )}
                    {step.metrics.estimatedCost != null && (
                      <span className="metric-chip metric-chip-cost">
                        ${step.metrics.estimatedCost.toFixed(6)}
                      </span>
                    )}
                    {step.metrics.inputTokens != null && (
                      <span className="metric-chip">{step.metrics.inputTokens.toLocaleString()} in</span>
                    )}
                    {step.metrics.outputTokens != null && (
                      <span className="metric-chip">{step.metrics.outputTokens.toLocaleString()} out</span>
                    )}
                    {step.metrics.tokensPerSecond != null && (
                      <span className="metric-chip">{step.metrics.tokensPerSecond.toLocaleString()} tok/s</span>
                    )}
                    {step.metrics.entitiesFound != null && (
                      <span className="metric-chip">{step.metrics.entitiesFound} entities</span>
                    )}
                  </div>
                )}

                {/* Step Details */}
                <details className="step-details">
                  <summary className="step-details-summary">Details</summary>
                  <pre className="step-details-json">
                    {JSON.stringify(step.details, null, 2)}
                  </pre>
                </details>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { WiringEdge, SystemDefinition, DeployResult } from '../../types'
import { registryClient } from '../../api/client'
import DeployProgress from './DeployProgress'
import './PropertiesPanel.css'

interface DiscoveredAgent {
  name: string
  endpoint_url: string
  app_name: string
  description: string
  capabilities: string
}

interface PropertiesPanelProps {
  system: SystemDefinition | null
  selectedNode: string | null
  selectedEdge: string | null
  edges: WiringEdge[]
  onEdgeUpdate: (edgeId: string, envVar: string) => void
  onRemoveAgent: (agentName: string) => void
  onSystemMetaChange: (field: string, value: string) => void
  onSave: () => void
  onDeploy: () => Promise<DeployResult | null>
  saving: boolean
}

export default function PropertiesPanel({
  system,
  selectedNode,
  selectedEdge,
  edges,
  onEdgeUpdate,
  onRemoveAgent,
  onSystemMetaChange,
  onSave,
  onDeploy,
  saving,
}: PropertiesPanelProps) {
  const [agentInfo, setAgentInfo] = useState<DiscoveredAgent | null>(null)
  const [deploying, setDeploying] = useState(false)
  const [deployResult, setDeployResult] = useState<DeployResult | null>(null)

  // Fetch agent info when a node is selected
  useEffect(() => {
    if (!selectedNode) {
      setAgentInfo(null)
      return
    }
    const fetchInfo = async () => {
      try {
        const response = await registryClient.get('/agents')
        const agents: DiscoveredAgent[] = Array.isArray(response.data) ? response.data : []
        const found = agents.find(a => a.name === selectedNode)
        setAgentInfo(found || null)
      } catch {
        setAgentInfo(null)
      }
    }
    fetchInfo()
  }, [selectedNode])

  const handleDeploy = async () => {
    setDeploying(true)
    setDeployResult(null)
    try {
      const result = await onDeploy()
      setDeployResult(result)
    } finally {
      setDeploying(false)
    }
  }

  const selectedEdgeData = selectedEdge
    ? edges.find(e => `${e.source_agent}->${e.target_agent}` === selectedEdge)
    : null

  return (
    <div className="properties-panel">
      <h3 className="properties-title">Properties</h3>

      {/* System metadata */}
      {system && (
        <div className="properties-section">
          <label className="properties-label">System Name</label>
          <input
            type="text"
            className="properties-input"
            value={system.name}
            onChange={e => onSystemMetaChange('name', e.target.value)}
          />
          <label className="properties-label">Description</label>
          <textarea
            className="properties-textarea"
            value={system.description}
            onChange={e => onSystemMetaChange('description', e.target.value)}
            rows={2}
          />
          <label className="properties-label">UC Catalog</label>
          <input
            type="text"
            className="properties-input"
            value={system.uc_catalog}
            onChange={e => onSystemMetaChange('uc_catalog', e.target.value)}
            placeholder="Optional"
          />
          <label className="properties-label">UC Schema</label>
          <input
            type="text"
            className="properties-input"
            value={system.uc_schema}
            onChange={e => onSystemMetaChange('uc_schema', e.target.value)}
            placeholder="Optional"
          />
        </div>
      )}

      {/* Selected edge properties */}
      {selectedEdgeData && (
        <div className="properties-section">
          <div className="properties-section-title">Edge: {selectedEdgeData.source_agent} → {selectedEdgeData.target_agent}</div>
          <label className="properties-label">Env Var (injected into {selectedEdgeData.target_agent})</label>
          <input
            type="text"
            className="properties-input"
            value={selectedEdgeData.env_var}
            onChange={e => onEdgeUpdate(selectedEdge!, e.target.value)}
            placeholder="e.g. RESEARCH_AGENT_URL"
          />
          <div className="properties-hint">
            This env var will be set to the URL of {selectedEdgeData.source_agent} when deployed.
          </div>
        </div>
      )}

      {/* Selected node properties */}
      {selectedNode && (
        <div className="properties-section">
          <div className="properties-section-title">Agent: {selectedNode}</div>
          {agentInfo ? (
            <>
              {agentInfo.description && (
                <div className="properties-detail">
                  <span className="properties-detail-label">Description:</span> {agentInfo.description}
                </div>
              )}
              {agentInfo.endpoint_url && (
                <div className="properties-detail">
                  <span className="properties-detail-label">URL:</span>{' '}
                  <span className="properties-url">{agentInfo.endpoint_url}</span>
                </div>
              )}
              {agentInfo.capabilities && (
                <div className="properties-detail">
                  <span className="properties-detail-label">Capabilities:</span> {agentInfo.capabilities}
                </div>
              )}
            </>
          ) : (
            <div className="properties-detail">Loading agent info...</div>
          )}
          <button
            className="properties-btn properties-btn-danger"
            onClick={() => onRemoveAgent(selectedNode)}
          >
            Remove from System
          </button>
        </div>
      )}

      {/* No selection */}
      {!selectedNode && !selectedEdgeData && (
        <div className="properties-empty">
          Select a node or edge to view properties, or draw a connection between agents.
        </div>
      )}

      {/* Actions */}
      <div className="properties-actions">
        <button
          className="properties-btn properties-btn-secondary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save System'}
        </button>
        <button
          className="properties-btn properties-btn-primary"
          onClick={handleDeploy}
          disabled={deploying || !system}
        >
          {deploying ? 'Deploying...' : 'Deploy System'}
        </button>
      </div>

      {/* Deploy results */}
      {deployResult && <DeployProgress result={deployResult} />}
    </div>
  )
}

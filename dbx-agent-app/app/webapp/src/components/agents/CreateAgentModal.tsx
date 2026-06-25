import { useState, useEffect } from 'react'
import { registryApi } from '../../api/registry'
import { Collection, AgentCreate } from '../../types'
import Modal from '../common/Modal'
import Button from '../common/Button'
import './CreateAgentModal.css'

interface CreateAgentModalProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (data: AgentCreate) => Promise<void>
}

export default function CreateAgentModal({ isOpen, onClose, onCreate }: CreateAgentModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [capabilities, setCapabilities] = useState('')
  const [endpointUrl, setEndpointUrl] = useState('')
  const [collectionId, setCollectionId] = useState<number | undefined>(undefined)
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Advanced / A2A fields
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [authToken, setAuthToken] = useState('')
  const [protocolVersion, setProtocolVersion] = useState('0.3.0')
  const [streaming, setStreaming] = useState(false)
  const [pushNotifications, setPushNotifications] = useState(false)
  const [skillsJson, setSkillsJson] = useState('')
  const [status, setStatus] = useState('draft')

  useEffect(() => {
    if (isOpen) {
      registryApi.getCollections().then(setCollections)
    }
  }, [isOpen])

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Agent name is required')
      return
    }

    // Validate skills JSON if provided
    if (skillsJson.trim()) {
      try {
        JSON.parse(skillsJson.trim())
      } catch {
        setError('Skills must be valid JSON')
        return
      }
    }

    const a2aCaps = (streaming || pushNotifications)
      ? JSON.stringify({ streaming, pushNotifications })
      : undefined

    try {
      setLoading(true)
      setError(null)
      await onCreate({
        name: name.trim(),
        description: description.trim() || undefined,
        capabilities: capabilities.trim() || undefined,
        endpoint_url: endpointUrl.trim() || undefined,
        collection_id: collectionId,
        status: status || undefined,
        system_prompt: systemPrompt.trim() || undefined,
        auth_token: authToken.trim() || undefined,
        protocol_version: protocolVersion.trim() || undefined,
        a2a_capabilities: a2aCaps,
        skills: skillsJson.trim() || undefined,
      })
      resetForm()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create agent')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setName('')
    setDescription('')
    setCapabilities('')
    setEndpointUrl('')
    setCollectionId(undefined)
    setError(null)
    setShowAdvanced(false)
    setSystemPrompt('')
    setAuthToken('')
    setProtocolVersion('0.3.0')
    setStreaming(false)
    setPushNotifications(false)
    setSkillsJson('')
    setStatus('draft')
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Agent"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !name.trim()}>
            {loading ? 'Creating...' : 'Create Agent'}
          </Button>
        </>
      }
    >
      <div className="create-agent-form">
        <div className="form-group">
          <label htmlFor="agent-name">Name *</label>
          <input
            id="agent-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter agent name"
            autoFocus
          />
        </div>

        <div className="form-group">
          <label htmlFor="agent-description">Description</label>
          <textarea
            id="agent-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this agent do?"
            rows={3}
          />
        </div>

        <div className="form-group">
          <label htmlFor="agent-capabilities">Capabilities</label>
          <input
            id="agent-capabilities"
            type="text"
            value={capabilities}
            onChange={(e) => setCapabilities(e.target.value)}
            placeholder="Comma-separated tags (e.g. search, analysis, reporting)"
          />
        </div>

        <div className="form-group">
          <label htmlFor="agent-endpoint">Endpoint URL</label>
          <input
            id="agent-endpoint"
            type="text"
            value={endpointUrl}
            onChange={(e) => setEndpointUrl(e.target.value)}
            placeholder="https://..."
          />
        </div>

        <div className="form-group">
          <label htmlFor="agent-collection">Collection (optional)</label>
          <select
            id="agent-collection"
            value={collectionId ?? ''}
            onChange={(e) => setCollectionId(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">None</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <button
          type="button"
          className="advanced-toggle"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced Settings
          <span className={`advanced-toggle-icon ${showAdvanced ? 'open' : ''}`}>&#9662;</span>
        </button>

        {showAdvanced && (
          <div className="advanced-section">
            <div className="form-group">
              <label htmlFor="agent-system-prompt">System Prompt</label>
              <textarea
                id="agent-system-prompt"
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Rich persona / instructions for LLM (e.g. 'You are a research specialist. Always cite sources and provide structured summaries.')"
                rows={5}
              />
            </div>

            <div className="form-group">
              <label htmlFor="agent-status">Status</label>
              <select
                id="agent-status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="agent-auth-token">Auth Token</label>
              <input
                id="agent-auth-token"
                type="password"
                value={authToken}
                onChange={(e) => setAuthToken(e.target.value)}
                placeholder="Bearer token for inbound A2A auth"
              />
            </div>

            <div className="form-group">
              <label htmlFor="agent-protocol-version">Protocol Version</label>
              <input
                id="agent-protocol-version"
                type="text"
                value={protocolVersion}
                onChange={(e) => setProtocolVersion(e.target.value)}
                placeholder="0.3.0"
              />
            </div>

            <div className="form-group">
              <label>A2A Capabilities</label>
              <div className="checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={streaming}
                    onChange={(e) => setStreaming(e.target.checked)}
                  />
                  Streaming (SSE)
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={pushNotifications}
                    onChange={(e) => setPushNotifications(e.target.checked)}
                  />
                  Push Notifications
                </label>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="agent-skills">Skills (JSON)</label>
              <textarea
                id="agent-skills"
                value={skillsJson}
                onChange={(e) => setSkillsJson(e.target.value)}
                placeholder={'[\n  {"id": "search", "name": "Search", "description": "Search documents", "tags": ["rag"]}\n]'}
                rows={4}
              />
            </div>
          </div>
        )}

        {error && <div className="form-error">{error}</div>}
      </div>
    </Modal>
  )
}

import { useState } from 'react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import './GenerateSupervisorModal.css'

interface GenerateSupervisorModalProps {
  isOpen: boolean
  onClose: () => void
  onGenerate: (mode: 'code-first' | 'mas') => Promise<{ supervisor_url: string; code?: string }>
  collectionName: string
}

export default function GenerateSupervisorModal({ isOpen, onClose, onGenerate, collectionName }: GenerateSupervisorModalProps) {
  const [mode, setMode] = useState<'code-first' | 'mas'>('code-first')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ supervisor_url: string; code?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await onGenerate(mode)
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate supervisor')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setResult(null)
    setError(null)
    onClose()
  }

  const handleCopyCode = () => {
    if (result?.code) {
      navigator.clipboard.writeText(result.code)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`Generate Supervisor: ${collectionName}`}
    >
      <div className="generate-supervisor-modal">
        {!result ? (
          <>
            <div className="mode-selection">
              <h4>Select Supervisor Mode:</h4>

              <div className="mode-options">
                <label className={`mode-option ${mode === 'code-first' ? 'selected' : ''}`}>
                  <input
                    type="radio"
                    name="mode"
                    value="code-first"
                    checked={mode === 'code-first'}
                    onChange={() => setMode('code-first')}
                  />
                  <div>
                    <strong>Code-First Supervisor</strong>
                    <p>Generate code-first multi-agent supervisor with Langgraph</p>
                  </div>
                </label>

                <label className={`mode-option ${mode === 'mas' ? 'selected' : ''}`}>
                  <input
                    type="radio"
                    name="mode"
                    value="mas"
                    checked={mode === 'mas'}
                    onChange={() => setMode('mas')}
                  />
                  <div>
                    <strong>MAS Supervisor</strong>
                    <p>Generate declarative multi-agent system configuration</p>
                  </div>
                </label>
              </div>
            </div>

            {error && <div className="generation-error">{error}</div>}

            <div className="modal-actions">
              <Button variant="secondary" onClick={handleClose} disabled={loading}>
                Cancel
              </Button>
              <Button onClick={handleGenerate} disabled={loading}>
                {loading ? 'Generating...' : 'Generate Supervisor'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="generation-result">
              <div className="result-success">
                Supervisor generated successfully!
              </div>

              <div className="result-field">
                <label>Supervisor URL:</label>
                <div className="url-display">
                  <code>{result.supervisor_url}</code>
                  <Button
                    size="small"
                    onClick={() => navigator.clipboard.writeText(result.supervisor_url)}
                  >
                    Copy
                  </Button>
                </div>
              </div>

              {result.code && (
                <div className="result-field">
                  <label>Generated Code:</label>
                  <div className="code-display">
                    <pre>{result.code}</pre>
                    <Button size="small" onClick={handleCopyCode}>
                      Copy Code
                    </Button>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-actions">
              <Button onClick={handleClose}>Close</Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}

import { useState } from 'react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import './CreateCollectionModal.css'

interface CreateCollectionModalProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (name: string, description: string) => Promise<void>
}

export default function CreateCollectionModal({ isOpen, onClose, onCreate }: CreateCollectionModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Collection name is required')
      return
    }

    try {
      setLoading(true)
      setError(null)
      await onCreate(name.trim(), description.trim())
      setName('')
      setDescription('')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create collection')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setName('')
    setDescription('')
    setError(null)
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Collection"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !name.trim()}>
            {loading ? 'Creating...' : 'Create Collection'}
          </Button>
        </>
      }
    >
      <div className="create-collection-form">
        <div className="form-group">
          <label htmlFor="collection-name">Name *</label>
          <input
            id="collection-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter collection name"
            autoFocus
          />
        </div>

        <div className="form-group">
          <label htmlFor="collection-description">Description</label>
          <textarea
            id="collection-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter collection description (optional)"
            rows={4}
          />
        </div>

        {error && <div className="form-error">{error}</div>}
      </div>
    </Modal>
  )
}

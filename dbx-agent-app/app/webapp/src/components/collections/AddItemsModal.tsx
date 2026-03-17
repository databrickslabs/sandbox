import { useState, useEffect, useMemo } from 'react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import Badge from '../common/Badge'
import SearchBox from '../discover/SearchBox'
import { App, MCPServer, Tool } from '../../types'
import './AddItemsModal.css'

interface AddItemsModalProps {
  isOpen: boolean
  onClose: () => void
  onAdd: (type: 'app' | 'server' | 'tool', id: number) => Promise<void>
  apps: App[]
  servers: MCPServer[]
  tools: Tool[]
}

export default function AddItemsModal({ isOpen, onClose, onAdd, apps, servers, tools }: AddItemsModalProps) {
  const [search, setSearch] = useState('')
  const [selectedType, setSelectedType] = useState<'app' | 'server' | 'tool' | 'all'>('all')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setSearch('')
      setSelectedType('all')
    }
  }, [isOpen])

  const filteredItems = useMemo(() => {
    const searchLower = search.toLowerCase()
    const results: Array<{ type: 'app' | 'server' | 'tool'; id: number; name: string; description: string }> = []

    if (selectedType === 'all' || selectedType === 'app') {
      apps.forEach(app => {
        if (!search || app.name.toLowerCase().includes(searchLower)) {
          results.push({
            type: 'app',
            id: app.id,
            name: app.name,
            description: app.owner ? `Owner: ${app.owner}` : 'No owner'
          })
        }
      })
    }

    if (selectedType === 'all' || selectedType === 'server') {
      servers.forEach(server => {
        if (!search || server.server_url.toLowerCase().includes(searchLower)) {
          results.push({
            type: 'server',
            id: server.id,
            name: server.server_url,
            description: `Kind: ${server.kind}`
          })
        }
      })
    }

    if (selectedType === 'all' || selectedType === 'tool') {
      tools.forEach(tool => {
        if (!search || tool.name.toLowerCase().includes(searchLower) || tool.description?.toLowerCase().includes(searchLower)) {
          results.push({
            type: 'tool',
            id: tool.id,
            name: tool.name,
            description: tool.description || 'No description'
          })
        }
      })
    }

    return results
  }, [apps, servers, tools, search, selectedType])

  const handleAdd = async (type: 'app' | 'server' | 'tool', id: number) => {
    try {
      setLoading(true)
      await onAdd(type, id)
    } catch {
      // Error is surfaced by the parent via onAdd rejection
    } finally {
      setLoading(false)
    }
  }

  const getTypeBadgeVariant = (type: 'app' | 'server' | 'tool') => {
    switch (type) {
      case 'app':
        return 'success'
      case 'server':
        return 'warning'
      case 'tool':
        return 'primary'
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Items to Collection">
      <div className="add-items-modal">
        <div className="add-items-controls">
          <SearchBox
            value={search}
            onChange={setSearch}
            placeholder="Search items..."
          />

          <div className="type-selector">
            <button
              className={selectedType === 'all' ? 'active' : ''}
              onClick={() => setSelectedType('all')}
            >
              All
            </button>
            <button
              className={selectedType === 'app' ? 'active' : ''}
              onClick={() => setSelectedType('app')}
            >
              Apps
            </button>
            <button
              className={selectedType === 'server' ? 'active' : ''}
              onClick={() => setSelectedType('server')}
            >
              Servers
            </button>
            <button
              className={selectedType === 'tool' ? 'active' : ''}
              onClick={() => setSelectedType('tool')}
            >
              Tools
            </button>
          </div>
        </div>

        <div className="items-list">
          {filteredItems.length === 0 ? (
            <p className="no-items">No items found</p>
          ) : (
            filteredItems.map((item) => (
              <div key={`${item.type}-${item.id}`} className="item-row">
                <div className="item-info">
                  <div className="item-header">
                    <span className="item-name">{item.name}</span>
                    <Badge variant={getTypeBadgeVariant(item.type)}>{item.type}</Badge>
                  </div>
                  <p className="item-description">{item.description}</p>
                </div>
                <Button
                  size="small"
                  onClick={() => handleAdd(item.type, item.id)}
                  disabled={loading}
                >
                  Add
                </Button>
              </div>
            ))
          )}
        </div>
      </div>
    </Modal>
  )
}

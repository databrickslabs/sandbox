import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { registryApi } from '../api/registry'
import { Collection, CollectionItem, App, MCPServer, Tool } from '../types'
import CollectionCard from '../components/collections/CollectionCard'
import CreateCollectionModal from '../components/collections/CreateCollectionModal'
import AddItemsModal from '../components/collections/AddItemsModal'
import GenerateSupervisorModal from '../components/collections/GenerateSupervisorModal'
import Button from '../components/common/Button'
import Badge from '../components/common/Badge'
import Spinner from '../components/common/Spinner'
import './CollectionsPage.css'

export default function CollectionsPage() {
  const navigate = useNavigate()
  const [collections, setCollections] = useState<Collection[]>([])
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null)
  const [items, setItems] = useState<CollectionItem[]>([])
  const [apps, setApps] = useState<App[]>([])
  const [servers, setServers] = useState<MCPServer[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [addItemsModalOpen, setAddItemsModalOpen] = useState(false)
  const [generateModalOpen, setGenerateModalOpen] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (selectedCollection) {
      loadCollectionItems(selectedCollection.id)
    } else {
      setItems([])
    }
  }, [selectedCollection])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [collectionsData, appsData, serversData, toolsData] = await Promise.all([
        registryApi.getCollections(),
        registryApi.getApps(),
        registryApi.getServers(),
        registryApi.getTools()
      ])
      setCollections(collectionsData)
      setApps(appsData)
      setServers(serversData)
      setTools(toolsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadCollectionItems = async (collectionId: number) => {
    try {
      const data = await registryApi.getCollectionItems(collectionId)
      setItems(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load collection items')
    }
  }

  const handleCreateCollection = async (name: string, description: string) => {
    await registryApi.createCollection({ name, description })
    await loadData()
  }

  const handleDeleteCollection = async () => {
    if (!selectedCollection) return

    if (!confirm(`Are you sure you want to delete "${selectedCollection.name}"?`)) {
      return
    }

    try {
      await registryApi.deleteCollection(selectedCollection.id)
      setSelectedCollection(null)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete collection')
    }
  }

  const handleAddItem = async (type: 'app' | 'server' | 'tool', id: number) => {
    if (!selectedCollection) return

    const payload: { app_id?: number; mcp_server_id?: number; tool_id?: number } = {}
    if (type === 'app') payload.app_id = id
    else if (type === 'server') payload.mcp_server_id = id
    else if (type === 'tool') payload.tool_id = id

    await registryApi.addCollectionItem(selectedCollection.id, payload)
    await loadCollectionItems(selectedCollection.id)
  }

  const handleRemoveItem = async (itemId: number) => {
    if (!selectedCollection) return

    if (!confirm('Are you sure you want to remove this item from the collection?')) {
      return
    }

    try {
      await registryApi.removeCollectionItem(selectedCollection.id, itemId)
      await loadCollectionItems(selectedCollection.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove item')
    }
  }

  const handleGenerateSupervisor = async (mode: 'code-first' | 'mas') => {
    if (!selectedCollection) {
      throw new Error('No collection selected')
    }

    return await registryApi.generateSupervisor({
      collection_id: selectedCollection.id,
      mode
    })
  }

  if (loading && !collections.length) {
    return (
      <div className="collections-page">
        <div className="collections-loading">
          <Spinner size="large" />
          <p>Loading collections...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="collections-page">
      <div className="collections-header">
        <div className="collections-title">
          <h2>Collections</h2>
          <p className="collections-subtitle">Organize tools and generate supervisors</p>
        </div>
        <Button onClick={() => setCreateModalOpen(true)}>
          Create Collection
        </Button>
      </div>

      {error && (
        <div className="collections-error-banner">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="collections-layout">
        <aside className="collections-sidebar">
          <h3>Your Collections ({collections.length})</h3>
          <div className="collection-list">
            {collections.map((collection) => (
              <CollectionCard
                key={collection.id}
                collection={collection}
                isActive={selectedCollection?.id === collection.id}
                onClick={() => setSelectedCollection(collection)}
              />
            ))}
            {collections.length === 0 && (
              <div className="empty-state">
                <p>No collections yet.</p>
                <Button size="small" onClick={() => setCreateModalOpen(true)}>
                  Create Your First Collection
                </Button>
              </div>
            )}
          </div>
        </aside>

        <main className="collections-main">
          {selectedCollection ? (
            <div className="collection-detail">
              <div className="collection-detail-header">
                <div>
                  <h3>{selectedCollection.name}</h3>
                  <p>{selectedCollection.description || 'No description'}</p>
                </div>
                <div className="collection-actions">
                  <Button
                    size="small"
                    onClick={() => navigate(`/chat?collection=${selectedCollection.id}`)}
                    disabled={items.length === 0}
                  >
                    Test Collection
                  </Button>
                  <Button
                    size="small"
                    onClick={() => setGenerateModalOpen(true)}
                    disabled={items.length === 0}
                  >
                    Generate Supervisor
                  </Button>
                  <Button
                    size="small"
                    variant="danger"
                    onClick={handleDeleteCollection}
                  >
                    Delete Collection
                  </Button>
                </div>
              </div>

              <div className="collection-items-section">
                <div className="items-header">
                  <h4>Items ({items.length})</h4>
                  <Button size="small" onClick={() => setAddItemsModalOpen(true)}>
                    Add Items
                  </Button>
                </div>

                <div className="items-grid">
                  {items.map((item) => (
                    <div key={item.id} className="collection-item-card">
                      {item.app && (
                        <div className="item-content">
                          <div className="item-header">
                            <span className="item-name">{item.app.name}</span>
                            <Badge variant="success">App</Badge>
                          </div>
                          {item.app.owner && <p className="item-meta">Owner: {item.app.owner}</p>}
                        </div>
                      )}
                      {item.server && (
                        <div className="item-content">
                          <div className="item-header">
                            <span className="item-name-small">{item.server.server_url}</span>
                            <Badge variant="warning">Server</Badge>
                          </div>
                          <p className="item-meta">Kind: {item.server.kind}</p>
                        </div>
                      )}
                      {item.tool && (
                        <div className="item-content">
                          <div className="item-header">
                            <span className="item-name">{item.tool.name}</span>
                            <Badge variant="primary">Tool</Badge>
                          </div>
                          {item.tool.description && (
                            <p className="item-meta">{item.tool.description}</p>
                          )}
                        </div>
                      )}
                      <Button
                        size="small"
                        variant="danger"
                        onClick={() => handleRemoveItem(item.id)}
                      >
                        Remove
                      </Button>
                    </div>
                  ))}

                  {items.length === 0 && (
                    <div className="empty-items">
                      <p>No items in this collection yet.</p>
                      <Button size="small" onClick={() => setAddItemsModalOpen(true)}>
                        Add Items
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="collection-empty">
              <p>Select a collection to view details</p>
            </div>
          )}
        </main>
      </div>

      <CreateCollectionModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreate={handleCreateCollection}
      />

      <AddItemsModal
        isOpen={addItemsModalOpen}
        onClose={() => setAddItemsModalOpen(false)}
        onAdd={handleAddItem}
        apps={apps}
        servers={servers}
        tools={tools}
      />

      {selectedCollection && (
        <GenerateSupervisorModal
          isOpen={generateModalOpen}
          onClose={() => setGenerateModalOpen(false)}
          onGenerate={handleGenerateSupervisor}
          collectionName={selectedCollection.name}
        />
      )}
    </div>
  )
}

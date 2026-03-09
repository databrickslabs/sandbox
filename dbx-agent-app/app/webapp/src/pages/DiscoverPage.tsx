import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { registryApi } from '../api/registry'
import { App, MCPServer, Tool, DiscoverFilters, Collection, WorkspaceProfile, CatalogAsset, WorkspaceAsset, SearchResultItem, SearchResponse, Agent } from '../types'
import AppCard from '../components/discover/AppCard'
import ServerCard from '../components/discover/ServerCard'
import ToolCard from '../components/discover/ToolCard'
import WorkspaceCard from '../components/discover/WorkspaceCard'
import CatalogAssetCard from '../components/discover/CatalogAssetCard'
import WorkspaceAssetCard from '../components/discover/WorkspaceAssetCard'
import AgentCard from '../components/agents/AgentCard'
import SearchResultCard from '../components/search/SearchResultCard'
import SearchBox from '../components/discover/SearchBox'
import FilterBar from '../components/discover/FilterBar'
import DetailModal from '../components/discover/DetailModal'
import Button from '../components/common/Button'
import Badge from '../components/common/Badge'
import Spinner from '../components/common/Spinner'
import Modal from '../components/common/Modal'
import { getDefaultQuestion } from '../utils/suggestedQuestions'
import './DiscoverPage.css'

export default function DiscoverPage() {
  const navigate = useNavigate()
  const [apps, setApps] = useState<App[]>([])
  const [servers, setServers] = useState<MCPServer[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [catalogAssets, setCatalogAssets] = useState<CatalogAsset[]>([])
  const [workspaceAssets, setWorkspaceAssets] = useState<WorkspaceAsset[]>([])
  const [collections, setCollections] = useState<Collection[]>([])
  const [workspaceProfiles, setWorkspaceProfiles] = useState<WorkspaceProfile[]>([])
  const [workspacesLoading, setWorkspacesLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [crawling, setCrawling] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Semantic search state
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([])
  const [searchMode, setSearchMode] = useState<string | null>(null)
  const [searching, setSearching] = useState(false)
  const [embedding, setEmbedding] = useState(false)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [filters, setFilters] = useState<DiscoverFilters>({
    search: '',
    tags: [],
    owner: '',
    type: 'all'
  })

  const [detailModal, setDetailModal] = useState<{
    isOpen: boolean
    item: App | MCPServer | Tool | CatalogAsset | WorkspaceAsset | null
    type: string
  }>({
    isOpen: false,
    item: null,
    type: 'app'
  })

  const [addToCollectionModal, setAddToCollectionModal] = useState<{
    isOpen: boolean
    item: { type: 'app' | 'server' | 'tool'; id: number } | null
  }>({
    isOpen: false,
    item: null
  })

  useEffect(() => {
    loadData()
    loadWorkspaces()
  }, [])

  // Debounced semantic search — fires 400ms after user stops typing
  const executeSearch = useCallback(async (query: string, typeFilter: string, ownerFilter: string) => {
    if (!query || query.length < 2) {
      setSearchResults([])
      setSearchMode(null)
      return
    }

    try {
      setSearching(true)
      const types = typeFilter !== 'all' ? [typeFilter] : undefined
      const owner = ownerFilter || undefined
      const response: SearchResponse = await registryApi.search({
        query,
        types,
        owner,
        limit: 50,
      })
      setSearchResults(response.results)
      setSearchMode(response.search_mode)
    } catch {
      // Fall back to client-side filtering if search API fails
      setSearchResults([])
      setSearchMode(null)
    } finally {
      setSearching(false)
    }
  }, [])

  // Trigger debounced search on filter changes
  useEffect(() => {
    if (searchTimerRef.current) {
      clearTimeout(searchTimerRef.current)
    }

    if (filters.search && filters.search.length >= 2) {
      searchTimerRef.current = setTimeout(() => {
        executeSearch(filters.search, filters.type, filters.owner)
      }, 400)
    } else {
      setSearchResults([])
      setSearchMode(null)
    }

    return () => {
      if (searchTimerRef.current) {
        clearTimeout(searchTimerRef.current)
      }
    }
  }, [filters.search, filters.type, filters.owner, executeSearch])

  const isSemanticSearchActive = searchMode !== null && searchResults.length > 0

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [appsData, serversData, toolsData, agentsData, collectionsData, catalogData, workspaceData] = await Promise.all([
        registryApi.getApps(),
        registryApi.getServers(),
        registryApi.getTools(),
        registryApi.getAgents(),
        registryApi.getCollections(),
        registryApi.getCatalogAssets({ page_size: 200 }),
        registryApi.getWorkspaceAssets({ page_size: 200 }),
      ])
      setApps(appsData)
      setServers(serversData)
      setTools(toolsData)
      setAgents(agentsData)
      setCollections(collectionsData)
      setCatalogAssets(catalogData)
      setWorkspaceAssets(workspaceData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadWorkspaces = async () => {
    try {
      setWorkspacesLoading(true)
      const data = await registryApi.getWorkspaceProfiles()
      setWorkspaceProfiles(data.profiles)
    } catch {
      // Non-critical — don't block the page if profiles fail to load
    } finally {
      setWorkspacesLoading(false)
    }
  }

  const handleWorkspaceDiscover = async (profile: WorkspaceProfile) => {
    try {
      setLoading(true)
      await registryApi.refreshDiscoveryWithProfile(profile.name)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to discover workspace')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    try {
      setLoading(true)
      await registryApi.refreshDiscovery()
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh discovery')
    } finally {
      setLoading(false)
    }
  }

  const handleCrawlCatalog = async () => {
    try {
      setCrawling('catalog')
      setError(null)
      const result = await registryApi.crawlCatalog()
      if (result.status === 'failed') {
        setError(`Catalog crawl failed: ${result.errors.join(', ')}`)
      }
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to crawl catalog')
    } finally {
      setCrawling(null)
    }
  }

  const handleCrawlWorkspace = async () => {
    try {
      setCrawling('workspace')
      setError(null)
      const result = await registryApi.crawlWorkspace()
      if (result.status === 'failed') {
        setError(`Workspace crawl failed: ${result.errors.join(', ')}`)
      }
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to crawl workspace')
    } finally {
      setCrawling(null)
    }
  }

  const handleEmbedAll = async () => {
    try {
      setEmbedding(true)
      setError(null)
      await registryApi.embedAllAssets()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate embeddings')
    } finally {
      setEmbedding(false)
    }
  }

  const handleAddToCollection = async (collectionId: number) => {
    if (!addToCollectionModal.item) return

    try {
      const { type, id } = addToCollectionModal.item
      const payload: { app_id?: number; mcp_server_id?: number; tool_id?: number } = {}

      if (type === 'app') payload.app_id = id
      else if (type === 'server') payload.mcp_server_id = id
      else if (type === 'tool') payload.tool_id = id

      await registryApi.addCollectionItem(collectionId, payload)
      setAddToCollectionModal({ isOpen: false, item: null })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add to collection')
    }
  }

  const handleAskAI = (asset: CatalogAsset | WorkspaceAsset, assetType: string) => {
    const question = getDefaultQuestion(asset, assetType)
    navigate(`/chat?q=${encodeURIComponent(question)}`)
  }

  const handleAskAIQuestion = (question: string) => {
    navigate(`/chat?q=${encodeURIComponent(question)}`)
  }

  const owners = useMemo(() => {
    const ownerSet = new Set<string>()
    apps.forEach(app => { if (app.owner) ownerSet.add(app.owner) })
    catalogAssets.forEach(a => { if (a.owner) ownerSet.add(a.owner) })
    workspaceAssets.forEach(a => { if (a.owner) ownerSet.add(a.owner) })
    return Array.from(ownerSet).sort()
  }, [apps, catalogAssets, workspaceAssets])

  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    apps.forEach(app => {
      if (app.tags) {
        app.tags.split(',').forEach(tag => tagSet.add(tag.trim()))
      }
    })
    return Array.from(tagSet).sort()
  }, [apps])

  // --- Client-side filtering (used when semantic search is not active) ---

  const isTypeMatch = (itemType: string) => {
    return filters.type === 'all' || filters.type === itemType
  }

  const matchesSearch = (searchable: string) => {
    if (!filters.search) return true
    return searchable.toLowerCase().includes(filters.search.toLowerCase())
  }

  const filteredApps = useMemo(() => {
    if (isSemanticSearchActive) return []
    // Filter out apps that have agent cards (those are shown as agents instead)
    const agentAppUrls = new Set(agents.map(a => a.endpoint_url))
    return apps.filter(app => {
      // Exclude apps that have an agent (to avoid duplication)
      if (agentAppUrls.has(app.url)) return false
      if (!isTypeMatch('app')) return false
      if (!matchesSearch(app.name)) return false
      if (filters.owner && app.owner !== filters.owner) return false
      if (filters.tags.length > 0) {
        const appTags = app.tags ? app.tags.split(',').map(t => t.trim()) : []
        if (!filters.tags.some(tag => appTags.includes(tag))) return false
      }
      return true
    })
  }, [apps, agents, filters, isSemanticSearchActive])

  const filteredServers = useMemo(() => {
    if (isSemanticSearchActive) return []
    return servers.filter(server => {
      if (!isTypeMatch('server')) return false
      return matchesSearch(server.server_url)
    })
  }, [servers, filters, isSemanticSearchActive])

  const filteredTools = useMemo(() => {
    if (isSemanticSearchActive) return []
    return tools.filter(tool => {
      if (!isTypeMatch('tool')) return false
      return matchesSearch(`${tool.name} ${tool.description || ''}`)
    })
  }, [tools, filters, isSemanticSearchActive])

  const filteredAgents = useMemo(() => {
    if (isSemanticSearchActive) return []
    return agents.filter(agent => {
      if (!isTypeMatch('agent')) return false
      if (!matchesSearch(`${agent.name} ${agent.description || ''} ${agent.capabilities || ''}`)) return false
      return true
    })
  }, [agents, filters, isSemanticSearchActive])

  const filteredCatalogAssets = useMemo(() => {
    if (isSemanticSearchActive) return []
    return catalogAssets.filter(asset => {
      if (!isTypeMatch(asset.asset_type)) return false
      if (!matchesSearch(`${asset.full_name} ${asset.comment || ''}`)) return false
      if (filters.owner && asset.owner !== filters.owner) return false
      return true
    })
  }, [catalogAssets, filters, isSemanticSearchActive])

  const filteredWorkspaceAssets = useMemo(() => {
    if (isSemanticSearchActive) return []
    return workspaceAssets.filter(asset => {
      if (!isTypeMatch(asset.asset_type)) return false
      if (!matchesSearch(`${asset.name} ${asset.description || ''} ${asset.path}`)) return false
      if (filters.owner && asset.owner !== filters.owner) return false
      return true
    })
  }, [workspaceAssets, filters, isSemanticSearchActive])

  const hasAnyData = apps.length > 0 || servers.length > 0 || tools.length > 0 || agents.length > 0 || catalogAssets.length > 0 || workspaceAssets.length > 0

  if (loading && !hasAnyData) {
    return (
      <div className="discover-page">
        <div className="discover-loading">
          <Spinner size="large" />
          <p>Loading discovery data...</p>
        </div>
      </div>
    )
  }

  if (error && !hasAnyData) {
    return (
      <div className="discover-page">
        <div className="discover-error">
          <p>Error: {error}</p>
          <Button onClick={loadData}>Retry</Button>
        </div>
      </div>
    )
  }

  const browseResults = filteredApps.length + filteredServers.length + filteredTools.length + filteredAgents.length
    + filteredCatalogAssets.length + filteredWorkspaceAssets.length
  const totalResults = isSemanticSearchActive ? searchResults.length : browseResults

  return (
    <div className="discover-page">
      <div className="discover-header">
        <div className="discover-title">
          <h2>Discover</h2>
          <p className="discover-subtitle">Search across your entire Databricks lakehouse</p>
        </div>
        <div className="discover-actions">
          <Button onClick={handleCrawlCatalog} disabled={crawling !== null} variant="secondary">
            {crawling === 'catalog' ? 'Crawling Catalog...' : 'Index Catalog'}
          </Button>
          <Button onClick={handleCrawlWorkspace} disabled={crawling !== null} variant="secondary">
            {crawling === 'workspace' ? 'Crawling Workspace...' : 'Index Workspace'}
          </Button>
          <Button onClick={handleEmbedAll} disabled={embedding} variant="secondary">
            {embedding ? 'Embedding...' : 'Build Index'}
          </Button>
          <Button onClick={handleRefresh} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh MCP'}
          </Button>
        </div>
      </div>

      <div className="discover-controls">
        <SearchBox
          value={filters.search}
          onChange={(search) => setFilters({ ...filters, search })}
          placeholder="Search tables, notebooks, jobs, tools, and more..."
        />
      </div>

      <FilterBar
        filters={filters}
        onFiltersChange={(newFilters) => setFilters({ ...filters, ...newFilters })}
        owners={owners}
        allTags={allTags}
      />

      <div className="discover-stats">
        <div className="stat-item">
          <span className="stat-label">Total:</span>
          <span className="stat-value">{totalResults}</span>
        </div>
        {isSemanticSearchActive && (
          <div className="stat-item">
            <span className="stat-label">Mode:</span>
            <Badge variant={searchMode === 'hybrid' ? 'success' : searchMode === 'semantic' ? 'primary' : 'default'}>
              {searchMode}
            </Badge>
          </div>
        )}
        {searching && (
          <div className="stat-item">
            <Spinner size="small" />
          </div>
        )}
        {!isSemanticSearchActive && filteredCatalogAssets.length > 0 && (
          <div className="stat-item">
            <span className="stat-label">Catalog:</span>
            <span className="stat-value">{filteredCatalogAssets.length}</span>
          </div>
        )}
        {!isSemanticSearchActive && filteredWorkspaceAssets.length > 0 && (
          <div className="stat-item">
            <span className="stat-label">Workspace:</span>
            <span className="stat-value">{filteredWorkspaceAssets.length}</span>
          </div>
        )}
        {!isSemanticSearchActive && filteredApps.length > 0 && (
          <div className="stat-item">
            <span className="stat-label">Apps:</span>
            <span className="stat-value">{filteredApps.length}</span>
          </div>
        )}
        {!isSemanticSearchActive && filteredServers.length > 0 && (
          <div className="stat-item">
            <span className="stat-label">Servers:</span>
            <span className="stat-value">{filteredServers.length}</span>
          </div>
        )}
        {!isSemanticSearchActive && filteredTools.length > 0 && (
          <div className="stat-item">
            <span className="stat-label">Tools:</span>
            <span className="stat-value">{filteredTools.length}</span>
          </div>
        )}
      </div>

      {workspaceProfiles.length > 0 && !isSemanticSearchActive && (
        <div className="workspace-section">
          <h3 className="workspace-section-title">Workspaces</h3>
          <p className="workspace-section-subtitle">
            Databricks CLI profiles from ~/.databrickscfg
          </p>
          {workspacesLoading ? (
            <Spinner size="small" />
          ) : (
            <div className="workspace-grid">
              {workspaceProfiles.map((profile) => (
                <WorkspaceCard
                  key={profile.name}
                  profile={profile}
                  onDiscover={handleWorkspaceDiscover}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="discover-error-banner">
          {error}
        </div>
      )}

      {/* Semantic search results view */}
      {isSemanticSearchActive && (
        <div className="discover-grid">
          {searchResults.map((result, idx) => (
            <SearchResultCard
              key={`search-${result.asset_type}-${result.asset_id}-${idx}`}
              result={result}
              onViewDetails={() => {
                setDetailModal({
                  isOpen: true,
                  item: null,
                  type: result.asset_type,
                })
              }}
            />
          ))}
        </div>
      )}

      {/* Browse view (no search or fallback) */}
      {!isSemanticSearchActive && (
        <div className="discover-grid">
          {filteredCatalogAssets.map((asset) => (
            <CatalogAssetCard
              key={`catalog-${asset.id}`}
              asset={asset}
              onViewDetails={(a) => setDetailModal({ isOpen: true, item: a, type: a.asset_type })}
              onAddToCollection={() => {}}
              onAskAI={(a) => handleAskAI(a, a.asset_type)}
            />
          ))}

          {filteredWorkspaceAssets.map((asset) => (
            <WorkspaceAssetCard
              key={`workspace-${asset.id}`}
              asset={asset}
              onViewDetails={(a) => setDetailModal({ isOpen: true, item: a, type: a.asset_type })}
              onAskAI={(a) => handleAskAI(a, a.asset_type)}
            />
          ))}

          {filteredApps.map((app) => (
            <AppCard
              key={`app-${app.id}`}
              app={app}
              onViewDetails={(app) => setDetailModal({ isOpen: true, item: app, type: 'app' })}
              onAddToCollection={(app) => setAddToCollectionModal({ isOpen: true, item: { type: 'app', id: app.id } })}
            />
          ))}

          {filteredServers.map((server) => (
            <ServerCard
              key={`server-${server.id}`}
              server={server}
              onViewDetails={(server) => setDetailModal({ isOpen: true, item: server, type: 'server' })}
              onAddToCollection={(server) => setAddToCollectionModal({ isOpen: true, item: { type: 'server', id: server.id } })}
            />
          ))}

          {filteredTools.map((tool) => (
            <ToolCard
              key={`tool-${tool.id}`}
              tool={tool}
              onViewDetails={(tool) => setDetailModal({ isOpen: true, item: tool, type: 'tool' })}
              onAddToCollection={(tool) => setAddToCollectionModal({ isOpen: true, item: { type: 'tool', id: tool.id } })}
            />
          ))}

          {filteredAgents.map((agent) => (
            <AgentCard
              key={`agent-${agent.id}`}
              agent={agent}
              isActive={false}
              onClick={() => navigate(`/agents`)}
            />
          ))}
        </div>
      )}

      {totalResults === 0 && !loading && !searching && (
        <div className="discover-empty">
          {!hasAnyData ? (
            <>
              <h3>No Data Available</h3>
              <p>Use the buttons above to index your Unity Catalog, workspace objects, or discover MCP servers.</p>
            </>
          ) : filters.search ? (
            <>
              <p>No results for "{filters.search}"</p>
              <Button onClick={() => setFilters({ search: '', tags: [], owner: '', type: 'all' })}>
                Clear Search
              </Button>
            </>
          ) : (
            <>
              <p>No items match your filter criteria.</p>
              <Button onClick={() => setFilters({ search: '', tags: [], owner: '', type: 'all' })}>
                Clear Filters
              </Button>
            </>
          )}
        </div>
      )}

      <DetailModal
        isOpen={detailModal.isOpen}
        onClose={() => setDetailModal({ isOpen: false, item: null, type: 'app' })}
        item={detailModal.item}
        type={detailModal.type}
        onAskAI={handleAskAIQuestion}
      />

      <Modal
        isOpen={addToCollectionModal.isOpen}
        onClose={() => setAddToCollectionModal({ isOpen: false, item: null })}
        title="Add to Collection"
      >
        <div className="add-to-collection-modal">
          {collections.length === 0 ? (
            <p>No collections available. Create a collection first.</p>
          ) : (
            <div className="collection-list">
              {collections.map((collection) => (
                <div key={collection.id} className="collection-option">
                  <div>
                    <h4>{collection.name}</h4>
                    <p>{collection.description || 'No description'}</p>
                  </div>
                  <Button size="small" onClick={() => handleAddToCollection(collection.id)}>
                    Add
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}

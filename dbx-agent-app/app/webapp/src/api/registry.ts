import { registryClient } from './client'
import {
  App,
  MCPServer,
  Tool,
  Collection,
  CollectionCreate,
  CollectionItem,
  Agent,
  AgentCreate,
  A2AAgentCard,
  A2ATask,
  SupervisorGenerateRequest,
  SupervisorGenerateResponse,
  WorkspaceProfilesResponse,
  CatalogAsset,
  WorkspaceAsset,
  CatalogCrawlResponse,
  WorkspaceCrawlResponse,
  SearchResponse,
  EmbedStatusResponse,
  LineageResponse,
  ImpactAnalysisResponse,
  AssetRelationship,
  LineageCrawlResponse,
  AuditLogEntry,
} from '../types'

export const registryApi = {
  async refreshDiscovery(): Promise<void> {
    await registryClient.post('/discovery/refresh')
  },

  async getApps(): Promise<App[]> {
    try {
      const response = await registryClient.get('/apps')
      // Handle paginated response or direct array
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getServers(): Promise<MCPServer[]> {
    try {
      const response = await registryClient.get('/mcp_servers')
      // Handle paginated response or direct array
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getTools(serverId?: number): Promise<Tool[]> {
    try {
      const params = serverId ? { mcp_server_id: serverId } : {}
      const response = await registryClient.get('/tools', { params })
      // Handle paginated response or direct array
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getCollections(): Promise<Collection[]> {
    try {
      const response = await registryClient.get('/collections')
      // Handle paginated response or direct array
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getCollection(id: number): Promise<Collection> {
    const response = await registryClient.get(`/collections/${id}`)
    return response.data
  },

  async createCollection(data: CollectionCreate): Promise<Collection> {
    const response = await registryClient.post('/collections', data)
    return response.data
  },

  async updateCollection(id: number, data: Partial<CollectionCreate>): Promise<Collection> {
    const response = await registryClient.put(`/collections/${id}`, data)
    return response.data
  },

  async deleteCollection(id: number): Promise<void> {
    await registryClient.delete(`/collections/${id}`)
  },

  async getCollectionItems(collectionId: number): Promise<CollectionItem[]> {
    try {
      const response = await registryClient.get(`/collections/${collectionId}/items`)
      // Handle paginated response or direct array
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async addCollectionItem(collectionId: number, item: {
    app_id?: number
    mcp_server_id?: number
    tool_id?: number
  }): Promise<CollectionItem> {
    const response = await registryClient.post(`/collections/${collectionId}/items`, item)
    return response.data
  },

  async removeCollectionItem(collectionId: number, itemId: number): Promise<void> {
    await registryClient.delete(`/collections/${collectionId}/items/${itemId}`)
  },

  async generateSupervisor(data: SupervisorGenerateRequest): Promise<SupervisorGenerateResponse> {
    const response = await registryClient.post('/supervisors/generate', data)
    return response.data
  },

  async getWorkspaceProfiles(): Promise<WorkspaceProfilesResponse> {
    const response = await registryClient.get('/discovery/workspaces')
    return response.data
  },

  async getAgents(): Promise<Agent[]> {
    try {
      const response = await registryClient.get('/agents')
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getAgent(id: number): Promise<Agent> {
    const response = await registryClient.get(`/agents/${id}`)
    return response.data
  },

  async createAgent(data: AgentCreate): Promise<Agent> {
    const response = await registryClient.post('/agents', data)
    return response.data
  },

  async updateAgent(id: number, data: Partial<AgentCreate>): Promise<Agent> {
    const response = await registryClient.put(`/agents/${id}`, data)
    return response.data
  },

  async deleteAgent(id: number): Promise<void> {
    await registryClient.delete(`/agents/${id}`)
  },

  async getAgentCard(id: number): Promise<A2AAgentCard> {
    const response = await registryClient.get(`/agents/${id}/card`)
    return response.data
  },

  async getA2ATasks(agentId: number): Promise<A2ATask[]> {
    try {
      const response = await registryClient.post(`/a2a/${agentId}`, {
        jsonrpc: '2.0',
        id: 1,
        method: 'tasks/list',
        params: {}
      })
      return response.data?.result?.tasks || []
    } catch {
      return []
    }
  },

  async refreshDiscoveryWithProfile(profile: string): Promise<void> {
    await registryClient.post('/discovery/refresh', {
      discover_workspace: true,
      databricks_profile: profile
    })
  },

  // --- Catalog Assets ---

  async getCatalogAssets(params?: {
    asset_type?: string
    catalog?: string
    schema_name?: string
    search?: string
    owner?: string
    page?: number
    page_size?: number
  }): Promise<CatalogAsset[]> {
    try {
      const response = await registryClient.get('/catalog-assets', { params })
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getCatalogAsset(id: number): Promise<CatalogAsset> {
    const response = await registryClient.get(`/catalog-assets/${id}`)
    return response.data
  },

  async crawlCatalog(params?: {
    catalogs?: string[]
    include_columns?: boolean
    databricks_profile?: string
  }): Promise<CatalogCrawlResponse> {
    const response = await registryClient.post('/catalog-assets/crawl', params || {})
    return response.data
  },

  // --- Workspace Assets ---

  async getWorkspaceAssets(params?: {
    asset_type?: string
    search?: string
    owner?: string
    workspace_host?: string
    page?: number
    page_size?: number
  }): Promise<WorkspaceAsset[]> {
    try {
      const response = await registryClient.get('/workspace-assets', { params })
      if (response.data.items && Array.isArray(response.data.items)) {
        return response.data.items
      }
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getWorkspaceAsset(id: number): Promise<WorkspaceAsset> {
    const response = await registryClient.get(`/workspace-assets/${id}`)
    return response.data
  },

  async crawlWorkspace(params?: {
    asset_types?: string[]
    root_path?: string
    databricks_profile?: string
  }): Promise<WorkspaceCrawlResponse> {
    const response = await registryClient.post('/workspace-assets/crawl', params || {})
    return response.data
  },

  // --- Semantic Search ---

  async search(params: {
    query: string
    types?: string[]
    catalogs?: string[]
    owner?: string
    limit?: number
  }): Promise<SearchResponse> {
    const response = await registryClient.post('/search', params)
    return response.data
  },

  async embedAllAssets(): Promise<EmbedStatusResponse> {
    const response = await registryClient.post('/search/embed-all')
    return response.data
  },

  async getEmbedStatus(): Promise<EmbedStatusResponse> {
    const response = await registryClient.get('/search/embed-status')
    return response.data
  },

  // --- Lineage ---

  async getLineage(assetType: string, assetId: number, params?: {
    direction?: 'upstream' | 'downstream' | 'both'
    max_depth?: number
  }): Promise<LineageResponse> {
    const response = await registryClient.get(`/lineage/${assetType}/${assetId}`, { params })
    return response.data
  },

  async getImpactAnalysis(assetType: string, assetId: number, params?: {
    max_depth?: number
  }): Promise<ImpactAnalysisResponse> {
    const response = await registryClient.get(`/lineage/${assetType}/${assetId}/impact`, { params })
    return response.data
  },

  async crawlLineage(params?: {
    databricks_profile?: string
    include_column_lineage?: boolean
  }): Promise<LineageCrawlResponse> {
    const response = await registryClient.post('/lineage/crawl', params || {})
    return response.data
  },

  async getRelationships(params?: {
    source_type?: string
    target_type?: string
    relationship_type?: string
    page?: number
    page_size?: number
  }): Promise<AssetRelationship[]> {
    const response = await registryClient.get('/lineage/relationships', { params })
    return response.data
  },

  // --- Audit Log ---

  async getAuditLog(params?: {
    user_email?: string
    action?: string
    resource_type?: string
    date_from?: string
    date_to?: string
    page?: number
    page_size?: number
  }): Promise<{ items: AuditLogEntry[]; total: number; page: number; page_size: number; total_pages: number }> {
    const response = await registryClient.get('/audit-log', { params })
    return response.data
  },
}

import { useEffect, useState } from 'react'
import { registryApi } from '../api/registry'
import { LineageResponse, ImpactAnalysisResponse, CatalogAsset, WorkspaceAsset } from '../types'
import LineageGraph from '../components/lineage/LineageGraph'
import Button from '../components/common/Button'
import Badge from '../components/common/Badge'
import Spinner from '../components/common/Spinner'
import './LineagePage.css'

interface SelectedAsset {
  type: string
  id: number
  name: string
}

export default function LineagePage() {
  const [catalogAssets, setCatalogAssets] = useState<CatalogAsset[]>([])
  const [workspaceAssets, setWorkspaceAssets] = useState<WorkspaceAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [crawling, setCrawling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [selectedAsset, setSelectedAsset] = useState<SelectedAsset | null>(null)
  const [lineage, setLineage] = useState<LineageResponse | null>(null)
  const [impact, setImpact] = useState<ImpactAnalysisResponse | null>(null)
  const [lineageLoading, setLineageLoading] = useState(false)
  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>('both')
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    loadAssets()
  }, [])

  const loadAssets = async () => {
    try {
      setLoading(true)
      const [catalog, workspace] = await Promise.all([
        registryApi.getCatalogAssets({ page_size: 500 }),
        registryApi.getWorkspaceAssets({ page_size: 500 }),
      ])
      setCatalogAssets(catalog)
      setWorkspaceAssets(workspace)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assets')
    } finally {
      setLoading(false)
    }
  }

  const handleCrawlLineage = async () => {
    try {
      setCrawling(true)
      setError(null)
      const result = await registryApi.crawlLineage()
      if (result.errors.length > 0) {
        setError(`Crawl completed with errors: ${result.errors.join(', ')}`)
      }
      // Reload lineage if an asset is selected
      if (selectedAsset) {
        await loadLineage(selectedAsset.type, selectedAsset.id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to crawl lineage')
    } finally {
      setCrawling(false)
    }
  }

  const loadLineage = async (assetType: string, assetId: number) => {
    try {
      setLineageLoading(true)
      const [lineageData, impactData] = await Promise.all([
        registryApi.getLineage(assetType, assetId, { direction, max_depth: 3 }),
        registryApi.getImpactAnalysis(assetType, assetId, { max_depth: 5 }),
      ])
      setLineage(lineageData)
      setImpact(impactData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lineage')
    } finally {
      setLineageLoading(false)
    }
  }

  const handleSelectAsset = (type: string, id: number, name: string) => {
    setSelectedAsset({ type, id, name })
    loadLineage(type, id)
  }

  const handleDirectionChange = (dir: 'upstream' | 'downstream' | 'both') => {
    setDirection(dir)
    if (selectedAsset) {
      setLineageLoading(true)
      registryApi.getLineage(selectedAsset.type, selectedAsset.id, { direction: dir, max_depth: 3 })
        .then(setLineage)
        .finally(() => setLineageLoading(false))
    }
  }

  const filteredCatalog = catalogAssets.filter(a =>
    !searchText || a.full_name.toLowerCase().includes(searchText.toLowerCase())
  )

  const filteredWorkspace = workspaceAssets.filter(a =>
    !searchText || a.name.toLowerCase().includes(searchText.toLowerCase())
  )

  if (loading) {
    return (
      <div className="lineage-page">
        <div className="lineage-page-loading">
          <Spinner size="large" />
          <p>Loading assets...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="lineage-page">
      <div className="lineage-page-header">
        <div>
          <h2>Lineage</h2>
          <p className="lineage-subtitle">Explore data flow and dependencies across your lakehouse</p>
        </div>
        <Button onClick={handleCrawlLineage} disabled={crawling}>
          {crawling ? 'Crawling...' : 'Crawl Lineage'}
        </Button>
      </div>

      {error && (
        <div className="lineage-error-banner">{error}</div>
      )}

      <div className="lineage-layout">
        {/* Asset picker sidebar */}
        <div className="lineage-sidebar">
          <input
            className="lineage-search-input"
            placeholder="Search assets..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />

          <div className="lineage-asset-list">
            {filteredCatalog.length > 0 && (
              <div className="lineage-asset-group">
                <h4>Catalog ({filteredCatalog.length})</h4>
                {filteredCatalog.slice(0, 50).map((asset) => (
                  <button
                    key={`c-${asset.id}`}
                    className={`lineage-asset-item ${
                      selectedAsset?.type === asset.asset_type && selectedAsset?.id === asset.id ? 'active' : ''
                    }`}
                    onClick={() => handleSelectAsset(asset.asset_type, asset.id, asset.full_name)}
                  >
                    <Badge variant="primary">{asset.asset_type}</Badge>
                    <span className="lineage-asset-name">{asset.name}</span>
                  </button>
                ))}
              </div>
            )}

            {filteredWorkspace.length > 0 && (
              <div className="lineage-asset-group">
                <h4>Workspace ({filteredWorkspace.length})</h4>
                {filteredWorkspace.slice(0, 50).map((asset) => (
                  <button
                    key={`w-${asset.id}`}
                    className={`lineage-asset-item ${
                      selectedAsset?.type === asset.asset_type && selectedAsset?.id === asset.id ? 'active' : ''
                    }`}
                    onClick={() => handleSelectAsset(asset.asset_type, asset.id, asset.name)}
                  >
                    <Badge variant="success">{asset.asset_type}</Badge>
                    <span className="lineage-asset-name">{asset.name}</span>
                  </button>
                ))}
              </div>
            )}

            {filteredCatalog.length === 0 && filteredWorkspace.length === 0 && (
              <p className="lineage-no-assets">
                No assets indexed yet. Use Discover to index your catalog and workspace first.
              </p>
            )}
          </div>
        </div>

        {/* Graph area */}
        <div className="lineage-main">
          {selectedAsset && (
            <div className="lineage-toolbar">
              <span className="lineage-selected-label">
                Showing lineage for: <strong>{selectedAsset.name}</strong>
              </span>
              <div className="lineage-direction-toggle">
                {(['upstream', 'both', 'downstream'] as const).map((dir) => (
                  <button
                    key={dir}
                    className={`direction-btn ${direction === dir ? 'active' : ''}`}
                    onClick={() => handleDirectionChange(dir)}
                  >
                    {dir === 'upstream' ? 'Upstream' : dir === 'downstream' ? 'Downstream' : 'Both'}
                  </button>
                ))}
              </div>
            </div>
          )}

          {lineageLoading ? (
            <div className="lineage-page-loading">
              <Spinner size="large" />
              <p>Loading lineage...</p>
            </div>
          ) : lineage ? (
            <>
              <LineageGraph
                nodes={lineage.nodes}
                edges={lineage.edges}
                rootType={lineage.root_type}
                rootId={lineage.root_id}
                onNodeClick={(type, id) => {
                  const name = lineage.nodes.find(n => n.asset_type === type && n.asset_id === id)?.name || ''
                  handleSelectAsset(type, id, name)
                }}
              />

              {/* Impact analysis summary */}
              {impact && impact.total_affected > 0 && (
                <div className="lineage-impact-section">
                  <h4>Impact Analysis</h4>
                  <p>
                    Changing this asset could affect <strong>{impact.total_affected}</strong> downstream asset{impact.total_affected !== 1 ? 's' : ''}:
                  </p>
                  <div className="lineage-impact-list">
                    {impact.affected_assets.map((a, idx) => (
                      <div key={idx} className="lineage-impact-item">
                        <Badge variant="danger">{a.asset_type}</Badge>
                        <span>{a.name}</span>
                        <span className="lineage-impact-depth">depth {a.depth}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Legend */}
              <div className="lineage-legend">
                <div className="lineage-legend-item">
                  <div className="lineage-legend-line" style={{ backgroundColor: '#1a73e8' }} />
                  <span>reads from</span>
                </div>
                <div className="lineage-legend-item">
                  <div className="lineage-legend-line" style={{ backgroundColor: '#ea4335' }} />
                  <span>writes to</span>
                </div>
                <div className="lineage-legend-item">
                  <div className="lineage-legend-line" style={{ backgroundColor: '#f9ab00' }} />
                  <span>depends on</span>
                </div>
                <div className="lineage-legend-item">
                  <div className="lineage-legend-line" style={{ backgroundColor: '#00897b' }} />
                  <span>scheduled by</span>
                </div>
              </div>
            </>
          ) : (
            <div className="lineage-placeholder">
              <h3>Select an asset</h3>
              <p>Choose an asset from the sidebar to explore its lineage and dependencies.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

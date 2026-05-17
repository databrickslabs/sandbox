import Modal from '../common/Modal'
import Badge from '../common/Badge'
import SuggestedQuestions from './SuggestedQuestions'
import { App, MCPServer, Tool, CatalogAsset, WorkspaceAsset } from '../../types'
import { getCatalogAssetQuestions, getWorkspaceAssetQuestions } from '../../utils/suggestedQuestions'
import './DetailModal.css'

interface DetailModalProps {
  isOpen: boolean
  onClose: () => void
  item: App | MCPServer | Tool | CatalogAsset | WorkspaceAsset | null
  type: string
  onAskAI?: (question: string) => void
}

const CATALOG_TYPES = ['table', 'view', 'function', 'model', 'volume']
const WORKSPACE_TYPES = ['notebook', 'job', 'dashboard', 'pipeline', 'cluster', 'experiment']

export default function DetailModal({ isOpen, onClose, item, type, onAskAI }: DetailModalProps) {
  if (!item) return null

  const renderAppDetails = (app: App) => (
    <div className="detail-content">
      <div className="detail-row">
        <strong>ID:</strong>
        <span>{app.id}</span>
      </div>
      <div className="detail-row">
        <strong>Name:</strong>
        <span>{app.name}</span>
      </div>
      {app.owner && (
        <div className="detail-row">
          <strong>Owner:</strong>
          <span>{app.owner}</span>
        </div>
      )}
      {app.url && (
        <div className="detail-row">
          <strong>URL:</strong>
          <a href={app.url} target="_blank" rel="noopener noreferrer">
            {app.url}
          </a>
        </div>
      )}
      {app.manifest_url && (
        <div className="detail-row">
          <strong>Manifest URL:</strong>
          <a href={app.manifest_url} target="_blank" rel="noopener noreferrer">
            {app.manifest_url}
          </a>
        </div>
      )}
      {app.tags && (
        <div className="detail-row">
          <strong>Tags:</strong>
          <div className="detail-tags">
            {app.tags.split(',').map((tag, i) => (
              <Badge key={i}>{tag.trim()}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  const renderServerDetails = (server: MCPServer) => (
    <div className="detail-content">
      <div className="detail-row">
        <strong>ID:</strong>
        <span>{server.id}</span>
      </div>
      <div className="detail-row">
        <strong>Server URL:</strong>
        <code className="detail-code">{server.server_url}</code>
      </div>
      <div className="detail-row">
        <strong>Kind:</strong>
        <Badge>{server.kind}</Badge>
      </div>
      {server.app_id && (
        <div className="detail-row">
          <strong>App ID:</strong>
          <span>{server.app_id}</span>
        </div>
      )}
      {server.uc_connection && (
        <div className="detail-row">
          <strong>UC Connection:</strong>
          <span>{server.uc_connection}</span>
        </div>
      )}
      {server.scopes && (
        <div className="detail-row">
          <strong>Scopes:</strong>
          <code className="detail-code">{server.scopes}</code>
        </div>
      )}
    </div>
  )

  const renderToolDetails = (tool: Tool) => (
    <div className="detail-content">
      <div className="detail-row">
        <strong>ID:</strong>
        <span>{tool.id}</span>
      </div>
      <div className="detail-row">
        <strong>Name:</strong>
        <span>{tool.name}</span>
      </div>
      <div className="detail-row">
        <strong>MCP Server ID:</strong>
        <span>{tool.mcp_server_id}</span>
      </div>
      {tool.description && (
        <div className="detail-row">
          <strong>Description:</strong>
          <p>{tool.description}</p>
        </div>
      )}
      {tool.parameters && (
        <div className="detail-row">
          <strong>Parameters:</strong>
          <pre className="detail-json">{(() => {
            try {
              return JSON.stringify(JSON.parse(tool.parameters), null, 2)
            } catch {
              return tool.parameters
            }
          })()}</pre>
        </div>
      )}
    </div>
  )

  const renderCatalogAssetDetails = (asset: CatalogAsset) => {
    const columns = asset.columns_json ? JSON.parse(asset.columns_json) : []
    const properties = asset.properties_json ? JSON.parse(asset.properties_json) : null

    return (
      <div className="detail-content">
        <div className="detail-row">
          <strong>Full Name:</strong>
          <code className="detail-code">{asset.full_name}</code>
        </div>
        <div className="detail-row">
          <strong>Type:</strong>
          <Badge variant="primary">{asset.asset_type}</Badge>
        </div>
        {asset.owner && (
          <div className="detail-row">
            <strong>Owner:</strong>
            <span>{asset.owner}</span>
          </div>
        )}
        {asset.comment && (
          <div className="detail-row">
            <strong>Description:</strong>
            <p>{asset.comment}</p>
          </div>
        )}
        {asset.table_type && (
          <div className="detail-row">
            <strong>Table Type:</strong>
            <Badge>{asset.table_type}</Badge>
          </div>
        )}
        {asset.data_source_format && (
          <div className="detail-row">
            <strong>Format:</strong>
            <Badge>{asset.data_source_format}</Badge>
          </div>
        )}
        {asset.row_count !== null && asset.row_count !== undefined && (
          <div className="detail-row">
            <strong>Row Count:</strong>
            <span>{asset.row_count.toLocaleString()}</span>
          </div>
        )}
        {columns.length > 0 && (
          <div className="detail-row detail-row-block">
            <strong>Columns ({columns.length}):</strong>
            <table className="detail-columns-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((col: { name: string; type: string; comment?: string }, i: number) => (
                  <tr key={i}>
                    <td><code>{col.name}</code></td>
                    <td><code>{col.type}</code></td>
                    <td>{col.comment || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {properties && Object.keys(properties).length > 0 && (
          <div className="detail-row detail-row-block">
            <strong>Properties:</strong>
            <pre className="detail-json">{JSON.stringify(properties, null, 2)}</pre>
          </div>
        )}
        {asset.last_indexed_at && (
          <div className="detail-row">
            <strong>Last Indexed:</strong>
            <span>{new Date(asset.last_indexed_at).toLocaleString()}</span>
          </div>
        )}
        {onAskAI && (
          <SuggestedQuestions
            questions={getCatalogAssetQuestions(asset)}
            onAskQuestion={(q) => { onClose(); onAskAI(q) }}
          />
        )}
      </div>
    )
  }

  const renderWorkspaceAssetDetails = (asset: WorkspaceAsset) => {
    const metadata = asset.metadata_json ? JSON.parse(asset.metadata_json) : null

    return (
      <div className="detail-content">
        <div className="detail-row">
          <strong>Name:</strong>
          <span>{asset.name}</span>
        </div>
        <div className="detail-row">
          <strong>Type:</strong>
          <Badge variant="primary">{asset.asset_type}</Badge>
        </div>
        <div className="detail-row">
          <strong>Path:</strong>
          <code className="detail-code">{asset.path}</code>
        </div>
        <div className="detail-row">
          <strong>Workspace:</strong>
          <span>{asset.workspace_host}</span>
        </div>
        {asset.owner && (
          <div className="detail-row">
            <strong>Owner:</strong>
            <span>{asset.owner}</span>
          </div>
        )}
        {asset.description && (
          <div className="detail-row">
            <strong>Description:</strong>
            <p>{asset.description}</p>
          </div>
        )}
        {asset.language && (
          <div className="detail-row">
            <strong>Language:</strong>
            <Badge>{asset.language}</Badge>
          </div>
        )}
        {asset.resource_id && (
          <div className="detail-row">
            <strong>Resource ID:</strong>
            <code className="detail-code">{asset.resource_id}</code>
          </div>
        )}
        {metadata && Object.keys(metadata).length > 0 && (
          <div className="detail-row detail-row-block">
            <strong>Metadata:</strong>
            <pre className="detail-json">{JSON.stringify(metadata, null, 2)}</pre>
          </div>
        )}
        {asset.last_indexed_at && (
          <div className="detail-row">
            <strong>Last Indexed:</strong>
            <span>{new Date(asset.last_indexed_at).toLocaleString()}</span>
          </div>
        )}
        {onAskAI && (
          <SuggestedQuestions
            questions={getWorkspaceAssetQuestions(asset)}
            onAskQuestion={(q) => { onClose(); onAskAI(q) }}
          />
        )}
      </div>
    )
  }

  const getTitle = () => {
    if (CATALOG_TYPES.includes(type)) {
      const asset = item as CatalogAsset
      return `${type.charAt(0).toUpperCase() + type.slice(1)}: ${asset.name}`
    }
    if (WORKSPACE_TYPES.includes(type)) {
      const asset = item as WorkspaceAsset
      return `${type.charAt(0).toUpperCase() + type.slice(1)}: ${asset.name}`
    }
    switch (type) {
      case 'app':
        return `App: ${(item as App).name}`
      case 'server':
        return 'MCP Server Details'
      case 'tool':
        return `Tool: ${(item as Tool).name}`
      default:
        return 'Details'
    }
  }

  const renderContent = () => {
    if (CATALOG_TYPES.includes(type)) {
      return renderCatalogAssetDetails(item as CatalogAsset)
    }
    if (WORKSPACE_TYPES.includes(type)) {
      return renderWorkspaceAssetDetails(item as WorkspaceAsset)
    }
    switch (type) {
      case 'app':
        return renderAppDetails(item as App)
      case 'server':
        return renderServerDetails(item as MCPServer)
      case 'tool':
        return renderToolDetails(item as Tool)
      default:
        return <p>Unknown item type</p>
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={getTitle()}>
      {renderContent()}
    </Modal>
  )
}

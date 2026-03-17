import { MCPServer } from '../../types'
import Card from '../common/Card'
import Badge from '../common/Badge'
import Button from '../common/Button'
import './ServerCard.css'

interface ServerCardProps {
  server: MCPServer
  onAddToCollection?: (server: MCPServer) => void
  onViewDetails?: (server: MCPServer) => void
}

export default function ServerCard({ server, onAddToCollection, onViewDetails }: ServerCardProps) {
  const getKindBadgeVariant = (kind: MCPServer['kind']) => {
    switch (kind) {
      case 'managed':
        return 'success'
      case 'external':
        return 'warning'
      case 'custom':
        return 'default'
      default:
        return 'default'
    }
  }

  return (
    <Card className="server-card">
      <div className="server-card-header">
        <h4>MCP Server</h4>
        <Badge variant={getKindBadgeVariant(server.kind)}>{server.kind}</Badge>
      </div>
      <div className="server-url">{server.server_url}</div>
      {server.uc_connection && (
        <p className="server-connection">UC Connection: {server.uc_connection}</p>
      )}
      {server.scopes && (
        <p className="server-scopes">Scopes: {server.scopes}</p>
      )}
      <div className="server-card-footer">
        <Button size="small" variant="secondary" onClick={() => onViewDetails?.(server)}>
          Details
        </Button>
        <Button size="small" onClick={() => onAddToCollection?.(server)}>
          Add to Collection
        </Button>
      </div>
    </Card>
  )
}

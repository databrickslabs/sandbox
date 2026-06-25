import { WorkspaceAsset } from '../../types'
import Card from '../common/Card'
import Badge from '../common/Badge'
import Button from '../common/Button'
import './WorkspaceAssetCard.css'

interface WorkspaceAssetCardProps {
  asset: WorkspaceAsset
  onViewDetails?: (asset: WorkspaceAsset) => void
  onAskAI?: (asset: WorkspaceAsset) => void
}

const TYPE_VARIANTS: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'default'> = {
  notebook: 'primary',
  job: 'success',
  dashboard: 'warning',
  pipeline: 'danger',
  cluster: 'default',
  experiment: 'default',
}

const TYPE_LABELS: Record<string, string> = {
  notebook: 'Notebook',
  job: 'Job',
  dashboard: 'Dashboard',
  pipeline: 'Pipeline',
  cluster: 'Cluster',
  experiment: 'Experiment',
}

export default function WorkspaceAssetCard({ asset, onViewDetails, onAskAI }: WorkspaceAssetCardProps) {
  const metadata = asset.metadata_json ? JSON.parse(asset.metadata_json) : {}

  return (
    <Card className="workspace-asset-card">
      <div className="workspace-asset-header">
        <h4>{asset.name}</h4>
        <Badge variant={TYPE_VARIANTS[asset.asset_type] || 'default'}>
          {TYPE_LABELS[asset.asset_type] || asset.asset_type}
        </Badge>
      </div>
      <p className="workspace-asset-path" title={asset.path}>{asset.path}</p>
      {asset.description && (
        <p className="workspace-asset-desc">{asset.description}</p>
      )}
      <div className="workspace-asset-meta">
        {asset.owner && <span className="meta-item">Owner: {asset.owner}</span>}
        {asset.language && <Badge variant="default">{asset.language}</Badge>}
        {metadata.schedule && <span className="meta-item">Scheduled</span>}
        {metadata.task_count && <span className="meta-item">{metadata.task_count} tasks</span>}
        {metadata.state && <Badge variant="default">{metadata.state}</Badge>}
      </div>
      <div className="workspace-asset-footer">
        <Button size="small" variant="secondary" onClick={() => onViewDetails?.(asset)}>
          Details
        </Button>
        {onAskAI && (
          <Button size="small" variant="secondary" onClick={() => onAskAI(asset)}>
            Ask AI
          </Button>
        )}
      </div>
    </Card>
  )
}

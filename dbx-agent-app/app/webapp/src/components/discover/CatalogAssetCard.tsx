import { CatalogAsset } from '../../types'
import Card from '../common/Card'
import Badge from '../common/Badge'
import Button from '../common/Button'
import './CatalogAssetCard.css'

interface CatalogAssetCardProps {
  asset: CatalogAsset
  onViewDetails?: (asset: CatalogAsset) => void
  onAddToCollection?: (asset: CatalogAsset) => void
  onAskAI?: (asset: CatalogAsset) => void
}

const TYPE_VARIANTS: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'default'> = {
  table: 'primary',
  view: 'success',
  function: 'warning',
  model: 'danger',
  volume: 'default',
}

export default function CatalogAssetCard({ asset, onViewDetails, onAddToCollection, onAskAI }: CatalogAssetCardProps) {
  const columns = asset.columns_json ? JSON.parse(asset.columns_json) : []
  const columnCount = columns.length

  return (
    <Card className="catalog-asset-card">
      <div className="catalog-asset-header">
        <h4 title={asset.full_name}>{asset.name}</h4>
        <Badge variant={TYPE_VARIANTS[asset.asset_type] || 'default'}>
          {asset.asset_type}
        </Badge>
      </div>
      <p className="catalog-asset-namespace">{asset.catalog}.{asset.schema_name}</p>
      {asset.comment && (
        <p className="catalog-asset-comment">{asset.comment}</p>
      )}
      <div className="catalog-asset-meta">
        {asset.owner && <span className="meta-item">Owner: {asset.owner}</span>}
        {columnCount > 0 && <span className="meta-item">{columnCount} columns</span>}
        {asset.data_source_format && (
          <Badge variant="default">{asset.data_source_format}</Badge>
        )}
        {asset.table_type && asset.table_type !== asset.asset_type.toUpperCase() && (
          <Badge variant="default">{asset.table_type}</Badge>
        )}
      </div>
      <div className="catalog-asset-footer">
        <Button size="small" variant="secondary" onClick={() => onViewDetails?.(asset)}>
          Details
        </Button>
        {onAskAI && (
          <Button size="small" variant="secondary" onClick={() => onAskAI(asset)}>
            Ask AI
          </Button>
        )}
        <Button size="small" onClick={() => onAddToCollection?.(asset)}>
          Add to Collection
        </Button>
      </div>
    </Card>
  )
}

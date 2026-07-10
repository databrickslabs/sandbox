import Card from '../common/Card'
import Badge from '../common/Badge'
import { SearchResultItem } from '../../types'
import './SearchResultCard.css'

interface SearchResultCardProps {
  result: SearchResultItem
  onViewDetails?: (result: SearchResultItem) => void
}

const TYPE_LABELS: Record<string, string> = {
  table: 'Table',
  view: 'View',
  function: 'Function',
  model: 'Model',
  volume: 'Volume',
  notebook: 'Notebook',
  job: 'Job',
  dashboard: 'Dashboard',
  pipeline: 'Pipeline',
  cluster: 'Cluster',
  experiment: 'Experiment',
  app: 'App',
  tool: 'Tool',
  server: 'Server',
}

const TYPE_VARIANTS: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'default'> = {
  table: 'primary',
  view: 'success',
  function: 'warning',
  model: 'danger',
  volume: 'default',
  notebook: 'primary',
  job: 'success',
  dashboard: 'warning',
  pipeline: 'danger',
  cluster: 'default',
  experiment: 'success',
  app: 'primary',
  tool: 'warning',
  server: 'default',
}

export default function SearchResultCard({ result, onViewDetails }: SearchResultCardProps) {
  const scorePercent = Math.round(result.score * 100)

  return (
    <Card
      className="search-result-card"
      onClick={() => onViewDetails?.(result)}
    >
      <div className="search-result-header">
        <Badge variant={TYPE_VARIANTS[result.asset_type] || 'default'}>
          {TYPE_LABELS[result.asset_type] || result.asset_type}
        </Badge>
        <div className="search-result-score">
          <div
            className="search-result-score-bar"
            style={{ width: `${scorePercent}%` }}
          />
          <span className="search-result-score-label">{scorePercent}%</span>
        </div>
      </div>

      <h4 className="search-result-name">{result.name}</h4>

      {result.full_name && (
        <p className="search-result-namespace">{result.full_name}</p>
      )}

      {result.path && (
        <p className="search-result-path">{result.path}</p>
      )}

      {result.snippet && (
        <p className="search-result-snippet">{result.snippet}</p>
      )}

      <div className="search-result-footer">
        {result.owner && (
          <span className="search-result-owner">{result.owner}</span>
        )}
        <Badge variant="default">{result.match_type}</Badge>
      </div>
    </Card>
  )
}

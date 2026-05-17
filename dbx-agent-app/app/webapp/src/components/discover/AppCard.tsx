import { App } from '../../types'
import Card from '../common/Card'
import Badge from '../common/Badge'
import Button from '../common/Button'
import './AppCard.css'

interface AppCardProps {
  app: App
  onAddToCollection?: (app: App) => void
  onViewDetails?: (app: App) => void
}

export default function AppCard({ app, onAddToCollection, onViewDetails }: AppCardProps) {
  const tags = app.tags ? app.tags.split(',').map(t => t.trim()) : []

  return (
    <Card className="app-card">
      <div className="app-card-header">
        <h4>{app.name}</h4>
        <Badge variant="success">App</Badge>
      </div>
      {app.owner && <p className="app-owner">Owner: {app.owner}</p>}
      {tags.length > 0 && (
        <div className="app-tags">
          {tags.map((tag, index) => (
            <Badge key={index} variant="default">{tag}</Badge>
          ))}
        </div>
      )}
      {app.url && (
        <a
          href={app.url}
          target="_blank"
          rel="noopener noreferrer"
          className="app-link"
          onClick={(e) => e.stopPropagation()}
        >
          View App
        </a>
      )}
      <div className="app-card-footer">
        <Button size="small" variant="secondary" onClick={() => onViewDetails?.(app)}>
          Details
        </Button>
        <Button size="small" onClick={() => onAddToCollection?.(app)}>
          Add to Collection
        </Button>
      </div>
    </Card>
  )
}

import { Tool } from '../../types'
import Card from '../common/Card'
import Badge from '../common/Badge'
import Button from '../common/Button'
import './ToolCard.css'

interface ToolCardProps {
  tool: Tool
  onAddToCollection?: (tool: Tool) => void
  onViewDetails?: (tool: Tool) => void
}

export default function ToolCard({ tool, onAddToCollection, onViewDetails }: ToolCardProps) {
  return (
    <Card className="tool-card">
      <div className="tool-card-header">
        <h4>{tool.name}</h4>
        <Badge variant="primary">Tool</Badge>
      </div>
      <p className="tool-description">{tool.description || 'No description available'}</p>
      <div className="tool-card-footer">
        <Button size="small" variant="secondary" onClick={() => onViewDetails?.(tool)}>
          Details
        </Button>
        <Button size="small" onClick={() => onAddToCollection?.(tool)}>
          Add to Collection
        </Button>
      </div>
    </Card>
  )
}

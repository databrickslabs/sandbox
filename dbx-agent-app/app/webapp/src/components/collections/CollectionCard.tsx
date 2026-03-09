import { Collection } from '../../types'
import Card from '../common/Card'
import './CollectionCard.css'

interface CollectionCardProps {
  collection: Collection
  isActive: boolean
  onClick: () => void
}

export default function CollectionCard({ collection, isActive, onClick }: CollectionCardProps) {
  return (
    <Card className={`collection-card ${isActive ? 'active' : ''}`} onClick={onClick}>
      <h4>{collection.name}</h4>
      <p className="collection-description">{collection.description || 'No description'}</p>
    </Card>
  )
}

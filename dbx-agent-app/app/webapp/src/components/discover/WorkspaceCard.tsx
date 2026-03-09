import { WorkspaceProfile } from '../../types'
import Card from '../common/Card'
import Badge from '../common/Badge'
import Button from '../common/Button'
import './WorkspaceCard.css'

interface WorkspaceCardProps {
  profile: WorkspaceProfile
  onDiscover?: (profile: WorkspaceProfile) => void
}

export default function WorkspaceCard({ profile, onDiscover }: WorkspaceCardProps) {
  const getBadgeVariant = (): 'success' | 'danger' | 'warning' => {
    if (profile.is_account_profile) return 'warning'
    return profile.auth_valid ? 'success' : 'danger'
  }

  const getBadgeLabel = (): string => {
    if (profile.is_account_profile) return 'account'
    return profile.auth_valid ? 'authenticated' : 'auth failed'
  }

  return (
    <Card className="workspace-card">
      <div className="workspace-card-header">
        <h4>{profile.name}</h4>
        <Badge variant={getBadgeVariant()}>{getBadgeLabel()}</Badge>
      </div>
      {profile.host && (
        <div className="workspace-host">{profile.host}</div>
      )}
      <div className="workspace-meta">
        {profile.auth_type && (
          <span className="workspace-auth-type">Auth: {profile.auth_type}</span>
        )}
        {profile.username && (
          <span className="workspace-username">User: {profile.username}</span>
        )}
      </div>
      {profile.auth_error && !profile.is_account_profile && (
        <p className="workspace-error">{profile.auth_error}</p>
      )}
      <div className="workspace-card-footer">
        <Button
          size="small"
          onClick={() => onDiscover?.(profile)}
          disabled={!profile.auth_valid}
        >
          Discover
        </Button>
      </div>
    </Card>
  )
}

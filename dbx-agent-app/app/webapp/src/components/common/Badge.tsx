import './Badge.css'

interface BadgeProps {
  children: string
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger'
}

export default function Badge({ children, variant = 'default' }: BadgeProps) {
  return <span className={`badge badge-${variant}`}>{children}</span>
}

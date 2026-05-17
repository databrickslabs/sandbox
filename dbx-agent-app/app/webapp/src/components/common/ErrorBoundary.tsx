import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div style={{
          padding: '2rem',
          margin: '1rem',
          borderRadius: '8px',
          backgroundColor: 'var(--color-error-bg, #fef2f2)',
          border: '1px solid var(--color-error-border, #fecaca)',
          color: 'var(--color-error-text, #991b1b)',
        }}>
          <h3 style={{ margin: '0 0 0.5rem 0' }}>Something went wrong</h3>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem' }}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              border: '1px solid currentColor',
              backgroundColor: 'transparent',
              color: 'inherit',
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

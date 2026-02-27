import { Outlet, Link, useLocation } from 'react-router-dom'
import './Layout.css'

export default function Layout() {
  const location = useLocation()

  const isActive = (path: string) => {
    return location.pathname === path ? 'active' : ''
  }

  return (
    <div className="layout">
      <header className="layout-header">
        <div className="header-content">
          <h1 className="header-title">Multi-Agent Registry</h1>
          <nav className="header-nav">
            <Link to="/discover" className={`nav-link ${isActive('/discover')}`}>
              Discover
            </Link>
            <Link to="/collections" className={`nav-link ${isActive('/collections')}`}>
              Collections
            </Link>
            <Link to="/agents" className={`nav-link ${isActive('/agents')}`}>
              Agents
            </Link>
            <Link to="/chat" className={`nav-link ${isActive('/chat')}`}>
              Chat
            </Link>
            <Link to="/agent-chat" className={`nav-link ${isActive('/agent-chat')}`}>
              Agent Chat
            </Link>
            <Link to="/lineage" className={`nav-link ${isActive('/lineage')}`}>
              Lineage
            </Link>
            <Link to="/audit-log" className={`nav-link ${isActive('/audit-log')}`}>
              Audit Log
            </Link>
          </nav>
        </div>
      </header>
      <main className="layout-main">
        <Outlet />
      </main>
    </div>
  )
}

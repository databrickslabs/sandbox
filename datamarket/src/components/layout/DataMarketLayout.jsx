import React, { useState } from 'react'
import { Search, Menu, X, ChevronDown, ShieldCheck, Bell, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { usePersona, personas } from '../../context/PersonaContext'
import { useAppConfig } from '../../context/AppConfigContext'
import { DataMarketAssistant } from '../DataMarketAssistant'

const DataMarket_BLUE = '#003865'

const personaBadgeColors = {
  richard: 'bg-blue-500',
  james: 'bg-emerald-500',
  admin: 'bg-purple-600'
}

const notifIcon = (status) => {
  if (status === 'Approved') return <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0" />
  if (status === 'Denied' || status === 'Revoked') return <XCircle className="h-4 w-4 text-red-500 shrink-0" />
  if (status === 'Expiring') return <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
  return <Clock className="h-4 w-4 text-gray-400 shrink-0" />
}

const notifText = (n) => {
  if (n.status === 'Approved') return `Access to ${n.product_name} approved`
  if (n.status === 'Denied') return `Access to ${n.product_name} denied`
  if (n.status === 'Revoked') return `Access to ${n.product_name} revoked`
  if (n.status === 'Expiring') return `${n.product_name} access expires soon`
  return n.product_name
}

export function DataMarketLayout({ currentPage, onNavigate, children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [personaMenuOpen, setPersonaMenuOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const { persona, currentPersona, setCurrentPersona, pendingRequests, notifications, unreadNotificationCount, isAdmin, demoMode, identityLoading } = usePersona()
  const { appName, appSubtitle, appLogoUrl, navLinks, askAiEnabled, insightsEnabled, featureRequestsEnabled } = useAppConfig()

  const personaColor = isAdmin ? '#7C3AED' : currentPersona === 'james' ? '#059669' : '#3B82F6'
  const avatarBadgeClass = isAdmin ? 'bg-purple-600' : currentPersona === 'james' ? 'bg-emerald-500' : 'bg-blue-500'

  const navItems = [
    { id: 'home',      label: 'Home' },
    { id: 'discover',  label: 'Discover' },
    ...(askAiEnabled  ? [{ id: 'ask-ai',   label: 'Ask AI' }]   : []),
    ...(insightsEnabled ? [{ id: 'insights', label: 'Insights' }] : []),
    ...(featureRequestsEnabled ? [{ id: 'feature-requests', label: 'Requests' }] : []),
    { id: 'my-access', label: isAdmin ? 'Manage' : 'My Data' },
  ]

  const isActive = (id) => {
    if (id === 'home')             return currentPage === 'home'
    if (id === 'discover')         return ['discover', 'data', 'catalog', 'detail'].includes(currentPage)
    if (id === 'ask-ai')           return ['ask-ai', 'ai-explorer'].includes(currentPage)
    if (id === 'insights')         return currentPage === 'insights'
    if (id === 'feature-requests') return currentPage === 'feature-requests'
    if (id === 'my-access')        return ['my-access', 'library', 'my-library', 'register', 'admin'].includes(currentPage)
    return false
  }

  const switchPersona = (id) => {
    setCurrentPersona(id)
    setPersonaMenuOpen(false)
    setUserMenuOpen(false)
    onNavigate('home')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Demo Banner — only shown in demo mode */}
      {demoMode && (
        <div className="text-center py-1.5 text-xs text-white font-medium"
          style={{ backgroundColor: personaColor }}>
          <ShieldCheck className="inline h-3 w-3 mr-1.5 mb-0.5" />
          Demo mode — viewing as <strong>{persona.name}</strong> ({persona.role}, {persona.department})
          {!isAdmin && ' · '}
          {isAdmin && pendingRequests.length > 0 && (
            <button onClick={() => onNavigate('my-access')} className="underline ml-1">
              {pendingRequests.length} pending approval{pendingRequests.length !== 1 ? 's' : ''} →
            </button>
          )}
        </div>
      )}

      {/* Top Nav */}
      <header style={{ backgroundColor: DataMarket_BLUE }} className="sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <button onClick={() => onNavigate('home')} className="flex items-center gap-3 hover:opacity-90 transition-opacity">
              {appLogoUrl && <img src={appLogoUrl} alt={appName} className="w-9 h-9 rounded-full shrink-0 ring-2 ring-white/30" />}
              <div className="hidden sm:flex flex-col gap-0 self-center">
                <span className="text-white font-semibold text-base tracking-wide leading-[1.1]">{appName}</span>
                <span className="text-white/60 text-[10px] tracking-wide leading-[1.1]">{appSubtitle}</span>
              </div>
              <span className="text-white font-semibold text-sm sm:hidden">{appName}</span>
            </button>

            {/* Desktop Nav */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map(item => (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-1.5 ${
                    isActive(item.id) ? 'bg-white/20 text-white' : 'text-white/80 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {item.label}
                  {item.id === 'my-access' && isAdmin && pendingRequests.length > 0 && (
                    <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                      {pendingRequests.length}
                    </span>
                  )}
                </button>
              ))}
            </nav>

            {/* Right side */}
            <div className="flex items-center gap-2">
              {/* Notifications bell */}
              <div className="relative">
                <button
                  onClick={() => { setNotifOpen(v => !v); setUserMenuOpen(false) }}
                  className="relative p-2 text-white/80 hover:text-white transition-colors"
                >
                  <Bell className="h-5 w-5" />
                  {(isAdmin ? pendingRequests.length : unreadNotificationCount) > 0 && (
                    <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border border-[#003865]" />
                  )}
                </button>

                {notifOpen && (
                  <div className="absolute right-0 mt-1 w-80 bg-white rounded-xl shadow-xl border border-gray-200 py-2 z-50">
                    <p className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-100">
                      {isAdmin ? 'Pending Approvals' : 'Notifications'}
                    </p>
                    {isAdmin ? (
                      pendingRequests.length === 0 ? (
                        <p className="px-4 py-6 text-sm text-gray-400 text-center">No pending approvals</p>
                      ) : (
                        <>
                          {pendingRequests.slice(0, 5).map(r => (
                            <button key={r.request_ref || r.id}
                              onClick={() => { onNavigate('admin'); setNotifOpen(false) }}
                              className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 text-left">
                              <Clock className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                              <div className="min-w-0">
                                <p className="text-sm text-gray-800 truncate">{r.product_name} — {r.requester_name || r.requester_email}</p>
                                <p className="text-xs text-gray-400">Awaiting approval</p>
                              </div>
                            </button>
                          ))}
                          <div className="border-t border-gray-100 pt-1">
                            <button onClick={() => { onNavigate('my-access'); setNotifOpen(false) }}
                              className="w-full text-center text-xs text-blue-600 hover:text-blue-800 py-2">
                              View all in Manage →
                            </button>
                          </div>
                        </>
                      )
                    ) : (
                      notifications.length === 0 ? (
                        <p className="px-4 py-6 text-sm text-gray-400 text-center">No recent notifications</p>
                      ) : (
                        notifications.slice(0, 6).map((n, i) => (
                          <div key={i} className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50">
                            {notifIcon(n.status)}
                            <div className="min-w-0">
                              <p className="text-sm text-gray-800">{notifText(n)}</p>
                              {n.status === 'Approved' && n.expires_at && (
                                <p className="text-xs text-gray-400">
                                  Expires {new Date(n.expires_at).toLocaleDateString()}
                                </p>
                              )}
                              {(n.status === 'Denied' || n.status === 'Revoked') && n.denial_reason && (
                                <p className="text-xs text-gray-400 truncate">{n.denial_reason}</p>
                              )}
                            </div>
                          </div>
                        ))
                      )
                    )}
                  </div>
                )}
              </div>

              {/* Search */}
              <div className="relative hidden sm:block">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/60" />
                <input
                  type="text"
                  placeholder="Search..."
                  className="pl-9 pr-4 py-1.5 rounded text-sm bg-white/15 text-white placeholder-white/60 border border-white/20 focus:outline-none focus:bg-white/25 w-40"
                  onKeyDown={e => { if (e.key === 'Enter' && e.target.value) onNavigate('discover') }}
                />
              </div>

              {/* Persona / User menu */}
              <div className="relative">
                <button
                  onClick={() => { setUserMenuOpen(!userMenuOpen); setPersonaMenuOpen(false) }}
                  className="flex items-center gap-2 text-white/90 hover:text-white px-2 py-1 rounded hover:bg-white/10 transition-colors"
                >
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold ${identityLoading ? 'bg-white/20' : avatarBadgeClass}`}>
                    {identityLoading ? '…' : persona.avatar}
                  </div>
                  <span className="text-sm hidden sm:block">{identityLoading ? '' :
                    (() => { const n = persona.name || ''; return n.includes('@') ? n.split('@')[0] : (n.split(' ')[0] || n); })()
                  }</span>
                  <ChevronDown className="h-3 w-3 hidden sm:block" />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-1 w-64 bg-white rounded-xl shadow-xl border border-gray-200 py-2 z-50">
                    {/* Current user info */}
                    <div className="px-4 py-3 border-b border-gray-100">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold ${avatarBadgeClass}`}>
                          {persona.avatar}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{persona.name}</p>
                          <p className="text-xs text-gray-500">{persona.email}</p>
                          <p className="text-xs text-gray-400">{persona.role}</p>
                        </div>
                      </div>
                    </div>

                    {/* Quick links */}
                    <div className="py-1 border-b border-gray-100">
                      <button onClick={() => { onNavigate('my-access'); setUserMenuOpen(false) }} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">{isAdmin ? 'Manage' : 'My Data'}</button>
                      {isAdmin && (
                        <button onClick={() => { onNavigate('my-access'); setUserMenuOpen(false) }} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center justify-between">
                          Approvals
                          {pendingRequests.length > 0 && <span className="bg-red-100 text-red-700 text-xs font-medium px-2 py-0.5 rounded-full">{pendingRequests.length}</span>}
                        </button>
                      )}
                    </div>

                    {/* Persona switcher — demo mode only */}
                    {demoMode && (
                      <div className="py-2">
                        <p className="px-4 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                          <ShieldCheck className="h-3 w-3" /> Switch Demo Persona
                        </p>
                        {Object.values(personas).map(p => (
                          <button
                            key={p.id}
                            onClick={() => switchPersona(p.id)}
                            className={`w-full text-left px-4 py-2.5 hover:bg-gray-50 flex items-center gap-3 ${currentPersona === p.id ? 'bg-blue-50' : ''}`}
                          >
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${personaBadgeColors[p.id]}`}>
                              {p.avatar}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900">{p.name} — {p.role}</p>
                              <p className="text-xs text-gray-400 truncate">{p.description}</p>
                            </div>
                            {currentPersona === p.id && <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Mobile menu */}
              <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden text-white p-1">
                {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Nav */}
        {mobileOpen && (
          <div className="md:hidden border-t border-white/20 px-4 pb-3">
            {navItems.map(item => (
              <button key={item.id} onClick={() => { onNavigate(item.id); setMobileOpen(false) }}
                className="flex items-center justify-between w-full px-3 py-2 text-sm text-white/90 hover:text-white hover:bg-white/10 rounded mt-1">
                <span>{item.label}</span>
                {item.id === 'my-access' && isAdmin && pendingRequests.length > 0 && (
                  <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                    {pendingRequests.length}
                  </span>
                )}
              </button>
            ))}
            {/* Mobile: pending badge shown inline on "Manage" item via navItems loop above */}
          </div>
        )}
      </header>

      <main className="flex-1">
        {children}
      </main>

      <footer className="border-t border-gray-200 bg-white mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {appLogoUrl && <img src={appLogoUrl} alt={appName} className="w-6 h-6 rounded-full" />}
            <span className="text-sm text-gray-500">{appName} · {appSubtitle}</span>
          </div>
          {navLinks?.some(l => l.visible) && (
            <nav className="flex items-center gap-6">
              {(navLinks || []).filter(l => l.visible).map(link => (
                <button key={link.label}
                  onClick={() => onNavigate?.(link.label.toLowerCase())}
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
                  {link.label}
                </button>
              ))}
            </nav>
          )}
        </div>
      </footer>

      {(userMenuOpen || personaMenuOpen || mobileOpen || notifOpen) && (
        <div className="fixed inset-0 z-40" onClick={() => { setUserMenuOpen(false); setPersonaMenuOpen(false); setMobileOpen(false); setNotifOpen(false) }} />
      )}

      <DataMarketAssistant onNavigate={onNavigate} />
    </div>
  )
}

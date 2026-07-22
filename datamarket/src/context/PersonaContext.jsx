import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { isAdminRole, normalizeRole, roleDisplayName } from '../lib/roles'

export const personas = {
  richard: {
    id: 'richard',
    name: 'Richard',
    fullName: 'Richard Chen',
    email: 'richard.chen@example.org',
    role: 'Data Analyst',
    department: 'Finance & Accounting',
    avatar: 'RC',
    color: '#3B82F6',
    approvedProductRefs: ['DP-001', 'DP-007'],
    description: 'Analyst — limited access, can browse and request'
  },
  james: {
    id: 'james',
    name: 'James',
    fullName: 'James Park',
    email: 'james.park@example.org',
    role: 'Finance Manager',
    department: 'Budget & Finance',
    avatar: 'JP',
    color: '#10B981',
    approvedProductRefs: ['DP-001', 'DP-002', 'DP-003', 'DP-007', 'DP-010'],
    description: 'Finance Manager — pre-approved for financial data (demo only)'
  },
  admin: {
    id: 'admin',
    name: 'Admin',
    fullName: 'Data Steward',
    email: 'datasteward@example.org',
    role: 'Data Steward',
    department: 'Data Platform Team',
    avatar: 'DS',
    color: '#8B5CF6',
    approvedProductRefs: 'all',
    description: 'Data Steward — full access + approval authority'
  }
}

const PersonaContext = createContext(null)

function toProductRef(productRef) {
  return typeof productRef === 'number'
    ? `DP-${String(productRef).padStart(3, '0')}`
    : productRef
}

export function PersonaProvider({ children }) {
  const [currentPersona, setCurrentPersona] = useState('richard')
  const [requests, setRequests] = useState([])
  const [products, setProducts] = useState([])
  const [library, setLibrary] = useState([])
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(false)
  const [apiAvailable, setApiAvailable] = useState(false)
  const [demoMode, setDemoMode] = useState(null) // null = identity not yet resolved
  const [ssoUser, setSsoUser] = useState(null)
  const [rfaEnabled, setRfaEnabled] = useState(false)
  const [ucGrantsEnabled, setUcGrantsEnabled] = useState(false)

  const identityLoading = demoMode === null

  const ssoIsAdmin = ssoUser && !demoMode && isAdminRole(ssoUser.role)

  const persona = ssoUser && !demoMode ? {
    id: ssoIsAdmin ? 'admin' : 'sso',
    name: ssoUser.display_name?.split(' ')[0] || 'User',
    fullName: ssoUser.display_name || ssoUser.email,
    email: ssoUser.email,
    role: roleDisplayName(ssoUser.role),
    department: ssoUser.department || 'General',
    avatar: (ssoUser.display_name || ssoUser.email).split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase(),
    color: ssoIsAdmin ? '#8B5CF6' : '#3B82F6',
    approvedProductRefs: ssoIsAdmin ? 'all' : [],
    description: ssoIsAdmin ? 'Data Steward — authenticated via SSO' : 'Data Analyst — authenticated via SSO'
  } : personas[currentPersona]

  const isAdmin = persona.id === 'admin' || ssoIsAdmin

  // ── Check API availability and identity mode ───────────────────────────────
  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        const lakebaseOk = data.lakebase === 'connected'
        setApiAvailable(lakebaseOk)
        setDemoMode(data.demo_mode !== false)
        setRfaEnabled(!!data.rfa_enabled)
        setUcGrantsEnabled(!!data.uc_grants_enabled)
        if (!lakebaseOk) console.info('[PersonaContext] Lakebase not connected, using demo data')

        if (data.demo_mode === false) {
          fetch('/api/portal/identity')
            .then(r => r.json())
            .then(id => {
              if (id.mode === 'sso' && id.user) {
                setSsoUser({ ...id.user, role: normalizeRole(id.user.role) })
              }
            })
            .catch(() => {})
        }
      })
      .catch(() => setApiAvailable(false))
  }, [])

  // ── Load from API or fall back to local seed ──────────────────────────────
  const loadProducts = useCallback(async () => {
    if (!apiAvailable) return
    try {
      const r = await fetch('/api/portal/products')
      if (r.ok) setProducts(await r.json())
    } catch (e) { console.warn('products load failed', e) }
  }, [apiAvailable])

  const loadRequests = useCallback(async () => {
    if (!apiAvailable) return
    try {
      const r = await fetch('/api/portal/requests')
      if (r.ok) setRequests(await r.json())
    } catch (e) { console.warn('requests load failed', e) }
  }, [apiAvailable])

  const loadLibrary = useCallback(async () => {
    if (!apiAvailable) return
    try {
      const r = await fetch(`/api/portal/library?email=${encodeURIComponent(persona.email)}`)
      if (r.ok) setLibrary(await r.json())
    } catch (e) { console.warn('library load failed', e) }
  }, [apiAvailable, persona.email])

  const loadNotifications = useCallback(async () => {
    if (!apiAvailable || isAdmin) return
    try {
      const r = await fetch(`/api/portal/notifications?email=${encodeURIComponent(persona.email)}`)
      if (r.ok) setNotifications(await r.json())
    } catch (e) { console.warn('notifications load failed', e) }
  }, [apiAvailable, persona.email, isAdmin])

  useEffect(() => {
    if (apiAvailable) {
      loadProducts()
      loadRequests()
      loadLibrary()
      loadNotifications()
    }
  }, [apiAvailable, loadProducts, loadRequests, loadLibrary, loadNotifications])

  useEffect(() => {
    if (apiAvailable) {
      loadLibrary()
      loadNotifications()
    }
  }, [currentPersona, apiAvailable, loadLibrary, loadNotifications])

  // ── Mutations ─────────────────────────────────────────────────────────────
  const submitRequest = async (product, form) => {
    const productRef = product.product_ref || `DP-${String(product.id).padStart(3, '0')}`
    if (apiAvailable) {
      try {
        const r = await fetch('/api/portal/requests', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            productRef,
            requesterEmail: persona.email,
            team: form.team || persona.department,
            reason: form.reason,
            accessLevel: 'Read Only'
          })
        })
        if (r.ok) {
          await loadRequests()
          return await r.json()
        }
      } catch (e) { console.warn('submitRequest API failed, falling back', e) }
    }
    const newReq = {
      request_ref: `REQ-${String(requests.length + 1).padStart(3, '0')}`,
      product_ref: productRef,
      product_name: product.display_name || product.name,
      requester_email: persona.email,
      requester_name: persona.fullName,
      requester_team: form.team || persona.department,
      business_reason: form.reason,
      status: 'Pending',
      requested_at: new Date().toISOString(),
      access_level: 'Read Only',
      _local: true
    }
    setRequests(prev => [newReq, ...prev])
    return newReq
  }

  const approveRequest = async (reqRef) => {
    if (apiAvailable) {
      try {
        await fetch(`/api/portal/requests/${reqRef}/approve`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ adminEmail: persona.email })
        })
        await loadRequests()
        return
      } catch (e) { console.warn('approveRequest API failed', e) }
    }
    setRequests(prev => prev.map(r =>
      (r.request_ref === reqRef || r.id === reqRef)
        ? { ...r, status: 'Approved', resolved_at: new Date().toISOString() }
        : r
    ))
  }

  const denyRequest = async (reqRef, reason = '') => {
    if (apiAvailable) {
      try {
        await fetch(`/api/portal/requests/${reqRef}/deny`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ adminEmail: persona.email, reason })
        })
        await loadRequests()
        return
      } catch (e) { console.warn('denyRequest API failed', e) }
    }
    setRequests(prev => prev.map(r =>
      (r.request_ref === reqRef || r.id === reqRef)
        ? { ...r, status: 'Denied', resolved_at: new Date().toISOString(), denial_reason: reason }
        : r
    ))
  }

  const revokeRequest = async (reqRef, reason = '') => {
    if (apiAvailable) {
      try {
        await fetch(`/api/portal/requests/${reqRef}/revoke`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ adminEmail: persona.email, reason })
        })
        await loadRequests()
        await loadLibrary()
        await loadNotifications()
        return
      } catch (e) { console.warn('revokeRequest API failed', e) }
    }
    setRequests(prev => prev.map(r =>
      (r.request_ref === reqRef || r.id === reqRef)
        ? { ...r, status: 'Revoked', resolved_at: new Date().toISOString(), denial_reason: reason }
        : r
    ))
  }

  const myProductRequests = useCallback((productRef) => {
    const refStr = toProductRef(productRef)
    return requests.filter(r => {
      const matchesProduct = r.product_ref === refStr || r.productRef === refStr
      const matchesUser = r.requester_email === persona.email || r.requestedBy === currentPersona
      return matchesProduct && matchesUser
    }).sort((a, b) => new Date(b.resolved_at || b.requested_at) - new Date(a.resolved_at || a.requested_at))
  }, [requests, persona.email, currentPersona])

  const hasApprovedAccess = useCallback((productRef) => {
    const refStr = toProductRef(productRef)
    if (persona.approvedProductRefs === 'all') return false
    if (persona.approvedProductRefs.includes(refStr)) return true
    return myProductRequests(productRef).some(r => {
      if (r.status !== 'Approved') return false
      if (r.expires_at && new Date(r.expires_at) < new Date()) return false
      return true
    })
  }, [persona, myProductRequests])

  const getProductAccessState = useCallback((productRef) => {
    const refStr = toProductRef(productRef)
    const mine = myProductRequests(productRef)
    const approved = mine.find(r => {
      if (r.status !== 'Approved') return false
      if (r.expires_at && new Date(r.expires_at) < new Date()) return false
      return true
    })
    if (approved) {
      return { state: 'granted', requestRef: approved.request_ref || approved.id, canQuery: true }
    }
    const revoked = mine.find(r => r.status === 'Revoked')
    if (revoked) {
      return {
        state: 'revoked',
        requestRef: revoked.request_ref || revoked.id,
        reason: revoked.denial_reason || revoked.denyReason,
        canQuery: false,
      }
    }
    const pending = mine.find(r => r.status === 'Pending')
    if (pending) {
      return { state: 'pending', requestRef: pending.request_ref || pending.id, canQuery: false }
    }
    if (isAdmin) {
      return { state: 'admin', canQuery: true }
    }
    return { state: 'none', canQuery: false }
  }, [myProductRequests, isAdmin])

  const hasAccess = useCallback((productRef) => {
    const access = getProductAccessState(productRef)
    return access.canQuery
  }, [getProductAccessState])

  const unreadNotificationCount = useMemo(() => notifications.length, [notifications])

  const myRequests = requests.filter(r =>
    r.requester_email === persona.email || r.requestedBy === currentPersona)
  const pendingRequests = requests.filter(r => r.status === 'Pending')

  return (
    <PersonaContext.Provider value={{
      currentPersona,
      setCurrentPersona: demoMode ? setCurrentPersona : () => {},
      persona,
      isAdmin,
      requests,
      myRequests,
      pendingRequests,
      products,
      library,
      notifications,
      unreadNotificationCount,
      loading,
      identityLoading,
      apiAvailable,
      demoMode,
      rfaEnabled,
      ucGrantsEnabled,
      ssoUser,
      submitRequest,
      approveRequest,
      denyRequest,
      revokeRequest,
      hasAccess,
      hasApprovedAccess,
      getProductAccessState,
      refreshRequests: loadRequests,
      refreshLibrary: loadLibrary,
      refreshNotifications: loadNotifications
    }}>
      {children}
    </PersonaContext.Provider>
  )
}

export function usePersona() {
  const ctx = useContext(PersonaContext)
  if (!ctx) throw new Error('usePersona must be used within PersonaProvider')
  return ctx
}

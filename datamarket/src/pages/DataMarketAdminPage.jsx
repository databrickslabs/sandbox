import React, { useState, useEffect } from 'react'
import { ShieldCheck, CheckCircle2, XCircle, Clock, Terminal, ChevronDown, ChevronUp, User, Calendar, Database, Package, Eye, RotateCcw, AlertTriangle } from 'lucide-react'
import { usePersona } from '../context/PersonaContext'
import { useAppConfig } from '../context/AppConfigContext'

const DataMarket_BLUE = '#003865'

function UCGrantPanel({ request, action }) {
  const [open, setOpen] = useState(false)

  const grantSQL = request.ucGrantSql || `-- Unity Catalog RBAC — executed automatically on approval
GRANT SELECT ON TABLE <your_catalog>.<your_schema>.<your_table>
  TO \`${request.requesterEmail}\`;

-- Verify the grant was applied
SHOW GRANTS ON TABLE <your_catalog>.<your_schema>.<your_table>;`

  const revokeSQL = `-- Unity Catalog RBAC — executed automatically on denial
REVOKE SELECT ON TABLE <your_catalog>.<your_schema>.<your_table>
  FROM \`${request.requesterEmail}\`;`

  // Pending requests always preview the GRANT that will be executed on approval
  const sql = action === 'Denied' || action === 'Revoked' ? revokeSQL : grantSQL

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-xs font-medium text-gray-500 hover:text-gray-800 transition-colors"
      >
        <Terminal className="h-3.5 w-3.5" />
        {open ? 'Hide' : 'Show'} UC GRANT statement
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>
      {open && (
        <div className="mt-2 bg-gray-900 rounded-lg p-4 overflow-x-auto">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <div className="w-2 h-2 rounded-full bg-yellow-400" />
            <div className="w-2 h-2 rounded-full bg-green-400" />
            <span className="text-gray-400 text-[10px] ml-2">Unity Catalog — your_catalog</span>
          </div>
          <pre className="text-xs font-mono whitespace-pre text-green-400 leading-relaxed">{sql}</pre>
        </div>
      )}
    </div>
  )
}

// Normalize API (snake_case) and local (camelCase) request shapes
function norm(r) {
  return {
    id:            r.request_ref  || r.id,
    productName:   r.product_name || r.productName,
    requesterEmail:r.requester_email || r.requesterEmail,
    requesterName: r.requester_name  || r.requesterName,
    requesterTeam: r.requester_team  || r.requesterTeam,
    reason:        r.business_reason || r.reason,
    requestedAt:   r.requested_at   || r.requestedAt,
    status:        r.status,
    accessLevel:   r.access_level   || r.accessLevel || 'Read Only',
    denyReason:    r.denial_reason  || r.denyReason,
    ucGrantSql:    r.uc_grant_sql   || r.ucGrantSql,
    ucFullName:    r.uc_full_name,
    expiresAt:     r.expires_at     || r.expiresAt,
  }
}

export function DataMarketAdminPage({ embedded = false }) {
  const { requests, approveRequest, denyRequest, revokeRequest, currentPersona, isAdmin } = usePersona()
  const { demoMode } = useAppConfig()
  const [filter, setFilter] = useState(embedded ? 'Approved' : 'Pending')
  const [activeView, setActiveView] = useState('access') // 'access' | 'products'
  const [denyModal, setDenyModal] = useState(null)
  const [denyReason, setDenyReason] = useState('')
  const [revokeModal, setRevokeModal] = useState(null)
  const [revokeReason, setRevokeReason] = useState('')
  const [justActed, setJustActed] = useState({})
  const [pendingProducts, setPendingProducts] = useState([])
  const [resetState, setResetState] = useState('idle') // 'idle' | 'confirm' | 'loading' | 'done'
  const [productActed, setProductActed] = useState({})
  const normalizedReqs = requests.map(norm)

  useEffect(() => {
    fetch('/api/portal/products?includeAll=true')
      .then(r => r.json())
      .then(rows => {
        if (Array.isArray(rows)) {
          setPendingProducts(rows.filter(p => p.status === 'Pending' || p.is_active === false))
        }
      })
      .catch(() => {})
  }, [])

  const handlePublish = async (productRef, productName) => {
    try {
      await fetch(`/api/portal/products/${productRef}/publish`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewerEmail: 'datasteward@example.org' })
      })
      setProductActed(prev => ({ ...prev, [productRef]: 'published' }))
      setPendingProducts(prev => prev.filter(p => p.product_ref !== productRef))
    } catch (e) { console.error(e) }
  }

  const handleRejectProduct = async (productRef) => {
    try {
      await fetch(`/api/portal/products/${productRef}/reject`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewerEmail: 'datasteward@example.org', reason: 'Does not meet governance standards' })
      })
      setProductActed(prev => ({ ...prev, [productRef]: 'rejected' }))
      setPendingProducts(prev => prev.filter(p => p.product_ref !== productRef))
    } catch (e) { console.error(e) }
  }

  if (!isAdmin) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 text-center">
        <ShieldCheck className="h-16 w-16 text-gray-200 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Access Restricted</h2>
        <p className="text-gray-500">This page is only accessible to Data Stewards and Admins.</p>
      </div>
    )
  }

  const filtered = normalizedReqs.filter(r => filter === 'All' || r.status === filter)
  const counts = {
    Pending:  normalizedReqs.filter(r => r.status === 'Pending').length,
    Approved: normalizedReqs.filter(r => r.status === 'Approved').length,
    Denied:   normalizedReqs.filter(r => r.status === 'Denied').length,
  }

  const handleApprove = (reqId) => {
    approveRequest(reqId)
    setJustActed(prev => ({ ...prev, [reqId]: 'approved' }))
  }

  const handleDeny = () => {
    denyRequest(denyModal, denyReason)
    setJustActed(prev => ({ ...prev, [denyModal]: 'denied' }))
    setDenyModal(null)
    setDenyReason('')
  }

  const handleRevoke = () => {
    revokeRequest(revokeModal, revokeReason)
    setJustActed(prev => ({ ...prev, [revokeModal]: 'revoked' }))
    setRevokeModal(null)
    setRevokeReason('')
  }

  const timeAgo = (iso) => {
    const diff = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  }

  const wrapperClass = embedded
    ? 'w-full'
    : 'max-w-7xl mx-auto px-4 sm:px-6 py-8'

  return (
    <div className={wrapperClass}>
      {!embedded && <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldCheck className="h-6 w-6" style={{ color: DataMarket_BLUE }} />
            {activeView === 'access' ? 'Approval Queue' : 'Product Registration Queue'}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {activeView === 'access'
              ? 'Review and action data access requests — approvals automatically issue Unity Catalog grants'
              : 'Review and publish new data products submitted by producers'}
          </p>
        </div>
        {/* View toggle + Demo Reset */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setActiveView('access')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${activeView === 'access' ? 'text-white border-transparent' : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'}`}
            style={activeView === 'access' ? { backgroundColor: DataMarket_BLUE } : {}}
          >
            <ShieldCheck className="h-4 w-4" /> Access Requests
            {requests.filter(r => r.status === 'Pending').length > 0 && (
              <span className="bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {requests.filter(r => r.status === 'Pending').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveView('products')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${activeView === 'products' ? 'text-white border-transparent' : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'}`}
            style={activeView === 'products' ? { backgroundColor: DataMarket_BLUE } : {}}
          >
            <Package className="h-4 w-4" /> New Products
            {pendingProducts.length > 0 && (
              <span className="bg-blue-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {pendingProducts.length}
              </span>
            )}
          </button>

          {/* Demo Reset — only shown when DEMO_MODE=true */}
          {demoMode && <div className="relative ml-1">
            {resetState === 'idle' && (
              <button
                onClick={() => setResetState('confirm')}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border border-dashed border-gray-300 text-gray-400 hover:border-red-300 hover:text-red-500 transition-colors"
                title="Reset demo data"
              >
                <RotateCcw className="h-3.5 w-3.5" /> Reset Demo
              </button>
            )}
            {resetState === 'confirm' && (
              <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <AlertTriangle className="h-3.5 w-3.5 text-red-500 shrink-0" />
                <span className="text-xs text-red-700 font-medium">Clear all demo data?</span>
                <button
                  onClick={async () => {
                    setResetState('loading')
                    try {
                      await fetch('/api/portal/demo-reset', { method: 'POST' })
                      setResetState('done')
                      setTimeout(() => setResetState('idle'), 2500)
                      window.location.reload()
                    } catch { setResetState('idle') }
                  }}
                  className="px-2 py-0.5 bg-red-500 text-white rounded text-xs font-medium hover:bg-red-600"
                >Yes</button>
                <button
                  onClick={() => setResetState('idle')}
                  className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs text-gray-600 hover:bg-gray-50"
                >Cancel</button>
              </div>
            )}
            {resetState === 'loading' && (
              <span className="flex items-center gap-1.5 px-3 py-2 text-xs text-gray-400">
                <RotateCcw className="h-3.5 w-3.5 animate-spin" /> Clearing...
              </span>
            )}
            {resetState === 'done' && (
              <span className="flex items-center gap-1.5 px-3 py-2 text-xs text-emerald-600 font-medium">
                <CheckCircle2 className="h-3.5 w-3.5" /> Reset done
              </span>
            )}
          </div>}
        </div>
      </div>}

      {/* View toggle shown in embedded mode as compact pills */}
      {embedded && (
        <div className="flex items-center gap-2 mb-5">
          <button
            onClick={() => setActiveView('access')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${activeView === 'access' ? 'text-white border-transparent' : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'}`}
            style={activeView === 'access' ? { backgroundColor: DataMarket_BLUE } : {}}
          >
            <ShieldCheck className="h-4 w-4" /> Access Requests
            {requests.filter(r => r.status === 'Pending').length > 0 && (
              <span className="bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {requests.filter(r => r.status === 'Pending').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveView('products')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${activeView === 'products' ? 'text-white border-transparent' : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'}`}
            style={activeView === 'products' ? { backgroundColor: DataMarket_BLUE } : {}}
          >
            <Package className="h-4 w-4" /> New Products
            {pendingProducts.length > 0 && (
              <span className="bg-blue-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {pendingProducts.length}
              </span>
            )}
          </button>
        </div>
      )}

      {/* ── Product Registration Queue ─────────────────────────────────────────── */}
      {activeView === 'products' && (
        <div className="space-y-4">
          {pendingProducts.length === 0 && Object.keys(productActed).length === 0 && (
            <div className="text-center py-12 text-gray-400 bg-white rounded-xl border border-gray-200">
              <Package className="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No products pending review.</p>
              <p className="text-xs mt-1">Products submitted via Register Product will appear here.</p>
            </div>
          )}
          {Object.entries(productActed).map(([ref, action]) => (
            <div key={ref} className={`rounded-xl border-2 p-5 ${action === 'published' ? 'border-emerald-300 bg-emerald-50/30' : 'border-red-300 bg-red-50/30'}`}>
              <div className="flex items-center gap-2">
                {action === 'published' ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <XCircle className="h-5 w-5 text-red-500" />}
                <span className="text-sm font-medium text-gray-700">{ref} — {action === 'published' ? 'Published to catalog ✓' : 'Rejected'}</span>
              </div>
            </div>
          ))}
          {pendingProducts.map(p => {
            const tags = Array.isArray(p.tags) ? p.tags
              : typeof p.tags === 'string' ? (p.tags.startsWith('[') ? JSON.parse(p.tags) : p.tags.split(',')) : []
            return (
              <div key={p.product_ref} className="bg-white rounded-xl border-2 border-blue-200 p-5">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="text-xs font-mono text-gray-400">{p.product_ref}</span>
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">Pending Review</span>
                      <span className="text-xs text-gray-400">{p.domain || p.source_system}</span>
                    </div>
                    <div className="flex items-center gap-2 mb-3">
                      <Database className="h-4 w-4 text-gray-400 shrink-0" />
                      <h3 className="font-semibold text-gray-900">{p.display_name}</h3>
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{p.type}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                      <span className="flex items-center gap-1.5"><User className="h-3.5 w-3.5" /> {p.owner_email}</span>
                      <span>{p.classification} · {p.refresh_frequency}</span>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600 border border-gray-100">
                      <p className="text-xs font-medium text-gray-400 mb-1">Description</p>
                      {p.description}
                    </div>
                    {tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {tags.map(t => <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">{t}</span>)}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => handlePublish(p.product_ref, p.display_name)}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors"
                    >
                      <CheckCircle2 className="h-4 w-4" /> Publish
                    </button>
                    <button
                      onClick={() => handleRejectProduct(p.product_ref)}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-red-600 border-2 border-red-200 hover:bg-red-50 transition-colors"
                    >
                      <XCircle className="h-4 w-4" /> Reject
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Access Request Queue ───────────────────────────────────────────────── */}
      {activeView === 'access' && (<>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Pending', count: counts.Pending, color: 'amber', icon: Clock },
          { label: 'Approved', count: counts.Approved, color: 'emerald', icon: CheckCircle2 },
          { label: 'Denied', count: counts.Denied, color: 'red', icon: XCircle },
        ].map(({ label, count, color, icon: Icon }) => (
          <button
            key={label}
            onClick={() => setFilter(label)}
            className={`bg-white rounded-xl border-2 p-4 flex items-center gap-3 transition-colors ${filter === label ? `border-${color}-400` : 'border-gray-200 hover:border-gray-300'}`}
          >
            <Icon className={`h-8 w-8 text-${color}-500`} />
            <div className="text-left">
              <p className={`text-2xl font-bold text-${color}-600`}>{count}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {['Pending', 'Approved', 'Denied', 'All'].map(tab => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              filter === tab ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
            {tab !== 'All' && <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${filter === tab ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}`}>{counts[tab] || 0}</span>}
          </button>
        ))}
      </div>

      {/* Request cards */}
      <div className="space-y-4">
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400 bg-white rounded-xl border border-gray-200">
            <CheckCircle2 className="h-10 w-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No {filter.toLowerCase()} requests.</p>
          </div>
        )}

        {filtered.map(req => {
          const acted = justActed[req.id]
          return (
            <div
              key={req.id}
              className={`bg-white rounded-xl border-2 p-5 transition-all ${
                acted === 'approved' ? 'border-emerald-300 bg-emerald-50/30'
                : acted === 'denied' ? 'border-red-300 bg-red-50/30'
                : req.status === 'Pending' ? 'border-amber-200' : 'border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1 min-w-0">
                  {/* Header */}
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className="text-xs font-mono text-gray-400">{req.id}</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      req.status === 'Pending' ? 'bg-amber-100 text-amber-800'
                      : req.status === 'Approved' ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-red-100 text-red-800'
                    }`}>
                      {req.status}
                    </span>
                    <span className="text-xs text-gray-400">{timeAgo(req.requestedAt)}</span>
                  </div>

                  {/* Product */}
                  <div className="flex items-center gap-2 mb-3">
                    <Database className="h-4 w-4 text-gray-400 shrink-0" />
                    <h3 className="font-semibold text-gray-900">{req.productName}</h3>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{req.accessLevel}</span>
                  </div>

                  {/* Requester */}
                  <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                    <span className="flex items-center gap-1.5">
                      <User className="h-3.5 w-3.5" />
                      <strong className="text-gray-700">{req.requesterName}</strong> · {req.requesterEmail}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5" />
                      {req.requesterTeam}
                    </span>
                  </div>

                  {/* Reason */}
                  <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600 border border-gray-100">
                    <p className="text-xs font-medium text-gray-400 mb-1">Business Justification</p>
                    {req.reason}
                  </div>

                  {req.expiresAt && req.status === 'Approved' && (
                    <div className="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-1.5 mt-2 w-fit">
                      <Clock className="h-3.5 w-3.5" />
                      Access expires {new Date(req.expiresAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                  )}
                  {req.denyReason && (
                    <div className="bg-red-50 rounded-lg p-3 text-sm text-red-700 border border-red-100 mt-2">
                      <p className="text-xs font-medium text-red-400 mb-1">{req.status === 'Revoked' ? 'Revocation Reason' : 'Denial Reason'}</p>
                      {req.denyReason}
                    </div>
                  )}

                  <UCGrantPanel request={req} action={req.status} />
                </div>

                {/* Action buttons */}
                {req.status === 'Pending' && (
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => handleApprove(req.id)}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors"
                    >
                      <CheckCircle2 className="h-4 w-4" /> Approve
                    </button>
                    <button
                      onClick={() => setDenyModal(req.id)}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-red-700 border border-red-200 hover:bg-red-50 transition-colors"
                    >
                      <XCircle className="h-4 w-4" /> Deny
                    </button>
                  </div>
                )}

                {req.status !== 'Pending' && (
                  <div className="flex items-center gap-2 shrink-0 flex-wrap">
                    <div className={`flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-full ${
                      req.status === 'Approved' ? 'bg-emerald-100 text-emerald-700'
                      : req.status === 'Revoked' ? 'bg-orange-100 text-orange-700'
                      : 'bg-red-100 text-red-700'}`}>
                      {req.status === 'Approved' ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                      {req.status}
                    </div>
                    {req.status === 'Approved' && (
                      <button
                        onClick={() => { setRevokeModal(req.id); setRevokeReason('') }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-orange-700 border border-orange-200 hover:bg-orange-50 transition-colors"
                      >
                        <XCircle className="h-3.5 w-3.5" /> Revoke
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
      </>) }

      {/* Deny modal */}
      {denyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Deny Access Request</h3>
            <p className="text-sm text-gray-600 mb-4">
              Provide a reason for denying this request. The requester will be notified.
            </p>
            <textarea
              rows={3}
              placeholder="e.g. Insufficient business justification. Please resubmit with your manager's approval."
              value={denyReason}
              onChange={e => setDenyReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-400 resize-none mb-4"
            />
            <div className="flex gap-3">
              <button onClick={() => { setDenyModal(null); setDenyReason('') }} className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
              <button onClick={handleDeny} className="flex-1 py-2.5 rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-700">
                Deny Request
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Revoke modal */}
      {revokeModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-1">Revoke Access</h3>
            <p className="text-sm text-gray-500 mb-4">
              This will immediately remove the user's access and issue a UC REVOKE statement. The user will be notified.
            </p>
            <textarea
              rows={3}
              placeholder="e.g. Project completed. Access no longer required."
              value={revokeReason}
              onChange={e => setRevokeReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 resize-none mb-4"
            />
            <div className="flex gap-3">
              <button onClick={() => { setRevokeModal(null); setRevokeReason('') }} className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
              <button onClick={handleRevoke} className="flex-1 py-2.5 rounded-lg text-sm font-medium text-white bg-orange-600 hover:bg-orange-700">
                Revoke Access
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

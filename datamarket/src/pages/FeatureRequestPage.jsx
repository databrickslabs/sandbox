import React, { useState, useEffect, useCallback } from 'react'
import { ChevronUp, Plus, X, Lightbulb, MapPin, CheckCircle2 } from 'lucide-react'
import { usePersona } from '@/context/PersonaContext'

const DataMarket_BLUE = '#003865'

const STATUS_CONFIG = {
  open:        { label: 'Open',        color: 'bg-gray-100 text-gray-600' },
  on_roadmap:  { label: 'On Roadmap',  color: 'bg-orange-100 text-orange-700' },
  done:        { label: 'Done',        color: 'bg-emerald-100 text-emerald-700' },
  declined:    { label: 'Declined',    color: 'bg-red-100 text-red-600' },
}

const TABS = ['All', 'On Roadmap', 'My Requests', 'Done']

export function FeatureRequestPage() {
  const { persona, isAdmin } = usePersona()
  const [requests, setRequests]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [search, setSearch]       = useState('')
  const [activeTab, setActiveTab] = useState('All')
  const [showNew, setShowNew]     = useState(false)
  const [newForm, setNewForm]     = useState({ title: '', description: '' })
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [votingId, setVotingId]   = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    fetch('/api/portal/feature-requests')
      .then(r => r.json())
      .then(rows => { if (Array.isArray(rows)) setRequests(rows) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const handleVote = async (id) => {
    setVotingId(id)
    try {
      const r = await fetch(`/api/portal/feature-requests/${id}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requester_email: persona?.email || '' })
      })
      if (!r.ok) console.error('Vote failed:', r.status)
    } catch (e) {
      console.error('Vote error:', e)
    } finally {
      setVotingId(null)
      load() // always reload so button state reflects server truth
    }
  }

  const handleSubmit = async () => {
    if (!newForm.title.trim()) return
    setSubmitting(true)
    setSubmitError('')
    try {
      const r = await fetch('/api/portal/feature-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newForm,
          requester_email: persona?.email || 'anonymous',
          requester_name:  persona?.name  || '',
        })
      })
      if (r.ok) {
        setShowNew(false)
        setNewForm({ title: '', description: '' })
        setSubmitError('')
        load()
      } else {
        const body = await r.json().catch(() => ({}))
        setSubmitError(body.error || `Server error (${r.status}) — please try again.`)
      }
    } catch (e) {
      setSubmitError('Network error — please check your connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleStatus = async (id, status) => {
    await fetch(`/api/portal/feature-requests/${id}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    })
    load()
  }

  const email = persona?.email || ''

  const filtered = requests.filter(r => {
    if (search && !r.title.toLowerCase().includes(search.toLowerCase())) return false
    if (activeTab === 'On Roadmap') return r.status === 'on_roadmap'
    if (activeTab === 'My Requests') return r.requester_email === email || (r.voter_emails || []).includes(email)
    if (activeTab === 'Done') return r.status === 'done'
    return r.status !== 'declined' // All tab hides declined by default
  })

  const roadmap = requests.filter(r => r.status === 'on_roadmap')

  return (
    <div className="max-w-5xl mx-auto space-y-6 py-4">

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: DataMarket_BLUE }}>
            <Lightbulb className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Data Requests</h1>
            <p className="text-sm text-gray-500">Tell us what data you need — upvote what matters most</p>
          </div>
        </div>
        <button onClick={() => { setShowNew(true); setSubmitError('') }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ backgroundColor: DataMarket_BLUE }}>
          <Plus className="h-4 w-4" /> New request
        </button>
      </div>

      {/* New request modal */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Request data</h2>
              <button onClick={() => setShowNew(false)}><X className="h-5 w-5 text-gray-400 hover:text-gray-600" /></button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">What data do you need? *</label>
              <input type="text" value={newForm.title} autoFocus
                onChange={e => setNewForm(f => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Vendor spend by cost center"
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Why do you need it? <span className="text-gray-400 font-normal">(optional)</span></label>
              <textarea rows={3} value={newForm.description}
                onChange={e => setNewForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe your use case — helps stewards understand priority"
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none" />
            </div>
            {submitError && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700">{submitError}</div>
            )}
            <div className="flex gap-2 pt-1">
              <button onClick={handleSubmit} disabled={submitting || !newForm.title.trim()}
                className="flex-1 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
                style={{ backgroundColor: DataMarket_BLUE }}>
                {submitting ? 'Submitting...' : 'Submit request'}
              </button>
              <button onClick={() => setShowNew(false)}
                className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Left: request list ── */}
        <div className="lg:col-span-2 space-y-4">
          {/* Search + tabs */}
          <div className="space-y-3">
            <input type="text" placeholder="Search by title..." value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
              {TABS.map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    activeTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}>
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* List */}
          {loading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 py-12 text-center">
              <p className="text-sm text-gray-400">No requests yet. Be the first!</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map(r => {
                const hasVoted = r.user_voted || (r.voter_emails || []).includes(email) || r.requester_email === email
                const st = STATUS_CONFIG[r.status] || STATUS_CONFIG.open
                return (
                  <div key={r.request_id} className="bg-white border border-gray-200 rounded-xl p-4 flex gap-4 hover:border-blue-200 transition-colors">
                    {/* Upvote */}
                    <button onClick={() => handleVote(r.request_id)} disabled={votingId === r.request_id}
                      className={`flex flex-col items-center gap-0.5 w-10 shrink-0 rounded-lg py-2 border transition-colors ${
                        hasVoted
                          ? 'bg-blue-50 border-blue-200 text-blue-700'
                          : 'bg-gray-50 border-gray-200 text-gray-400 hover:border-blue-200 hover:text-blue-600'
                      }`}>
                      <ChevronUp className="h-4 w-4" />
                      <span className="text-xs font-semibold">{r.upvotes}</span>
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900 leading-snug">{r.title}</p>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0 ${st.color}`}>{st.label}</span>
                      </div>
                      {r.description && (
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{r.description}</p>
                      )}
                      <p className="text-[11px] text-gray-400 mt-1.5">
                        Requested by {r.requester_name || r.requester_email}
                        {(r.voter_emails?.length > 1) && ` · ${r.voter_emails.length} upvotes`}
                      </p>
                    </div>

                    {/* Admin status control */}
                    {isAdmin && (
                      <select value={r.status}
                        onChange={e => handleStatus(r.request_id, e.target.value)}
                        className="text-xs border border-gray-200 rounded-lg px-2 py-1 text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-400 shrink-0 self-start">
                        <option value="open">Open</option>
                        <option value="on_roadmap">On Roadmap</option>
                        <option value="done">Done</option>
                        <option value="declined">Declined</option>
                      </select>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* ── Right: roadmap ── */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-3">
              <MapPin className="h-4 w-4 text-orange-500" />
              <h3 className="text-sm font-semibold text-gray-800">Roadmap</h3>
              <span className="text-xs text-gray-400 ml-auto">Ranked by upvotes</span>
            </div>
            {roadmap.length === 0 ? (
              <p className="text-xs text-gray-400 py-4 text-center">Nothing on the roadmap yet.</p>
            ) : (
              <div className="space-y-2">
                {roadmap.map((r, i) => (
                  <div key={r.request_id} className="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0">
                    <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0 mt-0.5"
                      style={{ backgroundColor: DataMarket_BLUE }}>{i + 1}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-800 leading-snug">{r.title}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{r.upvotes} upvote{r.upvotes !== 1 ? 's' : ''} · {r.requester_name || r.requester_email}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 space-y-1.5">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-600" />
              <p className="text-xs font-semibold text-blue-800">How this works</p>
            </div>
            <p className="text-[11px] text-blue-700 leading-relaxed">
              Submit what data you need. Upvote requests from others. Data stewards use the vote count to prioritise what to publish next.
            </p>
          </div>
        </div>

      </div>
    </div>
  )
}

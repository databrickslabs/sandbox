import React, { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Sparkles, CheckCircle, Clock, AlertCircle, Bell, ChevronRight, Database, RotateCcw } from 'lucide-react'
import { usePersona } from '../context/PersonaContext'

const DataMarket_BLUE = '#003865'

const allProducts = [
  { id: 1, ref: 'DP-001', name: 'Budget Expenditure Report', category: 'Budget', owner: 'james.park', steward: 'Sarah Johnson' },
  { id: 2, ref: 'DP-002', name: 'Employee Metrics Dashboard', category: 'HRIS', owner: 'sarah.kim', steward: 'Sarah Johnson' },
  { id: 3, ref: 'DP-003', name: 'Property Tax Report 2024', category: 'Property Tax', owner: 'robert.lee', steward: 'Sarah Johnson' },
  { id: 4, ref: 'DP-004', name: 'Census 2023 Dataset', category: 'Demographics', owner: 'diana.torres', steward: 'Sarah Johnson' },
  { id: 5, ref: 'DP-005', name: 'Service Ticket Tracking Report', category: 'Accounting', owner: 'michael.chang', steward: 'Sarah Johnson' },
  { id: 6, ref: 'DP-006', name: 'Essential Service Usage Report', category: 'Health Services', owner: 'angela.wright', steward: 'Sarah Johnson' },
  { id: 7, ref: 'DP-007', name: 'Payroll Dashboard', category: 'Payroll', owner: 'james.park', steward: 'Sarah Johnson' },
  { id: 8, ref: 'DP-008', name: 'Property Tax Dashboard', category: 'Property Tax', owner: 'robert.lee', steward: 'Sarah Johnson' },
  { id: 9, ref: 'DP-009', name: 'Population by Age 2020 Dataset', category: 'Demographics', owner: 'diana.torres', steward: 'Sarah Johnson' },
  { id: 10, ref: 'DP-010', name: 'Enterprise Budget Analytics Dashboard', category: 'Budget', owner: 'john.doe', steward: 'Sarah Johnson' },
  { id: 11, ref: 'DP-011', name: 'Audit Finding Tracker', category: 'Audit', owner: 'david.nguyen', steward: 'Sarah Johnson' },
  { id: 12, ref: 'DP-012', name: 'GIS Infrastructure Map', category: 'GIS', owner: 'john.doe', steward: 'Sarah Johnson' },
]

const statusIcon = (status) => {
  if (status === 'Approved') return <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
  if (status === 'Denied') return <AlertCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
  return <Clock className="h-3.5 w-3.5 text-amber-500 shrink-0" />
}

const statusColor = (status) => {
  if (status === 'Approved') return 'text-green-700 bg-green-50 border-green-200'
  if (status === 'Denied') return 'text-red-700 bg-red-50 border-red-200'
  return 'text-amber-700 bg-amber-50 border-amber-200'
}

function buildResponse(input, persona, myRequests, pendingRequests, hasAccess, apiAvailable, onNudge) {
  const q = input.toLowerCase()

  // ── Admin: approvals queue (must come before status check) ───────────────
  if (/approval|waiting on me|pending approval|queue|review|need.*approve/.test(q)) {
    if (!isAdmin) {
      return {
        text: `Only Data Stewards can view the approval queue. You can check the status of your own requests instead.`,
        chips: ['Check my request status']
      }
    }
    if (pendingRequests.length === 0) {
      return {
        text: `No pending approvals right now — you're all caught up! All submitted requests have been resolved.`,
        actions: [{ label: 'Open Admin Panel', page: 'admin' }]
      }
    }
    return {
      text: `You have ${pendingRequests.length} request${pendingRequests.length > 1 ? 's' : ''} waiting for your review:`,
      requests: pendingRequests.slice(0, 4),
      followUp: `Head to the Admin panel to approve or deny with a single click.`,
      actions: [{ label: 'Open Admin Panel', page: 'admin' }]
    }
  }

  // ── Status of my requests ─────────────────────────────────────────────────
  if (/status|check.*request|my request|pending|approved|denied/.test(q)) {
    if (myRequests.length === 0) {
      return {
        text: `You have no open access requests, ${persona.name}. Head to the Data Catalog to find datasets and request access.`,
        actions: [{ label: 'Browse Catalog', page: 'discover' }]
      }
    }
    const pending = myRequests.filter(r => r.status === 'Pending')
    const approved = myRequests.filter(r => r.status === 'Approved')
    const denied = myRequests.filter(r => r.status === 'Denied')
    return {
      text: `Here's your request summary, ${persona.name}:`,
      requests: myRequests.slice(0, 4),
      followUp: pending.length > 0
        ? `You have ${pending.length} pending request${pending.length > 1 ? 's' : ''}. Want me to send a nudge to the approver?`
        : approved.length > 0
        ? `${approved.length} request${approved.length > 1 ? 's have' : ' has'} been approved — check your Library.`
        : null,
      nudgeable: pending.length > 0 ? pending[0] : null,
      onNudge
    }
  }

  // ── Nudge approver ────────────────────────────────────────────────────────
  if (/nudge|remind|follow.?up|ping|chase|hasn.?t|haven.?t heard/.test(q)) {
    const pending = myRequests.filter(r => r.status === 'Pending')
    if (pending.length === 0) {
      return { text: `No pending requests to follow up on right now. All your requests have been resolved.` }
    }
    return {
      text: `I can send a reminder to the Data Steward for your pending request${pending.length > 1 ? 's' : ''}:`,
      nudgeable: pending[0],
      onNudge,
      followUp: 'Click the button below to notify the approver.'
    }
  }

  // ── What can I access ─────────────────────────────────────────────────────
  if (/what.*access|my.*data|can.*access|have access|library|approved/.test(q)) {
    const accessible = allProducts.filter(p => hasAccess(p.ref))
    if (accessible.length === 0) {
      return {
        text: `You don't have approved access to any datasets yet, ${persona.name}. Browse the catalog to find what you need and submit a request.`,
        actions: [{ label: 'Browse Catalog', page: 'discover' }]
      }
    }
    return {
      text: `You currently have access to ${accessible.length} data product${accessible.length > 1 ? 's' : ''}:`,
      products: accessible.slice(0, 5),
      followUp: accessible.length > 5 ? `...and ${accessible.length - 5} more. Check your Library for the full list.` : null,
      actions: [{ label: 'View My Data', page: 'my-access' }]
    }
  }

  // ── Who approves / owns what ──────────────────────────────────────────────
  if (/who.*approve|who.*own|data steward|data owner|approver|contact/.test(q)) {
    return {
      text: `All access requests in DataMarket are reviewed by the Data Steward team. For specific datasets:`,
      products: allProducts.slice(0, 4).map(p => ({ ...p, showOwner: true })),
      followUp: 'Submit a request from any product page and the steward is notified automatically.'
    }
  }

  // ── Find/discover data ────────────────────────────────────────────────────
  if (/find|search|look for|do we have|is there|data about|dataset/.test(q)) {
    const keywords = q.replace(/find|search|look for|do we have|is there|data about|dataset|any/g, '').trim().split(/\s+/).filter(w => w.length > 2)
    const matches = allProducts.filter(p =>
      keywords.some(k =>
        p.name.toLowerCase().includes(k) ||
        p.category.toLowerCase().includes(k)
      )
    )
    if (matches.length === 0) {
      return {
        text: `I didn't find an exact match for that topic. Browse the full catalog — it has 12 data products across Budget, HR, Property Tax, Demographics, and more.`,
        actions: [{ label: 'Browse Catalog', page: 'discover' }]
      }
    }
    return {
      text: `Found ${matches.length} data product${matches.length > 1 ? 's' : ''} matching your query:`,
      products: matches.slice(0, 4),
      actions: matches.length > 0 && !hasAccess(matches[0].ref)
        ? [{ label: `Request Access to ${matches[0].name.split(' ').slice(0, 3).join(' ')}...`, page: 'discover' }]
        : [{ label: 'View in Catalog', page: 'discover' }]
    }
  }

  // ── How to request access ─────────────────────────────────────────────────
  if (/how.*request|request.*access|get access|apply|submit/.test(q)) {
    return {
      text: `Requesting access is simple:`,
      steps: [
        'Go to the Data Catalog (click "Data" in the nav)',
        'Click any data product to open its detail page',
        'Click "Request Access" and fill in your business justification',
        'The Data Steward is notified and typically responds within 1-2 business days',
        'Once approved, the dataset appears in your Library'
      ],
      actions: [{ label: 'Go to Catalog', page: 'discover' }]
    }
  }

  // ── Greetings ─────────────────────────────────────────────────────────────
  if (/^(hi|hello|hey|help|what can you|what do you)/.test(q)) {
    const pending = myRequests.filter(r => r.status === 'Pending')
    if (isAdmin) {
      return {
        text: `Hi ${persona.name}! As Data Steward I can help you:`,
        chips: ['Approvals waiting on me', 'Show all pending requests', 'Who has access to what?', 'How does approval work?']
      }
    }
    return {
      text: `Hi ${persona.name}! I'm your DataMarket assistant. I can help you with:`,
      chips: ['Check my request status', 'What data can I access?', 'Find budget data', 'How do I request access?', pending.length > 0 ? 'Nudge my approver' : 'Who owns payroll data?']
    }
  }

  // ── Default ───────────────────────────────────────────────────────────────
  return {
    text: `I can help you with access requests, data discovery, and navigating DataMarket. Try asking:`,
    chips: ['Check my request status', 'What data can I access?', 'Find payroll data', 'Who approves requests?']
  }
}

function Message({ msg, onChipClick, onPageNavigate }) {
  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-3`}>
      {msg.role === 'assistant' && (
        <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mr-2 mt-0.5"
          style={{ backgroundColor: DataMarket_BLUE }}>
          <Sparkles className="h-3 w-3 text-white" />
        </div>
      )}
      <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-first' : ''}`}>
        {msg.role === 'user' ? (
          <div className="px-3 py-2 rounded-2xl rounded-tr-sm text-sm text-white"
            style={{ backgroundColor: DataMarket_BLUE }}>
            {msg.content}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="px-3 py-2 rounded-2xl rounded-tl-sm bg-white border border-gray-200 text-sm text-gray-800 shadow-sm">
              {msg.content}
            </div>

            {/* Request status list */}
            {msg.requests && (
              <div className="space-y-1.5">
                {msg.requests.map((r, i) => (
                  <div key={i} className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs ${statusColor(r.status)}`}>
                    {statusIcon(r.status)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{r.product_name || r.product_ref}</p>
                      <p className="opacity-70">{r.status} · {r.requested_at ? new Date(r.requested_at).toLocaleDateString() : 'Recently'}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Product list */}
            {msg.products && (
              <div className="space-y-1.5">
                {msg.products.map((p, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 bg-white text-xs">
                    <Database className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">{p.name}</p>
                      {p.showOwner
                        ? <p className="text-gray-500">Owner: {p.owner} · Steward: {p.steward}</p>
                        : <p className="text-gray-500">{p.category}</p>
                      }
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Steps list */}
            {msg.steps && (
              <div className="space-y-1">
                {msg.steps.map((s, i) => (
                  <div key={i} className="flex items-start gap-2 px-3 py-1.5 text-xs text-gray-700">
                    <span className="w-4 h-4 rounded-full text-[10px] flex items-center justify-center shrink-0 font-bold text-white mt-0.5"
                      style={{ backgroundColor: DataMarket_BLUE }}>{i + 1}</span>
                    {s}
                  </div>
                ))}
              </div>
            )}

            {/* Follow-up text */}
            {msg.followUp && (
              <div className="px-3 py-2 rounded-2xl rounded-tl-sm bg-white border border-gray-200 text-sm text-gray-600 shadow-sm italic">
                {msg.followUp}
              </div>
            )}

            {/* Nudge button */}
            {msg.nudgeable && msg.onNudge && (
              <button
                onClick={() => msg.onNudge(msg.nudgeable)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-white w-full transition-opacity hover:opacity-90"
                style={{ backgroundColor: '#D97706' }}
              >
                <Bell className="h-3.5 w-3.5" />
                Send reminder for "{(msg.nudgeable.product_name || msg.nudgeable.product_ref || '').slice(0, 30)}..."
              </button>
            )}

            {/* Action buttons */}
            {msg.actions && (
              <div className="flex flex-wrap gap-1.5">
                {msg.actions.map((a, i) => (
                  <button key={i}
                    onClick={() => onPageNavigate && onPageNavigate(a.page)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90"
                    style={{ backgroundColor: DataMarket_BLUE }}
                  >
                    {a.label} <ChevronRight className="h-3 w-3" />
                  </button>
                ))}
              </div>
            )}

            {/* Quick chips */}
            {msg.chips && (
              <div className="flex flex-wrap gap-1.5">
                {msg.chips.map((c, i) => (
                  <button key={i}
                    onClick={() => onChipClick(c)}
                    className="px-2.5 py-1 rounded-full text-xs border border-gray-300 bg-white text-gray-600 hover:bg-gray-50 hover:border-gray-400 transition-colors"
                  >
                    {c}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function DataMarketAssistant({ onNavigate }) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [nudgedRefs, setNudgedRefs] = useState(new Set())
  const [unread, setUnread] = useState(0)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const { persona, myRequests, pendingRequests, hasAccess, apiAvailable, isAdmin } = usePersona()

  const buildGreeting = (p, myReqs, pendingReqs) => {
    if (p.id === 'admin') {
      return pendingReqs.length > 0
        ? {
            role: 'assistant',
            content: `Hi ${p.name}! There are ${pendingReqs.length} access request${pendingReqs.length > 1 ? 's' : ''} waiting for your review.`,
            chips: ['Approvals waiting on me', 'Who has access to what?', 'Show all pending requests']
          }
        : {
            role: 'assistant',
            content: `Hi ${p.name}! No pending approvals right now. Everything's up to date.`,
            chips: ['Who has access to what?', 'Show all pending requests', 'How does approval work?']
          }
    }
    const pending = myReqs.filter(r => r.status === 'Pending')
    return pending.length > 0
      ? {
          role: 'assistant',
          content: `Hi ${p.name}! You have ${pending.length} pending access request${pending.length > 1 ? 's' : ''}. Want me to check the status or send a reminder?`,
          chips: ['Check my request status', 'Nudge my approver', 'What data can I access?']
        }
      : {
          role: 'assistant',
          content: `Hi ${p.name}! I can help with data access, request status, or finding the right dataset.`,
          chips: ['Check my request status', 'What data can I access?', 'Find budget data', 'How do I request access?']
        }
  }

  const resetChat = () => {
    setNudgedRefs(new Set())
    setMessages([buildGreeting(persona, myRequests, pendingRequests)])
    setTimeout(() => inputRef.current?.focus(), 100)
  }

  // Fire greeting whenever open becomes true OR persona changes while open
  useEffect(() => {
    if (open) {
      setUnread(0)
      if (messages.length === 0) {
        setMessages([buildGreeting(persona, myRequests, pendingRequests)])
      }
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  // Persona switch — always reset and re-greet
  useEffect(() => {
    setNudgedRefs(new Set())
    const greeting = buildGreeting(persona, myRequests, pendingRequests)
    if (open) {
      setMessages([greeting])
    } else {
      setMessages([])
      setUnread(1)
    }
  }, [persona.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleNudge = async (request) => {
    const ref = request.request_ref || request.id
    if (nudgedRefs.has(ref)) {
      addAssistantMessage({ content: `I already sent a reminder for that request. Give the approver a little more time — they've been notified.` })
      return
    }
    try {
      await fetch(`/api/portal/requests/${ref}/nudge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requesterEmail: persona.email, productName: request.product_name })
      })
    } catch (e) { /* silent — nudge is best-effort */ }
    setNudgedRefs(prev => new Set([...prev, ref]))
    addAssistantMessage({
      content: `✓ Reminder sent to the Data Steward for "${request.product_name || request.product_ref}". They've been notified that your request is waiting. You'll typically hear back within 1 business day.`
    })
  }

  const addAssistantMessage = (msg) => {
    setMessages(prev => [...prev, { role: 'assistant', ...msg }])
  }

  const sendMessage = (text) => {
    const userText = text || input.trim()
    if (!userText) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userText }])

    setTimeout(() => {
      const response = buildResponse(userText, persona, myRequests, pendingRequests, hasAccess, apiAvailable, handleNudge)
      addAssistantMessage(response)
    }, 400)
  }

  return (
    <>
      {/* Floating bubble */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-transform hover:scale-105 active:scale-95"
          style={{ backgroundColor: DataMarket_BLUE }}
          aria-label="Open DataMarket Assistant"
        >
          <MessageCircle className="h-6 w-6 text-white" />
          {unread > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-white text-[10px] font-bold flex items-center justify-center">
              {unread}
            </span>
          )}
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-80 sm:w-96 flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-gray-200"
          style={{ height: '520px' }}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 shrink-0" style={{ backgroundColor: DataMarket_BLUE }}>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-white text-sm font-semibold">DataMarket Assistant</p>
                <p className="text-white/70 text-[10px]">Powered by Databricks</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={resetChat}
                className="text-white/60 hover:text-white transition-colors p-1.5 rounded"
                title="Reset conversation"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
              <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white transition-colors p-1 rounded">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 bg-gray-50 space-y-1">
            {messages.map((msg, i) => (
              <Message
                key={i}
                msg={msg}
                onChipClick={sendMessage}
                onPageNavigate={(page) => { onNavigate(page); setOpen(false) }}
              />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-3 py-3 bg-white border-t border-gray-200 shrink-0">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage()}
                placeholder="Ask about your data access..."
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim()}
                className="p-2 rounded-lg text-white disabled:opacity-40 transition-opacity"
                style={{ backgroundColor: DataMarket_BLUE }}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

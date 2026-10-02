import React, { useState, useRef, useEffect } from 'react'
import { Bot, Send, Sparkles, Database, BarChart3, FileText, RotateCcw, Search, ExternalLink, Tag, ArrowRight, BookOpen, ClipboardCheck, Zap, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAppConfig } from '@/context/AppConfigContext'

const TYPE_ICONS = { Dashboard: BarChart3, Report: FileText, Dataset: Database }
const DataMarket_BLUE = '#003865'

const DOMAIN_COLORS = {
  Finance:     { bg: 'bg-emerald-50',  text: 'text-emerald-700',  border: 'border-emerald-200' },
  HR:          { bg: 'bg-violet-50',   text: 'text-violet-700',   border: 'border-violet-200' },
  Operations:  { bg: 'bg-blue-50',     text: 'text-blue-700',     border: 'border-blue-200' },
  'Public Safety': { bg: 'bg-red-50',  text: 'text-red-700',      border: 'border-red-200' },
  Technology:  { bg: 'bg-cyan-50',     text: 'text-cyan-700',     border: 'border-cyan-200' },
  Analytics:   { bg: 'bg-amber-50',    text: 'text-amber-700',    border: 'border-amber-200' },
  Other:       { bg: 'bg-gray-50',     text: 'text-gray-600',     border: 'border-gray-200' },
}
function domainColor(d) { return DOMAIN_COLORS[d] || DOMAIN_COLORS.Other }

const HOW_IT_WORKS = [
  {
    icon: Search,
    step: '1. Describe what you need',
    detail: 'Type a business question, topic, or use case in plain English.',
  },
  {
    icon: BookOpen,
    step: '2. AI finds matching data',
    detail: 'Databricks AI scans your catalog and explains why each product fits.',
  },
  {
    icon: ClipboardCheck,
    step: '3. Request access',
    detail: 'Open a product and click "Request Access" — a steward reviews and approves.',
  },
  {
    icon: Zap,
    step: '4. Query immediately',
    detail: 'Once approved, open the table in UC Explorer or copy a ready-to-run SQL snippet.',
  },
]

export function AIExplorerPage({ initialQuestion = '', onNavigate, onOpenProduct }) {
  const { demoMode } = useAppConfig()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [domains, setDomains] = useState([])
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const initialSent = useRef(false)

  // Load real domains from catalog on mount
  useEffect(() => {
    fetch('/api/portal/products?includeAll=false')
      .then(r => r.json())
      .then(products => {
        if (!Array.isArray(products)) return
        const counts = {}
        products.forEach(p => {
          const d = p.domain || 'Other'
          counts[d] = (counts[d] || 0) + 1
        })
        setDomains(Object.entries(counts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 7)
          .map(([name, count]) => ({ name, count }))
        )
      })
      .catch(() => {})
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const sendQuestion = async (question) => {
    if (!question.trim() || loading) return
    const q = question.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setLoading(true)

    try {
      const r = await fetch('/api/portal/ask-catalog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.error || 'API error')

      if (data.matches?.length > 0) {
        setMessages(prev => [...prev, { role: 'assistant', type: 'products', matches: data.matches, question: q }])
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant', type: 'empty', question: q,
          content: `No data products matched "${q}". Try rephrasing or browse the full catalog.`
        }])
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant', type: 'error',
        content: `Catalog search is unavailable right now. ${e.message}`
      }])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initialQuestion && !initialSent.current) {
      initialSent.current = true
      setTimeout(() => sendQuestion(initialQuestion), 200)
    }
  }, [initialQuestion])

  const openProduct = async (ref, name) => {
    try {
      const res = await fetch('/api/portal/products?includeAll=true')
      const products = await res.json()
      const p = products.find(x => x.product_ref === ref || x.display_name === name)
      if (p && onOpenProduct) {
        onOpenProduct({
          id: p.product_id, product_ref: p.product_ref, ref: p.product_ref,
          name: p.display_name, description: p.description, type: p.type,
          source: p.source_system, tags: Array.isArray(p.tags) ? p.tags : [],
          refreshFrequency: p.refresh_frequency, owner: p.owner_email,
          classification: p.classification, uc_full_name: p.uc_full_name, ucFullName: p.uc_full_name,
        })
        return
      }
    } catch (_) {}
    onNavigate?.('discover', { search: name })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: DataMarket_BLUE }}>
          <Bot className="h-5 w-5 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Explorer</h2>
          <p className="text-gray-500 text-sm">Find data products using natural language — powered by Databricks Foundation Models</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">

        {/* ── Chat panel ── */}
        <div className="xl:col-span-3">
          <Card className="flex flex-col min-h-[540px]">
            <CardContent className="flex-1 p-4 space-y-4 overflow-y-auto max-h-[540px]">

              {messages.length === 0 && !loading && (
                <div className="flex flex-col items-center justify-center h-64 text-center gap-3">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-blue-50">
                    <Search className="h-7 w-7 text-blue-500" />
                  </div>
                  <p className="font-semibold text-gray-800">What data are you looking for?</p>
                  <p className="text-sm text-gray-400 max-w-xs">Describe your use case or ask about a topic. I'll find the most relevant data products in your catalog.</p>
                  {domains.length > 0 && (
                    <div className="flex flex-wrap justify-center gap-2 mt-1 max-w-sm">
                      {domains.map(d => {
                        const c = domainColor(d.name)
                        return (
                          <button key={d.name}
                            onClick={() => sendQuestion(`What ${d.name} data products do we have?`)}
                            className={`text-xs px-3 py-1 rounded-full border font-medium transition-all hover:shadow-sm ${c.bg} ${c.text} ${c.border}`}>
                            {d.name} · {d.count}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'user' ? (
                    <div className="max-w-[75%] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-white" style={{ backgroundColor: DataMarket_BLUE }}>
                      {msg.content}
                    </div>
                  ) : (
                    <div className="max-w-[90%] w-full space-y-3">
                      <div className="flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                        <span className="text-xs font-medium text-blue-600">Catalog AI</span>
                      </div>

                      {msg.type === 'products' && (
                        <>
                          <p className="text-sm text-gray-600">
                            Found <span className="font-semibold text-gray-900">{msg.matches.length} data product{msg.matches.length > 1 ? 's' : ''}</span> relevant to <span className="italic">"{msg.question}"</span>:
                          </p>
                          <div className="space-y-2">
                            {msg.matches.map((m, mi) => {
                              const Icon = TYPE_ICONS[m.type] || Database
                              const c = domainColor(m.domain)
                              return (
                                <div key={mi} className="bg-white border border-gray-200 rounded-xl p-3.5 hover:border-blue-200 hover:shadow-sm transition-all">
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-start gap-3 flex-1 min-w-0">
                                      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: '#EFF6FF' }}>
                                        <Icon className="h-4 w-4" style={{ color: DataMarket_BLUE }} />
                                      </div>
                                      <div className="min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                          <span className="font-semibold text-sm text-gray-900">{m.name}</span>
                                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-medium ${c.bg} ${c.text} ${c.border}`}>{m.domain}</span>
                                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">{m.type}</span>
                                        </div>
                                        <p className="text-xs text-gray-500 mt-1 leading-relaxed">{m.reason}</p>
                                        {m.tags?.length > 0 && (
                                          <div className="flex flex-wrap gap-1 mt-1.5">
                                            {m.tags.slice(0, 4).map(t => (
                                              <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-50 border border-gray-100 text-gray-500 flex items-center gap-0.5">
                                                <Tag className="h-2 w-2" />{t}
                                              </span>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                    <button onClick={() => openProduct(m.ref, m.name)}
                                      className="shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-colors hover:opacity-90"
                                      style={{ backgroundColor: DataMarket_BLUE }}>
                                      View <ArrowRight className="h-3 w-3" />
                                    </button>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                          <button onClick={() => onNavigate?.('discover')}
                            className="text-xs text-blue-600 hover:underline flex items-center gap-1 pt-1">
                            <ExternalLink className="h-3 w-3" /> Browse full catalog
                          </button>
                        </>
                      )}

                      {(msg.type === 'empty' || msg.type === 'error') && (
                        <div className={`rounded-xl p-3.5 text-sm ${msg.type === 'error' ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-gray-50 text-gray-600 border border-gray-100'}`}>
                          <p>{msg.content}</p>
                          {msg.type === 'empty' && (
                            <button onClick={() => onNavigate?.('discover')}
                              className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1">
                              <ExternalLink className="h-3 w-3" /> Browse full catalog
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3 flex items-center gap-2">
                    <div className="flex gap-1">
                      {[0, 150, 300].map(d => (
                        <div key={d} className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
                      ))}
                    </div>
                    <span className="text-xs text-gray-500">Searching catalog...</span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </CardContent>

            <div className="border-t p-4">
              <div className="flex gap-2">
                <input ref={inputRef} type="text"
                  placeholder="What data are you looking for?"
                  className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendQuestion(input)}
                />
                <Button onClick={() => sendQuestion(input)} disabled={loading || !input.trim()} style={{ backgroundColor: DataMarket_BLUE }}>
                  <Send className="h-4 w-4" />
                </Button>
                {messages.length > 0 && (
                  <Button variant="outline" onClick={() => { setMessages([]); setInput('') }} title="Clear conversation">
                    <RotateCcw className="h-4 w-4 text-gray-500" />
                  </Button>
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-4">

          {/* Browse by domain */}
          {domains.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-gray-500 uppercase tracking-wide font-semibold">Browse by domain</CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-1">
                {domains.map(d => {
                  const c = domainColor(d.name)
                  return (
                    <button key={d.name}
                      onClick={() => sendQuestion(`Show me ${d.name} data products`)}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors group">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${c.bg.replace('bg-', 'bg-').replace('50', '400')}`}
                          style={{ backgroundColor: undefined }}
                        />
                        <span className="text-xs font-medium text-gray-700 group-hover:text-gray-900">{d.name}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-[10px] text-gray-400">{d.count}</span>
                        <ChevronRight className="h-3 w-3 text-gray-300 group-hover:text-gray-500" />
                      </div>
                    </button>
                  )
                })}
              </CardContent>
            </Card>
          )}

          {/* How it works */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs text-gray-500 uppercase tracking-wide font-semibold">How it works</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
              {HOW_IT_WORKS.map((step, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 bg-blue-50">
                    <step.icon className="h-3.5 w-3.5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-800">{step.step}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">{step.detail}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Tip */}
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="p-3.5">
              <p className="text-[11px] font-semibold text-amber-800 mb-1">Tip</p>
              <p className="text-[11px] text-amber-700 leading-relaxed">
                The more specific your question, the better. Try including the use case:
                <span className="italic"> "revenue data for Q4 budget forecasting"</span> rather than just
                <span className="italic"> "revenue"</span>.
              </p>
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  )
}

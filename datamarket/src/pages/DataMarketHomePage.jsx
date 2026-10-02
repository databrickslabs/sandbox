import React, { useState, useEffect } from 'react'
import { Search, ArrowRight, Clock, Sparkles, BarChart3, FileText, Database, Lock, Bot, LayoutDashboard, AppWindow, Cpu, Layers } from 'lucide-react'
import { usePersona } from '../context/PersonaContext'
import { useAppConfig } from '../context/AppConfigContext'

// Heuristic: treat input as a natural-language question if it looks conversational
function isNaturalLanguage(q) {
  if (!q || q.trim().split(/\s+/).length < 3) return false
  return /^(show|find|what|which|how|give|get|list|compare|who|why|tell|analyze|summarize|break|top|total|average|trend|where)\b/i.test(q.trim()) ||
    /\b(by department|by team|over time|last year|this year|vs |versus|trend|breakdown|summary|analysis|compared to)\b/i.test(q)
}

const DataMarket_BLUE = '#003865'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr)
  const mins = Math.floor(diff / 60000)
  if (mins < 2)   return 'Just now'
  if (mins < 60)  return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)   return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days === 1) return 'Yesterday'
  if (days < 7)   return `${days} days ago`
  return new Date(dateStr).toLocaleDateString()
}

function parseTags(tags) {
  if (Array.isArray(tags)) return tags
  if (typeof tags === 'string') return tags.replace(/[{}"]/g, '').split(',').map(t => t.trim()).filter(Boolean)
  return []
}

const tagColors = {
  Budget: 'bg-blue-100 text-blue-800',
  Financial: 'bg-green-100 text-green-800',
  'ERP System': 'bg-purple-100 text-purple-800',
  Payroll: 'bg-orange-100 text-orange-800',
  HR: 'bg-pink-100 text-pink-800',
  'Property Tax': 'bg-amber-100 text-amber-800',
  Revenue: 'bg-teal-100 text-teal-800',
  HRIS: 'bg-indigo-100 text-indigo-800',
  Demographics: 'bg-rose-100 text-rose-800',
}

const typeIcons = {
  Dashboard:         BarChart3,
  'AI/BI Dashboard': LayoutDashboard,
  'Genie Space':     Bot,
  Dataset:           Database,
  Report:            FileText,
  App:               AppWindow,
  'ML Model':        Cpu,
  Source:            Layers,
}

export function DataMarketHomePage({ onNavigate, onOpenProduct }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [featuredProducts, setFeaturedProducts] = useState([])
  const [recentlyAccessed, setRecentlyAccessed] = useState([])
  const [chips, setChips] = useState([])
  const { persona, hasAccess, myRequests, identityLoading } = usePersona()
  const { searchChips: configChips, appLogoUrl } = useAppConfig()

  // Load featured (3 most recently published products)
  useEffect(() => {
    fetch('/api/portal/products?includeAll=false')
      .then(r => r.json())
      .then(products => {
        if (!Array.isArray(products)) return
        const sorted = [...products]
          .sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0))
          .slice(0, 3)
          .map(p => ({
            id:               p.product_id,
            ref:              p.product_ref,
            name:             p.display_name,
            tags:             parseTags(p.tags),
            type:             p.type || 'Dataset',
            description:      p.description || '',
            source:           p.source_system || '-',
            refreshFrequency: p.refresh_frequency || 'Daily',
            owner:            p.owner_email || '-',
            uc_full_name:     p.uc_full_name,
          }))
        setFeaturedProducts(sorted)
      })
      .catch(() => {})
  }, [])

  // Chips: use admin-configured if present, otherwise auto-generate from catalog domains
  useEffect(() => {
    if (configChips?.length) {
      setChips(configChips)
      return
    }
    fetch('/api/portal/products?includeAll=false')
      .then(r => r.json())
      .then(products => {
        if (!Array.isArray(products)) return
        const counts = {}
        products.forEach(p => { const d = p.domain || 'Other'; counts[d] = (counts[d] || 0) + 1 })
        const topDomains = Object.entries(counts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([domain]) => ({ label: `✦ ${domain}`, q: `Show me ${domain} data products` }))
        setChips(topDomains)
      })
      .catch(() => {})
  }, [configChips])

  // Derive recently accessed from approved requests (most recent first)
  useEffect(() => {
    if (!myRequests) return
    const approved = myRequests
      .filter(r => r.status === 'Approved')
      .sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0))
      .slice(0, 4)
      .map(r => ({
        name:     r.product_name || r.display_name || r.name || 'Unknown',
        ref:      r.product_ref,
        type:     r.product_type || r.type || 'Dataset',
        accessed: timeAgo(r.updated_at),
        tags:     parseTags(r.tags),
        product:  r,
      }))
    setRecentlyAccessed(approved)
  }, [myRequests])

  const handleSearch = (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    onNavigate('ask-ai', { question: searchQuery })
  }

  const launchChip = (text) => {
    onNavigate('ask-ai', { question: text })
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 space-y-12">
      {/* Hero Search */}
      <div className="text-center space-y-4">
        <div className="flex flex-col items-center gap-2 mb-2">
          <img src={appLogoUrl || '/datamarket-logo.svg'} alt="DataMarket" className="w-16 h-16 rounded-full shadow-md ring-2 ring-gray-200" />
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900">
          {identityLoading ? (
            <span className="inline-block w-48 h-9 bg-gray-200 rounded animate-pulse" />
          ) : (
            <>Hi {(() => {
              const name = persona.name || '';
              const display = name.includes('@') ? name.split('@')[0] : name.split(' ')[0];
              return display || name;
            })()},</>
          )}
        </h1>
        <p className="text-xl text-gray-500">Search for data or ask a question in plain English.</p>

        <div className="max-w-2xl mx-auto mt-6">
          <form onSubmit={handleSearch} className="relative">
            <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-blue-500" />
            <input
              type="text"
              placeholder="Describe what you're looking for — e.g. fire incident data, budget reports..."
              className="w-full pl-12 pr-28 py-4 text-base border-2 rounded-xl focus:outline-none shadow-sm transition-colors"
              style={{ borderColor: searchQuery ? '#3B82F6' : '#E5E7EB' }}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            <span className="absolute right-14 top-1/2 -translate-y-1/2 text-[10px] font-semibold px-2 py-1 rounded-full bg-blue-50 text-blue-600">
              ✦ Ask AI
            </span>
            <button type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg text-white"
              style={{ backgroundColor: '#3B82F6' }}>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          {/* Suggestion chips — auto-generated from domains or admin-configured */}
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3 justify-center">
              {chips.map(({ label, q }) => (
                <button key={q} onClick={() => launchChip(q)}
                  className="text-xs text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-3 py-1 rounded-full transition-colors border border-blue-100">
                  {label}
                </button>
              ))}
            </div>
          )}
          <p className="text-xs text-gray-400 mt-2">Type anything — a keyword, a topic, or a full question. Use <button onClick={() => onNavigate('discover')} className="underline hover:text-gray-600">Discover</button> to browse and filter the full catalog.</p>
        </div>
      </div>

      {/* Featured */}
      <section>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-semibold text-gray-900">Featured</h2>
          <button
                onClick={() => onNavigate('discover')}
                className="text-sm font-medium flex items-center gap-1 hover:gap-2 transition-all"
            style={{ color: DataMarket_BLUE }}
          >
            View All <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {featuredProducts.length === 0 && [1,2,3].map(i => (
            <div key={i} className="bg-white rounded-xl border border-gray-100 p-5 animate-pulse">
              <div className="w-10 h-10 rounded-lg bg-gray-100 mb-3" />
              <div className="h-4 bg-gray-100 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-full mb-1" />
              <div className="h-3 bg-gray-100 rounded w-2/3" />
            </div>
          ))}
          {featuredProducts.map(product => {
            const Icon = typeIcons[product.type] || BarChart3
            const isLocked = false
            return (
              <button
                key={product.id || product.ref}
                onClick={() => onOpenProduct(product)}
                className={`text-left bg-white rounded-xl border p-5 hover:shadow-md transition-all group ${isLocked ? 'border-amber-200 hover:border-amber-300' : 'border-gray-200 hover:border-blue-300'}`}
              >
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: isLocked ? '#FEF3C7' : '#E8F0F7' }}>
                    <Icon className="h-5 w-5" style={{ color: isLocked ? '#D97706' : DataMarket_BLUE }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <h3 className="font-semibold text-gray-900 text-sm leading-tight group-hover:text-blue-700 transition-colors">{product.name}</h3>
                      {isLocked && <Lock className="h-3 w-3 text-amber-500 shrink-0" />}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {product.tags.map(tag => (
                        <span key={tag} className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${tagColors[tag] || 'bg-gray-100 text-gray-700'}`}>{tag}</span>
                      ))}
                      {isLocked && <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-amber-100 text-amber-700">Request Access</span>}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-gray-500 line-clamp-3 leading-relaxed">{product.description}</p>
                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
                  <span>{product.source}</span>
                  <span>↻ {product.refreshFrequency}</span>
                </div>
              </button>
            )
          })}
        </div>
      </section>

      {/* Recently Accessed */}
      <section>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recently Accessed</h2>
        {recentlyAccessed.length > 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            {recentlyAccessed.map((item, i) => {
              const Icon = typeIcons[item.type] || BarChart3
              return (
                <button key={i}
                  onClick={async () => {
                    try {
                      const res = await fetch('/api/portal/products?includeAll=true')
                      const products = await res.json()
                      const p = products.find(x => x.product_ref === item.ref)
                      if (p && onOpenProduct) {
                        onOpenProduct({
                          id: p.product_id, product_ref: p.product_ref, ref: p.product_ref,
                          name: p.display_name, description: p.description, type: p.type,
                          source: p.source_system, tags: parseTags(p.tags),
                          refreshFrequency: p.refresh_frequency, owner: p.owner_email,
                          classification: p.classification, uc_full_name: p.uc_full_name, ucFullName: p.uc_full_name,
                        })
                        return
                      }
                    } catch (_) {}
                    onNavigate('my-access')
                  }}
                  className="w-full flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors text-left group"
                >
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: '#E8F0F7' }}>
                    <Icon className="h-4 w-4" style={{ color: DataMarket_BLUE }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 group-hover:text-blue-700">{item.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {item.tags.slice(0, 3).map(t => (
                        <span key={t} className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${tagColors[t] || 'bg-gray-100 text-gray-600'}`}>{t}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-400 shrink-0">
                    <Clock className="h-3.5 w-3.5" />
                    {item.accessed}
                  </div>
                </button>
              )
            })}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 px-6 py-10 text-center">
            <p className="text-sm text-gray-500">No approved data products yet.</p>
            <button onClick={() => onNavigate('discover')}
              className="mt-3 text-sm font-medium flex items-center gap-1 mx-auto hover:gap-2 transition-all"
              style={{ color: DataMarket_BLUE }}>
              Browse the catalog <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </section>
    </div>
  )
}

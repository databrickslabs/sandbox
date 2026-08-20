import React, { useState, useEffect, useMemo } from 'react'
import { Search, SlidersHorizontal, BarChart3, FileText, Database, ChevronLeft, ChevronRight, RefreshCw, Layers, Bot, LayoutDashboard, AppWindow, Cpu, Upload, PlusCircle, Sparkles } from 'lucide-react'
import { usePersona } from '../context/PersonaContext'
import { useAppConfig } from '../context/AppConfigContext'
import { ImportUCModal } from '../components/ImportUCModal'

const DataMarket_BLUE = '#003865'

// Type options — the supported product types (these are a fixed taxonomy)
const ALL_TYPES = ['All', 'Dashboard', 'AI/BI Dashboard', 'Genie Space', 'Dataset', 'Report', 'App', 'ML Model', 'Power BI', 'Tableau']

// Static fallback — shown if Lakebase is unavailable
const staticProducts = [
  { id: 1, product_ref: 'DP-001', name: 'Budget Expenditure Report', category: 'Budget', type: 'Dashboard', source: 'ERP', description: 'Departmental budget allocations and year-to-date expenditures with variance analysis across all departments.', refreshFrequency: 'Daily', owner: 'james.park', lastUpdated: '02/11/2025', tags: ['Budget', 'ERP'] },
  { id: 2, product_ref: 'DP-002', name: 'Employee Metrics Dashboard', category: 'HRIS', type: 'Dashboard', source: 'HRIS', description: 'Headcount, turnover rates, overtime trends, and compensation metrics segmented by department and bargaining unit.', refreshFrequency: 'Weekly', owner: 'sarah.kim', lastUpdated: '02/11/2025', tags: ['HRIS', 'HR'] },
  { id: 3, product_ref: 'DP-003', name: 'Property Tax Report 2024', category: 'Property Tax', type: 'Report', source: 'Property Tax', description: 'Annual property tax assessments, collection rates, delinquency analysis, and revenue projections for FY2024.', refreshFrequency: 'Weekly', owner: 'robert.lee', lastUpdated: '02/11/2025', tags: ['Property Tax', 'Revenue'] },
  { id: 4, product_ref: 'DP-004', name: 'Census 2023 Dataset', category: 'Demographics', type: 'Dataset', source: 'Demographics', description: 'Your Organization population demographics by census tract including age, income, household size, and language.', refreshFrequency: 'Annual', owner: 'diana.torres', lastUpdated: '02/11/2025', tags: ['Demographics'] },
  { id: 5, product_ref: 'DP-005', name: 'Service Ticket Tracking Report', category: 'Accounting', type: 'Report', source: 'IT', description: 'Internal IT service requests, resolution times, SLA compliance, and department utilization metrics.', refreshFrequency: 'Daily', owner: 'michael.chang', lastUpdated: '02/11/2025', tags: ['IT'] },
  { id: 6, product_ref: 'DP-006', name: 'Essential Service Usage Report', category: 'Health Services', type: 'Report', source: 'Health Services', description: 'Utilization rates for essential services including health clinics, mental health centers, and social services.', refreshFrequency: 'Monthly', owner: 'angela.wright', lastUpdated: '02/11/2025', tags: ['Health Services'] },
  { id: 7, product_ref: 'DP-007', name: 'Payroll Dashboard', category: 'Payroll', type: 'Dashboard', source: 'HRIS', description: 'Organization-wide payroll expenditures, overtime costs, benefits allocation, and headcount by department.', refreshFrequency: 'Daily', owner: 'james.park', lastUpdated: '02/11/2025', tags: ['Payroll', 'HRIS'] },
  { id: 8, product_ref: 'DP-008', name: 'Property Tax Dashboard', category: 'Property Tax', type: 'Dashboard', source: 'Property Tax', description: 'Real-time property tax collection status, delinquency rates, and revenue tracking against annual targets.', refreshFrequency: 'Daily', owner: 'robert.lee', lastUpdated: '02/11/2025', tags: ['Property Tax'] },
  { id: 9, product_ref: 'DP-009', name: 'Population by Age 2020 Dataset', category: 'Demographics', type: 'Dataset', source: 'Demographics', description: 'Age-stratified population data from the 2020 Census, segmented by supervisorial district and community.', refreshFrequency: 'Annual', owner: 'diana.torres', lastUpdated: '02/11/2025', tags: ['Demographics'] },
  { id: 10, product_ref: 'DP-010', name: 'Enterprise Budget Analytics Dashboard', category: 'Budget', type: 'Dashboard', source: 'ERP', description: 'Comprehensive budget allocation, expenditure tracking, and variance analysis for FY2024-25.', refreshFrequency: 'Daily', owner: 'john.doe', lastUpdated: '02/11/2025', tags: ['Budget', 'Financial', 'ERP'] },
  { id: 11, product_ref: 'DP-011', name: 'Audit Finding Tracker', category: 'Audit', type: 'Report', source: 'Audit', description: 'Open and resolved audit findings by department, risk level, and remediation timeline.', refreshFrequency: 'Weekly', owner: 'david.nguyen', lastUpdated: '02/11/2025', tags: ['Audit'] },
  { id: 12, product_ref: 'DP-012', name: 'GIS Infrastructure Map', category: 'GIS', type: 'Dataset', source: 'GIS', description: 'Geospatial data for infrastructure including roads, utilities, facilities, and service boundaries.', refreshFrequency: 'Monthly', owner: 'john.doe', lastUpdated: '02/11/2025', tags: ['GIS'] },
]

// Normalize a Lakebase row to the shape the UI expects
function normalizeProduct(p) {
  const tags = Array.isArray(p.tags) ? p.tags
    : typeof p.tags === 'string' ? (p.tags.startsWith('[') ? JSON.parse(p.tags) : p.tags.split(',').map(t => t.trim()))
    : []
  return {
    id: p.product_id || p.id,
    product_ref: p.product_ref,
    name: p.display_name || p.name,
    category: p.domain || p.category || 'Other',
    type: p.type || 'Dashboard',
    source: p.source_system || p.source || '-',
    description: p.description,
    refreshFrequency: p.refresh_frequency || p.refreshFrequency || 'Daily',
    owner: p.owner_email || p.owner || '-',
    lastUpdated: p.updated_at ? new Date(p.updated_at).toLocaleDateString() : p.lastUpdated || '-',
    lastRefreshed: p.last_refreshed ? new Date(p.last_refreshed) : null,
    ucFullName: p.uc_full_name || p.ucFullName || null,
    productUrl: p.product_url || null,
    sourceType: p.source_type || 'Databricks',
    reportUrl: p.report_url || null,
    tags,
    status: p.status || 'Published'
  }
}

// Returns a freshness label + color class based on how recently data was refreshed
function freshnessLabel(lastRefreshed, freq) {
  if (!lastRefreshed) return null
  const ageMs = Date.now() - lastRefreshed.getTime()
  const ageDays = ageMs / 86400000
  const thresholds = { Daily: 1.5, Weekly: 8, Monthly: 32, Annual: 370 }
  const threshold = thresholds[freq] || 3
  if (ageDays <= threshold * 0.5) return { label: 'Fresh', color: 'text-emerald-600 bg-emerald-50' }
  if (ageDays <= threshold) return { label: 'Recent', color: 'text-blue-600 bg-blue-50' }
  if (ageDays <= threshold * 2) return { label: 'Stale', color: 'text-amber-600 bg-amber-50' }
  return { label: 'Outdated', color: 'text-red-600 bg-red-50' }
}

const tagColors = {
  Budget: 'bg-blue-100 text-blue-800', Financial: 'bg-green-100 text-green-800',
  'ERP System': 'bg-purple-100 text-purple-800', Payroll: 'bg-orange-100 text-orange-800',
  HR: 'bg-pink-100 text-pink-800', 'Property Tax': 'bg-amber-100 text-amber-800',
  Revenue: 'bg-teal-100 text-teal-800', HRIS: 'bg-indigo-100 text-indigo-800',
  Demographics: 'bg-rose-100 text-rose-800', Audit: 'bg-red-100 text-red-800',
  IT: 'bg-gray-100 text-gray-800', GIS: 'bg-cyan-100 text-cyan-800',
  'Health Services': 'bg-emerald-100 text-emerald-800',
  'Power BI': 'bg-yellow-100 text-yellow-800',
  'Public Safety': 'bg-slate-100 text-slate-800',
}

const typeIcons = {
  Dashboard:         BarChart3,
  'AI/BI Dashboard': LayoutDashboard,
  'Genie Space':     Bot,
  Dataset:           Database,
  Report:            FileText,
  App:               AppWindow,
  'ML Model':        Cpu,
  'Power BI':        BarChart3,
  'Tableau':         BarChart3,
  Source:            Layers,
}
const PAGE_SIZE = 6

export function DataMarketCatalogPage({ onOpenProduct, onNavigate, initialSearch = '' }) {
  const { currentPersona, isAdmin } = usePersona()
  const { demoMode } = useAppConfig()
  const [search, setSearch] = useState(initialSearch)
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [selectedType, setSelectedType] = useState('All')
  const [selectedSource, setSelectedSource] = useState('All')
  const [selectedTag, setSelectedTag] = useState('All')
  const [sortBy, setSortBy] = useState('Most Recent')
  const [page, setPage] = useState(1)
  const [allProducts, setAllProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showImport, setShowImport] = useState(false)
  const [lakebaseEmpty, setLakebaseEmpty] = useState(false)

  // Derive categories dynamically from loaded products so filters always match real data
  const categories = useMemo(() => {
    const cats = [...new Set(allProducts.map(p => p.category).filter(Boolean))].sort()
    return ['All', ...cats]
  }, [allProducts])

  // Only show type options that actually exist in the current product set
  const types = useMemo(() => {
    const used = new Set(allProducts.map(p => p.type).filter(Boolean))
    return ['All', ...ALL_TYPES.slice(1).filter(t => used.has(t))]
  }, [allProducts])

  // Derive source options from real data
  const sourceTypes = useMemo(() => {
    const sources = [...new Set(allProducts.map(p => p.sourceType || p.source_system || '').filter(Boolean))].sort()
    return ['All', ...sources]
  }, [allProducts])

  // Derive tag options dynamically from all product tags
  const allTags = useMemo(() => {
    const tagSet = new Set()
    allProducts.forEach(p => (p.tags || []).forEach(t => t && t !== 'UC Import' && tagSet.add(t)))
    return ['All', ...Array.from(tagSet).sort()]
  }, [allProducts])

  const loadProducts = () => {
    fetch(`/api/portal/products${isAdmin ? '?includeAll=true' : ''}`)
      .then(r => r.json())
      .then(rows => {
        if (Array.isArray(rows) && rows.length > 0) {
          setAllProducts(rows.map(normalizeProduct))
          setLakebaseEmpty(false)
          setSelectedCategory('All')
          setSelectedType('All')
        } else if (Array.isArray(rows) && rows.length === 0) {
          setAllProducts([])
          setLakebaseEmpty(true)
        }
      })
      .catch(() => {
        // In demo mode fall back to static products so demos work offline
        if (demoMode) setAllProducts(staticProducts)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadProducts() }, [currentPersona])

  const filtered = allProducts.filter(p => {
    const words = search.toLowerCase().split(/\s+/).filter(Boolean)
    const matchesSearch = !search || words.every(w =>
      p.name.toLowerCase().includes(w) ||
      p.description.toLowerCase().includes(w) ||
      p.tags.some(t => t.toLowerCase().includes(w)) ||
      p.category.toLowerCase().includes(w) ||
      p.source.toLowerCase().includes(w)
    )
    const matchesCat = selectedCategory === 'All' || p.category === selectedCategory
    const matchesType = selectedType === 'All' || p.type === selectedType
    const matchesSource = selectedSource === 'All' || p.sourceType === selectedSource
    const matchesTag    = selectedTag === 'All' || (p.tags || []).includes(selectedTag)
    return matchesSearch && matchesCat && matchesType && matchesSource && matchesTag
  })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <>
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Catalog</h1>
          <p className="text-sm text-gray-500 mt-1 flex items-center gap-2">
            {loading && <RefreshCw className="h-3 w-3 animate-spin" />}
            {filtered.length} data products available
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isAdmin && (
            <button
              onClick={() => setShowImport(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white"
              style={{ backgroundColor: '#003865' }}
            >
              <Upload className="h-3.5 w-3.5" />
              Import from UC
            </button>
          )}
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>Sort By</span>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none"
            >
              <option>Most Recent</option>
              <option>Name A-Z</option>
              <option>Name Z-A</option>
            </select>
          </div>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Filters */}
        <aside className="w-52 shrink-0 hidden md:block">
          {/* Search */}
          <div className="relative mb-5">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search"
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
            />
          </div>

          {/* Filter By Category */}
          <div className="mb-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <SlidersHorizontal className="h-3 w-3" /> Filter By
            </p>
            <div className="space-y-0.5">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => { setSelectedCategory(cat); setPage(1) }}
                  className={`w-full text-left px-3 py-1.5 rounded text-sm transition-colors ${
                    selectedCategory === cat
                      ? 'font-medium text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                  style={selectedCategory === cat ? { backgroundColor: DataMarket_BLUE } : {}}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Type Filter */}
          <div className="mb-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Type</p>
            <div className="flex flex-wrap gap-1.5">
              {types.map(t => (
                <button
                  key={t}
                  onClick={() => { setSelectedType(t); setPage(1) }}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                    selectedType === t ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  style={selectedType === t ? { backgroundColor: DataMarket_BLUE } : {}}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Source Filter */}
          <div className="mb-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers className="h-3 w-3" /> Source
            </p>
            <div className="flex flex-wrap gap-1.5">
              {sourceTypes.map(s => (
                <button
                  key={s}
                  onClick={() => { setSelectedSource(s); setPage(1) }}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors flex items-center gap-1 ${
                    selectedSource === s ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  style={selectedSource === s ? { backgroundColor: DataMarket_BLUE } : {}}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Tags Filter — only show if real tags exist beyond 'UC Import' */}
          {allTags.length > 1 && (
            <div className="mb-5">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Tags</p>
              <div className="flex flex-wrap gap-1.5">
                {allTags.map(tag => (
                  <button
                    key={tag}
                    onClick={() => { setSelectedTag(tag); setPage(1) }}
                    className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                      selectedTag === tag ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                    style={selectedTag === tag ? { backgroundColor: DataMarket_BLUE } : {}}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* Main Grid */}
        <div className="flex-1 min-w-0">
          {/* Mobile search */}
          <div className="relative mb-4 md:hidden">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search"
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
            />
          </div>

          {/* First-run onboarding banner — shown only when catalog is empty */}
          {lakebaseEmpty && isAdmin && (
            <div className="rounded-2xl border-2 border-dashed border-blue-200 bg-blue-50/40 p-10 mb-6 text-center">
              <div className="w-16 h-16 rounded-full bg-white shadow-sm flex items-center justify-center mx-auto mb-4">
                <Sparkles className="h-8 w-8 text-blue-500" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Welcome to DataMarket</h2>
              <p className="text-sm text-gray-500 max-w-md mx-auto mb-6">
                Your data catalog is empty. Get started by importing existing tables from Unity Catalog,
                or register a new data product manually.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={() => setShowImport(true)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white shadow"
                  style={{ backgroundColor: '#003865' }}
                >
                  <Upload className="h-4 w-4" />
                  Import from Unity Catalog
                </button>
                {onNavigate && (
                  <button
                    onClick={() => onNavigate('register')}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-gray-700 bg-white border border-gray-200 hover:bg-gray-50"
                  >
                    <PlusCircle className="h-4 w-4" />
                    Register a Product
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="space-y-3">
            {paged.length === 0 && !lakebaseEmpty && (
              <div className="text-center py-16 text-gray-400">
                <Database className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No data products match your filters.</p>
              </div>
            )}
            {paged.map(product => {
              const Icon = typeIcons[product.type] || BarChart3
              return (
                <button
                  key={product.id}
                  onClick={() => onOpenProduct(product)}
                  className="w-full text-left bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-md transition-all group"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: '#E8F0F7' }}>
                      <Icon className="h-5 w-5" style={{ color: DataMarket_BLUE }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <h3 className="font-semibold text-gray-900 text-sm group-hover:text-blue-700 transition-colors">{product.name}</h3>
                        <div className="flex flex-wrap gap-1 shrink-0">
                          {product.tags.map(tag => (
                            <span key={tag} className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${tagColors[tag] || 'bg-gray-100 text-gray-700'}`}>{tag}</span>
                          ))}
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{product.description}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400 flex-wrap">
                        <span>↻ {product.refreshFrequency}</span>
                        <span>Owner: {product.owner}</span>
                        <span>Updated: {product.lastUpdated}</span>
                        {product.sourceType === 'Power BI' && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">
                            📊 Power BI
                          </span>
                        )}
                        {(() => {
                          const f = freshnessLabel(product.lastRefreshed, product.refreshFrequency)
                          return f ? (
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${f.color}`}>
                              ● {f.label}
                            </span>
                          ) : null
                        })()}
                      </div>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
                <button
                  key={n}
                  onClick={() => setPage(n)}
                  className={`w-8 h-8 rounded text-sm font-medium transition-colors ${page === n ? 'text-white' : 'border border-gray-200 text-gray-600 hover:bg-gray-50'}`}
                  style={page === n ? { backgroundColor: DataMarket_BLUE } : {}}
                >
                  {n}
                </button>
              ))}
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>

    {showImport && (
      <ImportUCModal
        onClose={() => setShowImport(false)}
        onImported={() => { setShowImport(false); loadProducts() }}
      />
    )}
    </>
  )
}

import React, { useState } from 'react'
import { Search, Edit3, Check, X, ExternalLink, Link2, Database, AlertTriangle, CheckCircle2, Trash2 } from 'lucide-react'
import { statusConfig } from './adminConstants'

// ─── Inline Edit Row for Product ───────────────────────────────────────────────
function ProductEditRow({ product, onSave, onCancel }) {
  const [form, setForm] = useState({
    uc_full_name: product.uc_full_name || '',
    source_type: product.source_type || 'Databricks',
    refresh_frequency: product.refresh_frequency || 'Daily',
    domain: product.domain || '',
  })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await fetch(`/api/portal/products/${product.product_ref}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })
      onSave()
    } catch (e) { console.error(e) }
    setSaving(false)
  }

  return (
    <tr className="bg-blue-50/50 border-b border-blue-200">
      <td className="py-2 px-4 text-xs font-mono text-gray-500">{product.product_ref}</td>
      <td className="py-2 px-4 text-xs font-medium text-gray-900">{product.display_name}</td>
      <td className="py-2 px-4">
        <input value={form.domain} onChange={e => setForm({ ...form, domain: e.target.value })}
          className="w-full px-2 py-1 border border-blue-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-400" />
      </td>
      <td className="py-2 px-4">
        <select value={form.source_type} onChange={e => setForm({ ...form, source_type: e.target.value })}
          className="px-2 py-1 border border-blue-200 rounded text-xs focus:outline-none">
          <option>Databricks</option>
          <option>Power BI</option>
        </select>
      </td>
      <td className="py-2 px-4">
        <input value={form.uc_full_name} onChange={e => setForm({ ...form, uc_full_name: e.target.value })}
          placeholder="catalog.schema.table"
          className="w-full px-2 py-1 border border-blue-200 rounded text-xs font-mono focus:outline-none focus:ring-1 focus:ring-blue-400" />
      </td>
      <td className="py-2 px-4">
        <select value={form.refresh_frequency} onChange={e => setForm({ ...form, refresh_frequency: e.target.value })}
          className="px-2 py-1 border border-blue-200 rounded text-xs focus:outline-none">
          <option>Daily</option>
          <option>Weekly</option>
          <option>Monthly</option>
          <option>Annual</option>
        </select>
      </td>
      <td className="py-2 px-4">
        <div className="flex gap-1">
          <button onClick={handleSave} disabled={saving} className="p-1 rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200"><Check className="h-3.5 w-3.5" /></button>
          <button onClick={onCancel} className="p-1 rounded bg-gray-100 text-gray-500 hover:bg-gray-200"><X className="h-3.5 w-3.5" /></button>
        </div>
      </td>
    </tr>
  )
}

export function AdminProductsTab({
  allProducts, filteredProducts, loadingProducts, productsError,
  syncResult, editingRef, setEditingRef, loadAllProducts,
  search, setSearch, onNavigate, fromRequests, persona, activeTab,
}) {
  return (
    <>
      {/* Sync result toast */}
      {syncResult && !syncResult.error && (
        <div className="mb-3 px-4 py-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Sync complete — {syncResult.synced} refreshed, {syncResult.unavailable} marked unavailable
        </div>
      )}
      {syncResult?.error && (
        <div className="mb-3 px-4 py-2.5 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{syncResult.error}</div>
      )}
      {/* Draft products banner */}
      {allProducts.filter(p => p.status === 'Draft').length > 0 && (
        <div className="mb-3 px-4 py-2.5 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            <strong>{allProducts.filter(p => p.status === 'Draft').length} draft product{allProducts.filter(p => p.status === 'Draft').length > 1 ? 's' : ''}</strong> auto-discovered from UC — review below and Publish or Delete.
          </span>
        </div>
      )}
      <div className="relative mb-4 max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input type="text" placeholder="Search products" value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>

      {activeTab === 'Data Products' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Ref</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Name</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Domain</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Source</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">UC Table</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Frequency</th>
                  <th className="text-center py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Status</th>
                  <th className="text-center py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide w-20">Edit</th>
                </tr>
              </thead>
              <tbody>
                {loadingProducts && (
                  <tr><td colSpan={8} className="py-12 text-center text-gray-400 text-sm">Loading products...</td></tr>
                )}
                {productsError && !loadingProducts && (
                  <tr><td colSpan={8} className="py-6 text-center text-red-500 text-sm">Error: {productsError}</td></tr>
                )}
                {filteredProducts.map(p => {
                  if (editingRef === p.product_ref) {
                    return <ProductEditRow key={p.product_ref} product={p} onSave={() => { setEditingRef(null); loadAllProducts() }} onCancel={() => setEditingRef(null)} />
                  }
                  const st = p.source_type || 'Databricks'
                  const status = p.status || 'Published'
                  return (
                    <tr key={p.product_ref} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="py-3 px-4 text-xs font-mono text-gray-400">{p.product_ref}</td>
                      <td className="py-3 px-4">
                        <span className="font-medium text-gray-900 text-xs">{p.display_name}</span>
                      </td>
                      <td className="py-3 px-4 text-xs text-gray-600">{p.domain || '-'}</td>
                      <td className="py-3 px-4">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                          st === 'Power BI' ? 'bg-yellow-50 text-yellow-700 border border-yellow-200' : 'bg-blue-50 text-blue-700 border border-blue-200'
                        }`}>
                          {st === 'Power BI' ? '📊' : '⚡'} {st}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {p.uc_full_name ? (
                          <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded flex items-center gap-1 w-fit">
                            <Link2 className="h-2.5 w-2.5" /> {p.uc_full_name.split('.').pop()}
                          </span>
                        ) : (
                          <span className="text-[10px] text-gray-400">Not linked</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs text-gray-500">{p.refresh_frequency || '-'}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusConfig[status] || 'bg-gray-100 text-gray-700'}`}>
                          {status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => setEditingRef(p.product_ref)} title="Quick edit" className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700">
                            <Edit3 className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => onNavigate('register', { editProduct: p })} title="Full edit" className="p-1 rounded hover:bg-blue-100 text-blue-400 hover:text-blue-700">
                            <ExternalLink className="h-3.5 w-3.5" />
                          </button>
                          <button
                            title="Delete product"
                            className="p-1 rounded hover:bg-red-50 text-gray-300 hover:text-red-500 transition-colors"
                            onClick={async () => {
                              if (!window.confirm(`Delete "${p.display_name}"? This cannot be undone.`)) return
                              try {
                                const r = await fetch(`/api/portal/products/${p.product_ref}`, { method: 'DELETE' })
                                if (!r.ok) throw new Error(await r.text())
                                loadAllProducts()
                              } catch (e) { alert('Delete failed: ' + e.message) }
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {!loadingProducts && filteredProducts.length === 0 && (
            <div className="py-16 text-center text-gray-400">
              <Database className="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No products found.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'Requests' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Product</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Requester</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Reason</th>
                  <th className="text-center py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {fromRequests.length === 0 && (
                  <tr><td colSpan={4} className="py-12 text-center text-gray-400 text-sm">No requests yet.</td></tr>
                )}
                {fromRequests.map(r => (
                  <tr key={r.requestId || r.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 text-xs font-medium text-gray-900">{r.name}</td>
                    <td className="py-3 px-4 text-xs text-gray-500">{persona.email}</td>
                    <td className="py-3 px-4 text-xs text-gray-500 max-w-xs truncate">{r.reason || '-'}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusConfig[r.status] || 'bg-gray-100 text-gray-700'}`}>{r.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

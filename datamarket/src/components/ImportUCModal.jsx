import React, { useState, useEffect, useRef } from 'react'
import { Upload, X, Check, Database, FolderOpen, Folder, ChevronRight, ChevronDown, Loader2, Search, Table2, ShieldAlert, Copy, ExternalLink, CheckCircle2 } from 'lucide-react'

const BLUE = '#003865'

// ─── Indeterminate checkbox ────────────────────────────────────────────────────
function Checkbox({ checked, indeterminate, disabled, onChange, className = '' }) {
  const ref = useRef(null)
  useEffect(() => { if (ref.current) ref.current.indeterminate = !!indeterminate }, [indeterminate])
  return (
    <input ref={ref} type="checkbox" checked={checked} disabled={disabled}
      onChange={onChange} className={`cursor-pointer shrink-0 ${className}`} />
  )
}

// ─── Main modal ───────────────────────────────────────────────────────────────
export function ImportUCModal({ onClose, onImported }) {
  const [catalogs, setCatalogs]   = useState([])
  const [schemas,  setSchemas]    = useState({})
  const [tables,   setTables]     = useState({})
  const [tablesMeta, setTablesMeta] = useState({}) // { [catName.schName]: { needsGrant, grantSql, sqlEditorUrl } }
  const [selected, setSelected]   = useState(new Set())
  const [search,   setSearch]     = useState('')
  const [initLoad, setInitLoad]   = useState(true)
  const [importing, setImporting] = useState(false)
  const [result,   setResult]     = useState(null)
  const [initError, setInitError] = useState(null)
  const [copiedKey, setCopiedKey] = useState(null)

  // Load catalog list on mount
  useEffect(() => {
    fetch('/api/portal/admin/uc-catalogs')
      .then(r => r.json())
      .then(d => {
        if (d.error) throw new Error(d.error)
        setCatalogs((d.catalogs || []).map(c => ({
          name: c.name, comment: c.comment,
          expanded: false, loading: false, schemasLoaded: false,
        })))
      })
      .catch(e => setInitError(e.message))
      .finally(() => setInitLoad(false))
  }, [])

  // ── Catalog toggle ───────────────────────────────────────────────────────────
  const toggleCatalog = async (name) => {
    const cat = catalogs.find(c => c.name === name)
    if (!cat) return
    if (!cat.schemasLoaded && !cat.expanded) {
      setCatalogs(p => p.map(c => c.name === name ? { ...c, loading: true } : c))
      try {
        const d = await fetch(`/api/portal/admin/uc-schemas?catalog=${encodeURIComponent(name)}`).then(r => r.json())
        if (d.error) throw new Error(d.error)
        setSchemas(p => ({
          ...p,
          [name]: (d.schemas || []).map(s => ({
            name: s.name, expanded: false, loading: false, tablesLoaded: false,
          }))
        }))
        setCatalogs(p => p.map(c => c.name === name ? { ...c, schemasLoaded: true, loading: false, expanded: true } : c))
      } catch {
        setCatalogs(p => p.map(c => c.name === name ? { ...c, loading: false } : c))
      }
    } else {
      setCatalogs(p => p.map(c => c.name === name ? { ...c, expanded: !c.expanded } : c))
    }
  }

  // ── Schema toggle ────────────────────────────────────────────────────────────
  const toggleSchema = async (catName, schName) => {
    const sch = (schemas[catName] || []).find(s => s.name === schName)
    if (!sch) return
    const key = `${catName}.${schName}`
    if (!sch.tablesLoaded && !sch.expanded) {
      setSchemas(p => ({ ...p, [catName]: p[catName].map(s => s.name === schName ? { ...s, loading: true } : s) }))
      try {
        const d = await fetch(
          `/api/portal/admin/uc-tables-browse?catalog=${encodeURIComponent(catName)}&schema=${encodeURIComponent(schName)}`
        ).then(r => r.json())
        if (d.error) throw new Error(d.error)
        setTables(p => ({ ...p, [key]: d.tables || [] }))
        if (d.needsGrant) {
          setTablesMeta(p => ({ ...p, [key]: { needsGrant: true, grantSql: d.grantSql, sqlEditorUrl: d.sqlEditorUrl } }))
        }
        setSchemas(p => ({
          ...p,
          [catName]: p[catName].map(s => s.name === schName ? { ...s, tablesLoaded: true, loading: false, expanded: true } : s)
        }))
      } catch {
        setSchemas(p => ({ ...p, [catName]: p[catName].map(s => s.name === schName ? { ...s, loading: false } : s) }))
      }
    } else {
      setSchemas(p => ({ ...p, [catName]: p[catName].map(s => s.name === schName ? { ...s, expanded: !s.expanded } : s) }))
    }
  }

  // ── Selection helpers ────────────────────────────────────────────────────────
  const toggleTable = (fullName) =>
    setSelected(p => { const n = new Set(p); n.has(fullName) ? n.delete(fullName) : n.add(fullName); return n })

  const schemaSelectable = (catName, schName) =>
    (tables[`${catName}.${schName}`] || []).filter(t => !t.registered)

  const schemaCheckState = (catName, schName) => {
    const ts = schemaSelectable(catName, schName)
    if (!ts.length) return 'none'
    const sel = ts.filter(t => selected.has(t.full_name)).length
    return sel === 0 ? 'unchecked' : sel === ts.length ? 'checked' : 'indeterminate'
  }

  const toggleSchemaSelect = (catName, schName) => {
    const ts = schemaSelectable(catName, schName)
    const all = ts.every(t => selected.has(t.full_name))
    setSelected(p => { const n = new Set(p); ts.forEach(t => all ? n.delete(t.full_name) : n.add(t.full_name)); return n })
  }

  const catalogSelectable = (catName) =>
    (schemas[catName] || []).flatMap(s => schemaSelectable(catName, s.name))

  const catalogCheckState = (catName) => {
    const ts = catalogSelectable(catName)
    if (!ts.length) return 'none'
    const sel = ts.filter(t => selected.has(t.full_name)).length
    return sel === 0 ? 'unchecked' : sel === ts.length ? 'checked' : 'indeterminate'
  }

  const toggleCatalogSelect = (catName) => {
    const ts = catalogSelectable(catName)
    const all = ts.every(t => selected.has(t.full_name))
    setSelected(p => { const n = new Set(p); ts.forEach(t => all ? n.delete(t.full_name) : n.add(t.full_name)); return n })
  }

  // ── Search filter ─────────────────────────────────────────────────────────────
  const matches = (s) => !search || s.toLowerCase().includes(search.toLowerCase())

  // ── Import ────────────────────────────────────────────────────────────────────
  const handleImport = async () => {
    setImporting(true)
    try {
      const allTables = Object.values(tables).flat()
      const toImport = allTables.filter(t => selected.has(t.full_name))
      const r = await fetch('/api/portal/admin/import-uc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables: toImport }),
      })
      const data = await r.json()
      setResult(data)
      if (data.imported > 0) onImported()
    } catch (e) {
      setResult({ error: e.message })
    }
    setImporting(false)
  }

  // ── Result screen ─────────────────────────────────────────────────────────────
  if (result) return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-4">
          <Check className="h-8 w-8 text-emerald-600" />
        </div>
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          {result.error ? 'Import failed' : `${result.imported} Table${result.imported !== 1 ? 's' : ''} Imported`}
        </h3>
        <p className="text-sm text-gray-500 mb-6">
          {result.error || 'Data products created from Unity Catalog and published to the catalog.'}
        </p>
        <button onClick={onClose} className="w-full py-2.5 rounded-lg text-white font-medium" style={{ backgroundColor: BLUE }}>
          Done
        </button>
      </div>
    </div>
  )

  // ── Main modal ────────────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-2xl shadow-2xl flex flex-col" style={{ maxHeight: '82vh' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-100 shrink-0">
          <div>
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Upload className="h-4 w-4" style={{ color: BLUE }} />
              Import from Unity Catalog
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Browse catalogs → schemas → tables. Select tables to register as data products.
            </p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 pt-3 pb-2 shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
            <input
              type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Filter loaded tables by name…"
              className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-100 bg-gray-50"
            />
          </div>
        </div>

        {/* Tree body */}
        <div className="flex-1 overflow-y-auto px-3 pb-3">
          {initLoad ? (
            <div className="py-16 flex flex-col items-center gap-2 text-gray-400 text-sm">
              <Loader2 className="h-5 w-5 animate-spin" />
              Loading catalogs…
            </div>
          ) : initError ? (
            <div className="py-12 text-center text-sm">
              <Database className="h-8 w-8 mx-auto mb-2 text-red-300" />
              <p className="text-red-500 font-medium">Could not load Unity Catalog</p>
              <p className="text-gray-400 text-xs mt-1 max-w-xs mx-auto">{initError}</p>
              <p className="text-gray-400 text-xs mt-2">Ensure <code className="bg-gray-100 px-1 rounded">DATABRICKS_TOKEN</code> is set in app.yaml</p>
            </div>
          ) : catalogs.length === 0 ? (
            <div className="py-16 text-center text-gray-400 text-sm">
              <Database className="h-8 w-8 mx-auto mb-2 opacity-30" />
              No catalogs found
            </div>
          ) : (
            <div className="select-none text-sm mt-1 space-y-0.5">
              {catalogs.map(cat => {
                const catState = catalogCheckState(cat.name)
                return (
                  <div key={cat.name}>
                    {/* ── Catalog row ── */}
                    <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-gray-50 group">
                      <button onClick={() => toggleCatalog(cat.name)} className="flex items-center gap-1.5 flex-1 min-w-0 text-left">
                        {cat.loading
                          ? <Loader2 className="h-3.5 w-3.5 text-gray-400 animate-spin shrink-0" />
                          : cat.expanded
                            ? <ChevronDown className="h-3.5 w-3.5 text-gray-500 shrink-0" />
                            : <ChevronRight className="h-3.5 w-3.5 text-gray-500 shrink-0" />
                        }
                        <Database className="h-4 w-4 text-gray-500 shrink-0" />
                        <span className="font-semibold text-gray-800 truncate">{cat.name}</span>
                        {cat.schemasLoaded && (
                          <span className="text-xs text-gray-400 shrink-0">
                            ({(schemas[cat.name] || []).length})
                          </span>
                        )}
                      </button>
                      {catState !== 'none' && (
                        <Checkbox
                          checked={catState === 'checked'}
                          indeterminate={catState === 'indeterminate'}
                          onChange={() => toggleCatalogSelect(cat.name)}
                        />
                      )}
                    </div>

                    {/* ── Schemas ── */}
                    {cat.expanded && (
                      <div className="ml-4 pl-3 border-l-2 border-gray-100 space-y-0.5 mt-0.5 mb-1">
                        {(schemas[cat.name] || []).length === 0 && !cat.loading && (
                          <div className="py-1 px-2 text-xs text-gray-400 italic">No schemas</div>
                        )}
                        {(schemas[cat.name] || [])
                          .filter(sch => {
                            if (!search) return true
                            const key = `${cat.name}.${sch.name}`
                            return matches(sch.name) || (tables[key] || []).some(t => matches(t.table_name))
                          })
                          .map(sch => {
                            const schKey = `${cat.name}.${sch.name}`
                            const schTables = tables[schKey] || []
                            const unregistered = schTables.filter(t => !t.registered)
                            const schState = schemaCheckState(cat.name, sch.name)
                            const visibleTables = search ? schTables.filter(t => matches(t.table_name)) : schTables

                            return (
                              <div key={sch.name}>
                                {/* ── Schema row ── */}
                                <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-gray-50">
                                  <button onClick={() => toggleSchema(cat.name, sch.name)} className="flex items-center gap-1.5 flex-1 min-w-0 text-left">
                                    {sch.loading
                                      ? <Loader2 className="h-3 w-3 text-gray-400 animate-spin shrink-0" />
                                      : sch.expanded
                                        ? <ChevronDown className="h-3 w-3 text-gray-500 shrink-0" />
                                        : <ChevronRight className="h-3 w-3 text-gray-500 shrink-0" />
                                    }
                                    {sch.expanded
                                      ? <FolderOpen className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                                      : <Folder className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                                    }
                                    <span className="text-gray-700 truncate">{sch.name}</span>
                                    {sch.tablesLoaded && (
                                      <span className="text-xs text-gray-400 shrink-0">
                                        ({unregistered.length} available)
                                      </span>
                                    )}
                                  </button>
                                  {schState !== 'none' && (
                                    <Checkbox
                                      checked={schState === 'checked'}
                                      indeterminate={schState === 'indeterminate'}
                                      onChange={() => toggleSchemaSelect(cat.name, sch.name)}
                                    />
                                  )}
                                </div>

                                {/* ── Tables ── */}
                                {sch.expanded && (
                                  <div className="ml-4 pl-3 border-l-2 border-gray-100 space-y-0.5 mt-0.5 mb-1">
                                    {schTables.length === 0 && !sch.loading && (() => {
                                      const meta = tablesMeta[`${cat.name}.${sch.name}`]
                                      if (meta?.needsGrant) {
                                        return (
                                          <div className="py-2 px-2 space-y-2">
                                            <div className="flex items-start gap-1.5 text-xs text-amber-700">
                                              <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-500" />
                                              <span>App service principal needs <code className="bg-amber-100 px-1 rounded font-mono">SELECT ON CATALOG</code> to see tables here. Run once — covers all schemas.</span>
                                            </div>
                                            <div className="bg-gray-950 rounded-lg px-3 py-2 flex items-center gap-2">
                                              <code className="text-xs text-emerald-300 font-mono flex-1 break-all">{meta.grantSql}</code>
                                              <button
                                                onClick={() => {
                                                  navigator.clipboard.writeText(meta.grantSql)
                                                  setCopiedKey(`${cat.name}.${sch.name}`)
                                                  setTimeout(() => setCopiedKey(null), 2000)
                                                }}
                                                className="shrink-0 text-gray-500 hover:text-gray-300"
                                                title="Copy SQL"
                                              >
                                                {copiedKey === `${cat.name}.${sch.name}`
                                                  ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                                                  : <Copy className="h-3.5 w-3.5" />}
                                              </button>
                                            </div>
                                            {meta.sqlEditorUrl && (
                                              <a href={meta.sqlEditorUrl} target="_blank" rel="noopener noreferrer"
                                                className="flex items-center gap-1 text-xs text-blue-600 hover:underline">
                                                <ExternalLink className="h-3 w-3" /> Open SQL Editor
                                              </a>
                                            )}
                                            <button
                                              onClick={() => {
                                                setTablesMeta(p => { const n = {...p}; delete n[`${cat.name}.${sch.name}`]; return n })
                                                setSchemas(p => ({ ...p, [cat.name]: p[cat.name].map(s => s.name === sch.name ? { ...s, tablesLoaded: false, expanded: false } : s) }))
                                              }}
                                              className="text-xs text-gray-400 hover:text-gray-600"
                                            >
                                              Re-check after running SQL
                                            </button>
                                          </div>
                                        )
                                      }
                                      return <div className="py-1 px-2 text-xs text-gray-400 italic">No tables</div>
                                    })()}
                                    {visibleTables.map(t => (
                                      <label
                                        key={t.full_name}
                                        className={`flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${
                                          t.registered
                                            ? 'opacity-40 cursor-not-allowed'
                                            : selected.has(t.full_name)
                                              ? 'bg-blue-50'
                                              : 'hover:bg-gray-50'
                                        }`}
                                      >
                                        <input
                                          type="checkbox"
                                          checked={selected.has(t.full_name)}
                                          disabled={t.registered}
                                          onChange={() => !t.registered && toggleTable(t.full_name)}
                                          className="shrink-0"
                                        />
                                        <Table2 className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                                        <span className={`truncate text-xs ${
                                          selected.has(t.full_name) ? 'text-blue-700 font-medium' : 'text-gray-700'
                                        }`}>
                                          {t.table_name}
                                        </span>
                                        <span className="ml-auto shrink-0">
                                          {t.registered
                                            ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600">registered</span>
                                            : t.table_type && t.table_type !== 'MANAGED'
                                              ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{t.table_type}</span>
                                              : null
                                          }
                                        </span>
                                      </label>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 pb-5 pt-3 flex gap-3 border-t border-gray-100 shrink-0 items-center">
          <span className="text-xs text-gray-400 mr-auto">
            {selected.size > 0 ? `${selected.size} table${selected.size !== 1 ? 's' : ''} selected` : 'Expand catalogs to browse tables'}
          </span>
          <button onClick={onClose} className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={selected.size === 0 || importing}
            className="px-5 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40 flex items-center gap-2"
            style={{ backgroundColor: BLUE }}
          >
            {importing
              ? <><Loader2 className="h-4 w-4 animate-spin" /> Importing…</>
              : `Import ${selected.size || ''} Table${selected.size !== 1 ? 's' : ''}`
            }
          </button>
        </div>
      </div>
    </div>
  )
}

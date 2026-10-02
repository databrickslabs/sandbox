import React, { useState, useEffect, useCallback } from 'react'
import { Database, Warehouse, CheckCircle2, ArrowRight, X, Sparkles, Package,
         ShieldCheck, AlertTriangle, RefreshCw, Copy, ExternalLink } from 'lucide-react'
import { useAppConfig } from '@/context/AppConfigContext'
import { ImportUCModal } from '@/components/ImportUCModal'

const BLUE = '#003865'

const STEPS = [
  { id: 'warehouse',  short: 'SQL Warehouse',    icon: Warehouse    },
  { id: 'catalogs',   short: 'Catalog access',   icon: ShieldCheck  },
  { id: 'import',     short: 'Import data',      icon: Package      },
  { id: 'done',       short: 'You\'re live',     icon: CheckCircle2 },
]

export function FirstRunWizard({ onDismiss }) {
  const { appName, refreshConfig } = useAppConfig()
  const [step, setStep]               = useState(0)

  // Step 0 — Warehouse
  const [warehouseId, setWarehouseId]       = useState('')
  const [warehousePreFilled, setPreFilled]  = useState(false)
  const [saving, setSaving]                 = useState(false)
  const [saveError, setSaveError]           = useState('')

  // Step 1 — Catalog access
  const [accessCheck, setAccessCheck]   = useState(null)
  const [accessLoading, setAccessLoading] = useState(false)
  const [granting, setGranting]         = useState(false)
  const [grantResults, setGrantResults] = useState(null)   // null | { allSucceeded, results[] }
  const [copied, setCopied]             = useState(false)

  // Step 2 — Import
  const [showImport, setShowImport] = useState(false)
  const [imported, setImported]     = useState(false)

  // Pre-fill warehouse ID from settings
  useEffect(() => {
    fetch('/api/portal/settings')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        const id = data?.sql_warehouse_id || ''
        if (id) { setWarehouseId(id); setPreFilled(true) }
      })
      .catch(() => {})
  }, [])

  // Load access check whenever we enter step 1
  const runAccessCheck = useCallback(async () => {
    setAccessLoading(true)
    try {
      const d = await fetch('/api/portal/admin/uc-access-check').then(r => r.json())
      setAccessCheck(d)
    } catch (e) {
      setAccessCheck({ error: e.message })
    } finally {
      setAccessLoading(false)
    }
  }, [])

  useEffect(() => {
    if (step === 1) { setGrantResults(null); runAccessCheck() }
  }, [step, runAccessCheck])

  const runGrants = useCallback(async () => {
    setGranting(true)
    setGrantResults(null)
    try {
      // Only grant for catalogs that aren't already accessible
      const needsCatalogs = accessCheck?.needsGrant || []
      const d = await fetch('/api/portal/admin/uc-run-grants', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ catalogs: needsCatalogs }),
      }).then(r => r.json())
      setGrantResults(d)
      // Re-check access after granting so the list updates
      if (d.allSucceeded) await runAccessCheck()
    } catch (e) {
      setGrantResults({ error: e.message })
    } finally {
      setGranting(false)
    }
  }, [accessCheck, runAccessCheck])

  const saveWarehouse = async () => {
    if (!warehouseId.trim()) { setSaveError('Paste your warehouse ID first.'); return }
    setSaving(true); setSaveError('')
    try {
      const r = await fetch('/api/portal/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql_warehouse_id: warehouseId.trim() }),
      })
      if (!r.ok) throw new Error(await r.text())
      refreshConfig()
      setStep(1)
    } catch (e) { setSaveError(e.message) }
    finally { setSaving(false) }
  }

  const markComplete = async () => {
    await fetch('/api/portal/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ setup_complete: 'true' }),
    }).catch(() => {})
    refreshConfig()
    onDismiss()
  }

  const copyGrantSql = () => {
    navigator.clipboard.writeText(accessCheck?.grantSql || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const progressPct = (step / (STEPS.length - 1)) * 100

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">

          {/* Header */}
          <div className="px-6 pt-6 pb-4" style={{ background: `linear-gradient(135deg, ${BLUE} 0%, #1e4a7a 100%)` }}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/15 flex items-center justify-center">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="font-bold text-white text-lg leading-tight">Set up {appName}</h2>
                  <p className="text-white/70 text-xs mt-0.5">4 quick steps — takes about 2 minutes</p>
                </div>
              </div>
              <button onClick={markComplete} className="text-white/50 hover:text-white/90 transition-colors mt-0.5" title="Skip setup">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-4 h-1.5 bg-white/20 rounded-full overflow-hidden">
              <div className="h-full bg-white rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} />
            </div>
            <div className="flex justify-between mt-1.5">
              {STEPS.map((s, i) => (
                <span key={s.id} className={`text-[10px] font-medium transition-colors ${i <= step ? 'text-white' : 'text-white/40'}`}>
                  {i + 1}. {s.short}
                </span>
              ))}
            </div>
          </div>

          {/* Step content */}
          <div className="px-6 py-5">

            {/* ── Step 1: SQL Warehouse ── */}
            {step === 0 && (
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                    <Warehouse className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">Connect a SQL Warehouse</p>
                    <p className="text-sm text-gray-500 mt-0.5">Required so the app can execute Unity Catalog grants when you approve access requests.</p>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">SQL Warehouse ID</label>
                  {warehousePreFilled && (
                    <div className="flex items-center gap-2 mb-2 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                      <p className="text-xs text-emerald-700">Auto-detected by deploy script — verify below or continue.</p>
                    </div>
                  )}
                  <input
                    type="text" value={warehouseId}
                    onChange={e => { setWarehouseId(e.target.value); setPreFilled(false) }}
                    onKeyDown={e => e.key === 'Enter' && saveWarehouse()}
                    placeholder="e.g. abc1234def567890"
                    autoFocus={!warehousePreFilled}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                  {!warehousePreFilled && (
                    <p className="text-[11px] text-gray-400 mt-1.5">
                      Find it in SQL Warehouses → your warehouse → <strong>Connection Details</strong> → HTTP Path — it's the last segment after <code className="bg-gray-100 px-1 rounded">/sql/1.0/warehouses/</code>
                    </p>
                  )}
                </div>
                {saveError && <p className="text-xs text-red-600">{saveError}</p>}
                <div className="flex gap-2 pt-1">
                  <button onClick={saveWarehouse} disabled={saving || !warehouseId.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-50 transition-opacity"
                    style={{ backgroundColor: BLUE }}>
                    {saving ? 'Saving…' : warehousePreFilled ? 'Confirm & continue' : 'Save & continue'} {!saving && <ArrowRight className="h-4 w-4" />}
                  </button>
                  <button onClick={() => setStep(1)} className="px-4 py-2.5 rounded-lg text-sm text-gray-400 hover:text-gray-600">
                    Skip for now
                  </button>
                </div>
              </div>
            )}

            {/* ── Step 2: Catalog access ── */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-violet-50 flex items-center justify-center shrink-0">
                    <ShieldCheck className="h-5 w-5 text-violet-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">Grant catalog access to the app</p>
                    <p className="text-sm text-gray-500 mt-0.5">
                      The app runs as a service principal. It needs <code className="bg-gray-100 px-1 rounded text-xs">USE SCHEMA</code> on each schema to browse and import tables.
                    </p>
                  </div>
                </div>

                {/* Loading */}
                {accessLoading && (
                  <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
                    <RefreshCw className="h-4 w-4 animate-spin" /> Checking catalog access…
                  </div>
                )}

                {/* Error */}
                {!accessLoading && accessCheck?.error && (
                  <div className="bg-red-50 border border-red-100 rounded-lg px-4 py-3 text-xs text-red-600">
                    Could not check access: {accessCheck.error}
                  </div>
                )}

                {/* Results */}
                {!accessLoading && accessCheck && !accessCheck.error && (
                  <>
                    {/* Catalog list */}
                    <div className="border border-gray-100 rounded-xl overflow-hidden divide-y divide-gray-100">
                      {accessCheck.catalogs.map(cat => (
                        <div key={cat.name}>
                          <div className="flex items-center gap-3 px-4 py-2.5">
                            <Database className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                            <span className="text-sm text-gray-700 font-mono flex-1 truncate">{cat.name}</span>
                            {cat.accessible
                              ? <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium shrink-0"><CheckCircle2 className="h-3.5 w-3.5" /> Accessible</span>
                              : cat.canListSchemas
                                ? (cat.schemasNeedingGrant?.length > 0
                                  ? <span className="flex items-center gap-1 text-xs text-amber-600 font-medium shrink-0"><AlertTriangle className="h-3.5 w-3.5" /> Tables need grant</span>
                                  : <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium shrink-0"><CheckCircle2 className="h-3.5 w-3.5" /> Accessible</span>)
                                : <span className="flex items-center gap-1 text-xs text-red-600 font-medium shrink-0"><AlertTriangle className="h-3.5 w-3.5" /> No access</span>
                            }
                          </div>
                          {/* Per-schema breakdown when schemas are visible but tables aren't */}
                          {!cat.accessible && cat.canListSchemas && cat.schemasNeedingGrant?.length > 0 && (
                            <div className="bg-amber-50 border-t border-amber-100 px-5 py-2 space-y-1">
                              {cat.schemasNeedingGrant.map(s => (
                                <div key={s.name} className="flex items-center gap-2 text-xs text-amber-700">
                                  <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" />
                                  <code className="font-mono">{cat.name}.{s.name}</code>
                                  <span className="text-amber-500">— needs USE SCHEMA</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* All good */}
                    {accessCheck.allAccessible && (
                      <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3">
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                        <p className="text-sm text-emerald-700 font-medium">All catalogs accessible — you're good to go!</p>
                      </div>
                    )}

                    {/* Grant section */}
                    {!accessCheck.allAccessible && accessCheck.grantSql && (
                      <div className="space-y-3">
                        {/* Auto-grant button */}
                        <div className="bg-violet-50 border border-violet-100 rounded-xl p-4 space-y-3">
                          <div>
                            <p className="text-sm font-medium text-violet-900">Grant access automatically</p>
                            <p className="text-xs text-violet-600 mt-0.5">
                              Runs <code className="bg-violet-100 px-1 rounded">USE CATALOG + USE SCHEMA + SELECT</code> on each catalog — cascades to all schemas and future tables.
                            </p>
                          </div>
                          {/* Grant results */}
                          {grantResults && !grantResults.error && (
                            <div className="space-y-1">
                              {grantResults.results?.map(r => (
                                <div key={r.catalog} className={`flex items-center gap-2 text-xs ${r.success ? 'text-emerald-700' : 'text-red-600'}`}>
                                  {r.success
                                    ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                                    : <AlertTriangle className="h-3.5 w-3.5 shrink-0" />}
                                  <span className="font-mono">{r.catalog}</span>
                                  {!r.success && <span className="text-red-400">— {r.errors?.[0]}</span>}
                                </div>
                              ))}
                            </div>
                          )}
                          {grantResults?.error && (
                            <p className="text-xs text-red-600">{grantResults.error}</p>
                          )}
                          <button onClick={runGrants} disabled={granting || accessLoading}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-opacity disabled:opacity-40"
                            style={{ backgroundColor: BLUE }}>
                            {granting
                              ? <><RefreshCw className="h-4 w-4 animate-spin" /> Granting…</>
                              : <><ShieldCheck className="h-4 w-4" /> Grant access to {accessCheck.needsGrant?.length} catalog{accessCheck.needsGrant?.length !== 1 ? 's' : ''}</>}
                          </button>
                        </div>

                        {/* Manual fallback */}
                        <details className="group">
                          <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">
                            Or run manually in SQL Editor
                          </summary>
                          <div className="mt-2 space-y-2">
                            <div className="relative bg-gray-950 rounded-xl p-4 pr-10">
                              <pre className="text-xs text-emerald-300 font-mono whitespace-pre-wrap leading-relaxed overflow-x-auto">
                                {accessCheck.grantSql}
                              </pre>
                              <button onClick={copyGrantSql} title="Copy SQL"
                                className="absolute top-3 right-3 text-gray-500 hover:text-gray-300 transition-colors">
                                {copied
                                  ? <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                                  : <Copy className="h-4 w-4" />}
                              </button>
                            </div>
                            <div className="flex items-center gap-3">
                              {accessCheck.sqlEditorUrl && (
                                <a href={accessCheck.sqlEditorUrl} target="_blank" rel="noopener noreferrer"
                                  className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors">
                                  <ExternalLink className="h-3.5 w-3.5" /> Open SQL Editor
                                </a>
                              )}
                              <button onClick={runAccessCheck} disabled={accessLoading}
                                className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-40">
                                <RefreshCw className={`h-3.5 w-3.5 ${accessLoading ? 'animate-spin' : ''}`} /> Re-check
                              </button>
                            </div>
                          </div>
                        </details>
                      </div>
                    )}
                  </>
                )}

                <div className="flex gap-2 pt-1">
                  <button onClick={() => setStep(2)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white"
                    style={{ backgroundColor: BLUE }}>
                    {accessCheck?.allAccessible ? 'Continue' : 'Continue anyway'} <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}

            {/* ── Step 3: Import ── */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                    <Package className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">Import your first data products</p>
                    <p className="text-sm text-gray-500 mt-0.5">Pull tables from Unity Catalog into the catalog. Users can't discover anything until you import.</p>
                  </div>
                </div>
                {imported ? (
                  <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-100 rounded-lg px-4 py-3">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    <p className="text-sm text-emerald-700 font-medium">Tables imported. Ready to go!</p>
                  </div>
                ) : (
                  <button onClick={() => setShowImport(true)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white"
                    style={{ backgroundColor: BLUE }}>
                    <Database className="h-4 w-4" /> Import from Unity Catalog
                  </button>
                )}
                <div className="flex gap-2 pt-1">
                  {imported && (
                    <button onClick={() => setStep(3)}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white"
                      style={{ backgroundColor: BLUE }}>
                      Continue <ArrowRight className="h-4 w-4" />
                    </button>
                  )}
                  <button onClick={() => setStep(3)} className="px-4 py-2.5 rounded-lg text-sm text-gray-400 hover:text-gray-600">
                    {imported ? '' : 'Skip for now'}
                  </button>
                </div>
              </div>
            )}

            {/* ── Step 4: Done ── */}
            {step === 3 && (
              <div className="space-y-4 text-center py-2">
                <div className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center mx-auto">
                  <CheckCircle2 className="h-8 w-8 text-emerald-500" />
                </div>
                <div>
                  <p className="font-bold text-gray-900 text-lg">You're all set!</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {appName} is configured and ready. Invite your team and start approving access requests.
                  </p>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-left space-y-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">What's next</p>
                  {[
                    'Share this URL with your data consumers',
                    'Add data stewards in Manage → Users',
                    'Customise the portal name and logo in Settings',
                  ].map(t => (
                    <div key={t} className="flex items-center gap-2 text-sm text-gray-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                      {t}
                    </div>
                  ))}
                </div>
                <button onClick={markComplete}
                  className="w-full py-3 rounded-xl text-sm font-semibold text-white"
                  style={{ backgroundColor: BLUE }}>
                  Open {appName} →
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {showImport && (
        <ImportUCModal
          onClose={() => setShowImport(false)}
          onImported={() => { setShowImport(false); setImported(true) }}
        />
      )}
    </>
  )
}

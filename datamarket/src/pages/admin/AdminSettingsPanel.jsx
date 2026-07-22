import React, { useState, useEffect } from 'react'
import { RotateCcw, AlertTriangle, CheckCircle2, RefreshCw, Save, Sparkles, Check } from 'lucide-react'
import { useAppConfig } from '../../context/AppConfigContext'
import { DataMarket_BLUE } from './adminConstants'

export function AdminDemoControlsPanel() {
  const [resetState, setResetState]   = useState('idle')   // idle | confirm | loading | done
  const [seedState,  setSeedState]    = useState('idle')   // idle | loading | done | error
  const [seedCounts, setSeedCounts]   = useState(null)

  const handleReset = async () => {
    setResetState('loading')
    try {
      await fetch('/api/portal/demo-reset', { method: 'POST' })
      setResetState('done')
      setTimeout(() => { setResetState('idle'); window.location.reload() }, 1500)
    } catch { setResetState('idle') }
  }

  const handleSeed = async () => {
    setSeedState('loading')
    try {
      const res = await fetch('/api/portal/demo-seed', { method: 'POST' })
      const data = await res.json()
      setSeedCounts(data.counts)
      setSeedState('done')
      setTimeout(() => { setSeedState('idle'); window.location.reload() }, 2000)
    } catch { setSeedState('error') }
  }

  return (
    <div className="max-w-xl space-y-6">
      <div className="bg-rose-50 border border-rose-200 rounded-xl p-5">
        <h3 className="font-semibold text-rose-800 mb-1 flex items-center gap-2">
          <RotateCcw className="h-4 w-4" /> Reset Demo Data
        </h3>
        <p className="text-sm text-rose-700 mb-4">
          Clears all access requests, audit logs, and user library entries. Users and published products are preserved.
        </p>
        {resetState === 'idle' && (
          <button onClick={() => setResetState('confirm')}
            className="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium hover:bg-rose-700">
            Reset Demo Data
          </button>
        )}
        {resetState === 'confirm' && (
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
            <span className="text-sm text-rose-700 font-medium">Are you sure? This cannot be undone.</span>
            <button onClick={handleReset} className="px-3 py-1.5 bg-rose-600 text-white rounded text-sm font-medium hover:bg-rose-700">Yes, reset</button>
            <button onClick={() => setResetState('idle')} className="px-3 py-1.5 border border-gray-200 rounded text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        )}
        {resetState === 'loading' && <span className="flex items-center gap-2 text-sm text-rose-600"><RotateCcw className="h-4 w-4 animate-spin" /> Clearing...</span>}
        {resetState === 'done'    && <span className="flex items-center gap-2 text-sm text-emerald-600 font-medium"><CheckCircle2 className="h-4 w-4" /> Reset complete</span>}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h3 className="font-semibold text-blue-800 mb-1 flex items-center gap-2">
          <RefreshCw className="h-4 w-4" /> Load Demo Data
        </h3>
        <p className="text-sm text-blue-700 mb-4">
          Seeds 8 sample data products, 3 demo users, and 1 pending access request. Safe to run on an empty catalog — skips existing records.
        </p>
        {seedState === 'idle' && (
          <button onClick={handleSeed}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            Load Demo Data
          </button>
        )}
        {seedState === 'loading' && <span className="flex items-center gap-2 text-sm text-blue-600"><RefreshCw className="h-4 w-4 animate-spin" /> Seeding...</span>}
        {seedState === 'done'    && <span className="flex items-center gap-2 text-sm text-emerald-600 font-medium"><CheckCircle2 className="h-4 w-4" /> {seedCounts ? `Loaded — ${seedCounts.products} products, ${seedCounts.users} users` : 'Loaded'}</span>}
        {seedState === 'error'   && <span className="text-sm text-red-600">Seed failed — check app logs.</span>}
      </div>

      <p className="text-xs text-gray-400">Demo Controls are only visible when <code className="font-mono bg-gray-100 px-1 rounded">DEMO_MODE=true</code>.</p>
    </div>
  )
}

export function AdminSettingsPanel() {
  const { appName, appSubtitle, appLogoUrl, sqlWarehouseId: cfgWarehouse, rfaEnabled, setupComplete, demoMode, refreshConfig,
          autoDiscoverEnabled, autoDiscoverPrefix, navLinks: configNavLinks, askAiEnabled: cfgAskAi, insightsEnabled: cfgInsights,
          featureRequestsEnabled: cfgFeatureRequests, contributeUrl: cfgContributeUrl,
          aboutText: configAboutText, contactName: configContactName,
          contactEmail: configContactEmail, contactNote: configContactNote,
          faqItems: configFaqItems, searchChips: configSearchChips } = useAppConfig()

  const DEFAULT_NAV_LINKS = [
    { label: 'About',   visible: true },
    { label: 'FAQ',     visible: true },
    { label: 'Contact', visible: true },
  ]
  const DEFAULT_FAQ = [
    { q: 'What is a data product?', a: 'A certified, documented dataset made available for discovery and access through this portal.' },
    { q: 'How do I request access?', a: 'Open a product from the Discover page and click "Request Access". A data steward will review your request.' },
    { q: 'How long does approval take?', a: 'Once approved, Unity Catalog permissions are granted immediately.' },
  ]

  const [form, setForm] = useState({
    app_name:        appName,
    app_subtitle:    appSubtitle,
    app_logo_url:    appLogoUrl || '',
    sql_warehouse_id:cfgWarehouse || '',
    rfa_enabled:     String(rfaEnabled),
    ask_ai_enabled:             String(cfgAskAi !== false),
    insights_enabled:           String(cfgInsights !== false),
    feature_requests_enabled:   String(cfgFeatureRequests === true),
    contribute_url:             cfgContributeUrl || '',
    auto_discover_enabled: String(autoDiscoverEnabled),
    auto_discover_prefix:  autoDiscoverPrefix || '',
    about_text:      configAboutText || '',
    contact_name:    configContactName || '',
    contact_email:   configContactEmail || '',
    contact_note:    configContactNote || '',
  })
  const [navLinks, setNavLinks] = useState(configNavLinks?.length ? configNavLinks : DEFAULT_NAV_LINKS)
  const [faqItems, setFaqItems] = useState(configFaqItems?.length ? configFaqItems : DEFAULT_FAQ)
  const [searchChips, setSearchChips] = useState(configSearchChips || [])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)
  const [error, setError]   = useState('')

  useEffect(() => {
    setForm({
      app_name:        appName,
      app_subtitle:    appSubtitle,
      app_logo_url:    appLogoUrl || '',
      sql_warehouse_id:cfgWarehouse || '',
      rfa_enabled:     String(rfaEnabled),
      ask_ai_enabled:             String(cfgAskAi !== false),
      insights_enabled:           String(cfgInsights !== false),
      feature_requests_enabled:   String(cfgFeatureRequests === true),
      contribute_url:             cfgContributeUrl || '',
      auto_discover_enabled: String(autoDiscoverEnabled),
      auto_discover_prefix:  autoDiscoverPrefix || '',
      about_text:      configAboutText || '',
      contact_name:    configContactName || '',
      contact_email:   configContactEmail || '',
      contact_note:    configContactNote || '',
    })
    setNavLinks(configNavLinks?.length ? configNavLinks : DEFAULT_NAV_LINKS)
    setFaqItems(configFaqItems?.length ? configFaqItems : DEFAULT_FAQ)
    setSearchChips(configSearchChips || [])
  }, [appName, appSubtitle, appLogoUrl, cfgWarehouse, rfaEnabled, cfgAskAi, cfgInsights, cfgFeatureRequests, cfgContributeUrl,
      autoDiscoverEnabled, autoDiscoverPrefix,
      configNavLinks, configAboutText, configContactName, configContactEmail, configContactNote, configFaqItems, configSearchChips])

  const handleSave = async () => {
    setSaving(true); setSaved(false); setError('')
    try {
      const r = await fetch('/api/portal/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          setup_complete: 'true',
          nav_links:    JSON.stringify(navLinks),
          faq_items:    JSON.stringify(faqItems),
          search_chips: JSON.stringify(searchChips),
        }),
      })
      if (!r.ok) throw new Error(await r.text())
      setSaved(true)
      refreshConfig()
      setTimeout(() => setSaved(false), 3000)
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  const field = (label, key, placeholder = '', hint = '') => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type="text"
        value={form[key]}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
    </div>
  )

  const toggle = (key, color = 'bg-blue-600') => (
    <button onClick={() => setForm(f => ({ ...f, [key]: f[key] === 'true' ? 'false' : 'true' }))}
      className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors ${form[key] === 'true' ? color : 'bg-gray-200'}`}>
      <span className={`pointer-events-none block h-5 w-5 rounded-full bg-white shadow transition-transform ${form[key] === 'true' ? 'translate-x-5' : 'translate-x-0'}`} />
    </button>
  )

  return (
    <div className="max-w-2xl space-y-6 mt-4">
      {setupComplete ? (
        <div className="rounded-xl border border-gray-200 bg-gray-50 px-5 py-3 flex items-center justify-between">
          <p className="text-sm text-gray-500">Need to revisit the setup steps?</p>
          <button
            onClick={async () => {
              await fetch('/api/portal/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ setup_complete: 'false' }),
              }).catch(() => {})
              refreshConfig()
            }}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-white transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Re-open setup wizard
          </button>
        </div>
      ) : (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 flex gap-4">
          <Sparkles className="h-6 w-6 text-blue-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-blue-900 text-sm">Finish setting up your portal</p>
            <p className="text-blue-700 text-sm mt-1">
              Set your portal name and SQL Warehouse ID, then save. Changes take effect immediately — no redeploy needed.
            </p>
          </div>
        </div>
      )}

      {/* ── Branding & Layout ─────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">Branding & Layout</h3>
        <div className="space-y-4">
          {field('Portal Name', 'app_name', 'DataMarket', 'Shown in the top navigation bar')}
          {field('Tagline', 'app_subtitle', 'Data Discovery & Access', 'Subtitle shown under the portal name')}
          {field('Logo URL', 'app_logo_url', '/your-logo.png', 'Path or full URL. Leave empty to hide.')}
        </div>
        <div className="border-t border-gray-100 pt-4 space-y-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Navigation visibility</p>
          {[
            { key: 'ask_ai_enabled',           label: 'Ask AI',        desc: 'Natural language catalog search (Databricks FMAPI)' },
            { key: 'insights_enabled',          label: 'Insights',      desc: 'Dashboard and data product insights gallery' },
            { key: 'feature_requests_enabled',  label: 'Requests',      desc: 'Data demand board — users submit & upvote data requests (off by default)' },
          ].map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-700">{label}</p>
                <p className="text-xs text-gray-400">{desc}</p>
              </div>
              {toggle(key)}
            </div>
          ))}
          <p className="text-xs text-gray-400">Home, Discover, and My Data / Manage are always shown.</p>
        </div>
        <div className="border-t border-gray-100 pt-4 space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Footer links</p>
          {navLinks.map((link, i) => (
            <div key={i} className="flex items-center gap-3 py-1">
              <button onClick={() => setNavLinks(ls => ls.map((l, idx) => idx === i ? { ...l, visible: !l.visible } : l))}
                className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors ${link.visible ? 'bg-blue-600' : 'bg-gray-300'}`}>
                <span className={`block h-4 w-4 rounded-full bg-white shadow transition-transform ${link.visible ? 'translate-x-4' : 'translate-x-0'}`} />
              </button>
              <span className="text-sm font-medium text-gray-700 w-16">{link.label}</span>
              <span className="text-xs text-gray-400">in-app page · content editable in Page Content below</span>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-100 pt-4">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Search chips</p>
            <button onClick={() => setSearchChips(c => [...c, { label: '', q: '' }])}
              className="text-xs text-blue-600 hover:underline">+ Add chip</button>
          </div>
          <p className="text-xs text-gray-400 mb-3">
            Shortcut buttons below the home search bar. Leave empty to auto-generate from your catalog domains.
          </p>
          {searchChips.length === 0 ? (
            <p className="text-xs text-gray-400 italic">Auto-generating from catalog domains. Add chips above to override.</p>
          ) : (
            <div className="space-y-2">
              {searchChips.map((chip, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input type="text" value={chip.label} placeholder="Label (e.g. ✦ Fire data)"
                    onChange={e => setSearchChips(c => c.map((x, idx) => idx === i ? { ...x, label: e.target.value } : x))}
                    className="w-40 px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-400" />
                  <input type="text" value={chip.q} placeholder="AI question (e.g. Show me fire incident data)"
                    onChange={e => setSearchChips(c => c.map((x, idx) => idx === i ? { ...x, q: e.target.value } : x))}
                    className="flex-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-400" />
                  <button onClick={() => setSearchChips(c => c.filter((_, idx) => idx !== i))}
                    className="text-red-400 hover:text-red-600 text-xs px-1.5 shrink-0">✕</button>
                </div>
              ))}
              <button onClick={() => setSearchChips([])}
                className="text-xs text-gray-400 hover:text-gray-600 underline mt-1">
                Clear all (revert to auto)
              </button>
            </div>
          )}
        </div>
      </div>
      {/* ── Integrations ──────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">Integrations</h3>
        {field('SQL Warehouse ID', 'sql_warehouse_id', 'abc123...', 'Required to execute real GRANT / REVOKE in Unity Catalog on approval. Leave empty to log approvals only.')}
        <div className={`rounded-lg px-4 py-2.5 text-xs border flex items-center gap-2 ${form.sql_warehouse_id ? 'bg-emerald-50 border-emerald-100' : 'bg-amber-50 border-amber-100'}`}>
          <span className={`w-2 h-2 rounded-full shrink-0 ${form.sql_warehouse_id ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          {form.sql_warehouse_id
            ? <span className="text-emerald-700 font-medium">UC grants enabled — GRANT SELECT will execute on approval</span>
            : <span className="text-amber-700">UC grants disabled — approvals are logged but no UC permissions are set</span>
          }
        </div>
      </div>

      {/* ── Mode ──────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">Mode</h3>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-700">RFA Notifications</p>
            <p className="text-xs text-gray-400 mt-0.5">Send Databricks RFA access-request notifications when a user requests access.</p>
          </div>
          {toggle('rfa_enabled')}
        </div>
        {demoMode && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-800">
            <strong>Demo Mode is active.</strong> SSO identity and real UC grants are disabled.
            Set <code className="font-mono bg-amber-100 px-1 rounded">DEMO_MODE=false</code> in app.yaml and redeploy to enable production mode.
          </div>
        )}
      </div>

      {/* ── Data Product Lifecycle ─────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">Data Product Lifecycle</h3>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-700">Auto-Discover New UC Tables</p>
            <p className="text-xs text-gray-400 mt-0.5">
              New tables matching the prefix below are automatically added as <span className="font-medium text-amber-600">Draft</span> each time the app starts for admin review — nothing goes live without approval.
            </p>
          </div>
          {toggle('auto_discover_enabled', 'bg-emerald-500')}
        </div>
        {field('Discovery Prefix', 'auto_discover_prefix', 'main.gold or main.gold.sales_', 'catalog.schema or catalog.schema.name_prefix to scan.')}
      </div>

      {/* ── Page Content ──────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">Page Content</h3>

        <div className="space-y-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">About page</p>
          <textarea rows={3} value={form.about_text}
            onChange={e => setForm(f => ({ ...f, about_text: e.target.value }))}
            placeholder="Describe this portal in 2–3 sentences. Leave blank to show the default description."
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none" />
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Product feedback link <span className="text-gray-400 font-normal">(Loop 2 — optional)</span>
            </label>
            <input type="url" value={form.contribute_url}
              onChange={e => setForm(f => ({ ...f, contribute_url: e.target.value }))}
              placeholder="https://github.com/your-org/datamarket/issues/new"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            <p className="text-[11px] text-gray-400 mt-1">Displayed on the About page as a "Suggest a feature" link. GitHub Issues, Slack channel, or any URL.</p>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Contact page</p>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
              <input type="text" value={form.contact_name} placeholder="Your name"
                onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
              <input type="email" value={form.contact_email} placeholder="you@databricks.com"
                onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>
          <input type="text" value={form.contact_note} placeholder="Note — e.g. Slack: #data-platform · Response time: 1 business day"
            onChange={e => setForm(f => ({ ...f, contact_note: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>

        <div className="border-t border-gray-100 pt-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">FAQ items</p>
            <button onClick={() => setFaqItems(f => [...f, { q: '', a: '' }])}
              className="text-xs text-blue-600 hover:underline">+ Add question</button>
          </div>
          <div className="space-y-3">
            {faqItems.map((item, i) => (
              <div key={i} className="border border-gray-100 rounded-lg p-3 space-y-2 bg-gray-50">
                <div className="flex items-start gap-2">
                  <input type="text" value={item.q} placeholder="Question"
                    onChange={e => setFaqItems(f => f.map((x, idx) => idx === i ? { ...x, q: e.target.value } : x))}
                    className="flex-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white" />
                  <button onClick={() => setFaqItems(f => f.filter((_, idx) => idx !== i))}
                    className="text-red-400 hover:text-red-600 text-xs px-2 py-1.5 shrink-0">✕</button>
                </div>
                <textarea rows={2} value={item.a} placeholder="Answer"
                  onChange={e => setFaqItems(f => f.map((x, idx) => idx === i ? { ...x, a: e.target.value } : x))}
                  className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none bg-white" />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 pb-4">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
          style={{ backgroundColor: DataMarket_BLUE }}>
          <Save className="h-4 w-4" />
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        {saved && <span className="text-sm text-green-600 flex items-center gap-1"><Check className="h-4 w-4" /> Saved — changes are live</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </div>
  )
}

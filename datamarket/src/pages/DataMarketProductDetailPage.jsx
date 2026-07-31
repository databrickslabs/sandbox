import React, { useState, useEffect, useCallback } from 'react'
import { ArrowLeft, BarChart3, FileText, Database, X, Calendar, User, RefreshCw, Tag, Lock, ExternalLink, CheckCircle2, Clock, Eye, EyeOff, ShieldAlert, ShieldCheck, Shield, Bot, LayoutDashboard, AppWindow, Cpu, Layers, Edit3, ClipboardList, Check, XCircle } from 'lucide-react'
import { usePersona } from '../context/PersonaContext'
import { useAppConfig } from '../context/AppConfigContext'

const DataMarket_BLUE = '#003865'

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
  Source:            Layers,
}

const typeOpenLabel = {
  Dashboard:         'Open Dashboard',
  'AI/BI Dashboard': 'Open AI/BI Dashboard',
  'Genie Space':     'Open Genie',
  Dataset:           'Open Dataset',
  Report:            'Open Report',
  App:               'Open App',
  'ML Model':        'View Model',
  Source:            'View Source',
}

// ── Column-level sensitivity schemas per domain ───────────────────────────────
// Sensitivity levels: PUBLIC | INTERNAL | CONFIDENTIAL | PII
// masked: true       = hidden before access granted (standard ABAC column mask)
// elevatedPII: true  = stays masked even after standard approval (requires elevated grant)
const schemaByDomain = {
  Budget: [
    { name: 'department',        type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Department name' },
    { name: 'fiscal_year',       type: 'INTEGER',   sensitivity: 'PUBLIC',       masked: false,                   description: 'Fiscal year' },
    { name: 'budget_allocated',  type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Total budget allocation' },
    { name: 'ytd_spent',         type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Year-to-date expenditure' },
    { name: 'variance',          type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Budget vs. actual variance' },
    { name: 'cost_center_code',  type: 'STRING',    sensitivity: 'CONFIDENTIAL', masked: true,                    description: 'Internal cost center identifier' },
    { name: 'approver_id',       type: 'STRING',    sensitivity: 'CONFIDENTIAL', masked: true,                    description: 'Budget approver employee ID' },
  ],
  HRIS: [
    { name: 'department',        type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Department name' },
    { name: 'job_title',         type: 'STRING',    sensitivity: 'INTERNAL',     masked: false,                   description: 'Employee job title' },
    { name: 'headcount',         type: 'INTEGER',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Total headcount' },
    { name: 'turnover_rate',     type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Annual turnover rate (%)' },
    { name: 'avg_salary',        type: 'DECIMAL',   sensitivity: 'CONFIDENTIAL', masked: true,                    description: 'Average salary by role' },
    { name: 'employee_id',       type: 'STRING',    sensitivity: 'PII',          masked: true,                    description: 'Unique employee identifier' },
    { name: 'ssn_last4',         type: 'STRING',    sensitivity: 'PII',          masked: true,  elevatedPII: true, description: 'Last 4 digits of SSN' },
    { name: 'date_of_birth',     type: 'DATE',      sensitivity: 'PII',          masked: true,  elevatedPII: true, description: 'Employee date of birth' },
  ],
  Payroll: [
    { name: 'pay_period',        type: 'DATE',      sensitivity: 'INTERNAL',     masked: false,                   description: 'Pay period end date' },
    { name: 'department',        type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Department name' },
    { name: 'gross_pay',         type: 'DECIMAL',   sensitivity: 'CONFIDENTIAL', masked: true,                    description: 'Gross payroll amount' },
    { name: 'net_pay',           type: 'DECIMAL',   sensitivity: 'CONFIDENTIAL', masked: true,                    description: 'Net payroll after deductions' },
    { name: 'overtime_hours',    type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Total overtime hours' },
    { name: 'employee_id',       type: 'STRING',    sensitivity: 'PII',          masked: true,                    description: 'Employee identifier' },
    { name: 'bank_account_last4',type: 'STRING',    sensitivity: 'PII',          masked: true,  elevatedPII: true, description: 'Last 4 digits of bank account' },
  ],
  'Property Tax': [
    { name: 'parcel_id',         type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Property parcel identifier' },
    { name: 'district',          type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Tax district' },
    { name: 'assessed_value',    type: 'DECIMAL',   sensitivity: 'PUBLIC',       masked: false,                   description: 'Assessed property value' },
    { name: 'tax_levied',        type: 'DECIMAL',   sensitivity: 'PUBLIC',       masked: false,                   description: 'Tax amount levied' },
    { name: 'collection_status', type: 'STRING',    sensitivity: 'INTERNAL',     masked: false,                   description: 'Payment collection status' },
    { name: 'owner_name',        type: 'STRING',    sensitivity: 'PII',          masked: true,  elevatedPII: true, description: 'Property owner full name' },
    { name: 'owner_address',     type: 'STRING',    sensitivity: 'PII',          masked: true,  elevatedPII: true, description: 'Property owner mailing address' },
  ],
  Demographics: [
    { name: 'census_tract',      type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Census tract identifier' },
    { name: 'age_group',         type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Age bracket' },
    { name: 'population',        type: 'INTEGER',   sensitivity: 'PUBLIC',       masked: false,                   description: 'Population count' },
    { name: 'median_income',     type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Median household income' },
    { name: 'household_size',    type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Average household size' },
  ],
  'Public Safety': [
    { name: 'incident_id',      type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Unique incident identifier' },
    { name: 'incident_type',    type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Category of incident (fire, medical, crime)' },
    { name: 'response_time_min',type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Response time in minutes' },
    { name: 'district',         type: 'STRING',    sensitivity: 'PUBLIC',       masked: false,                   description: 'Service district' },
    { name: 'latitude',         type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Incident latitude' },
    { name: 'longitude',        type: 'DECIMAL',   sensitivity: 'INTERNAL',     masked: false,                   description: 'Incident longitude' },
    { name: 'officer_badge',    type: 'STRING',    sensitivity: 'CONFIDENTIAL', masked: true,                    description: 'Responding officer badge number' },
    { name: 'victim_name',      type: 'STRING',    sensitivity: 'PII',          masked: true,  elevatedPII: true, description: 'Victim full name' },
  ],
}

const defaultSchema = [
  { name: 'id',          type: 'STRING',  sensitivity: 'INTERNAL', masked: false, description: 'Record identifier' },
  { name: 'name',        type: 'STRING',  sensitivity: 'PUBLIC',   masked: false, description: 'Record name' },
  { name: 'category',    type: 'STRING',  sensitivity: 'PUBLIC',   masked: false, description: 'Category classification' },
  { name: 'value',       type: 'DECIMAL', sensitivity: 'INTERNAL', masked: false, description: 'Numeric value' },
  { name: 'updated_at',  type: 'DATE',    sensitivity: 'PUBLIC',   masked: false, description: 'Last update timestamp' },
]

function getSchema(product) {
  const domain = (product.category || product.domain || '').toLowerCase()
  if (domain.includes('hris') || domain.includes('ehr') || domain.includes('human resource') || domain.includes(' hr')) return schemaByDomain['HRIS']
  if (domain.includes('payroll')) return schemaByDomain['Payroll']
  if (domain.includes('budget') || domain.includes('financ') || domain.includes('account') || domain.includes('erp')) return schemaByDomain['Budget']
  if (domain.includes('property tax') || domain.includes('tax')) return schemaByDomain['Property Tax']
  if (domain.includes('demograph') || domain.includes('census') || domain.includes('population')) return schemaByDomain['Demographics']
  if (domain.includes('public safety') || domain.includes('incident') || domain.includes('safety')) return schemaByDomain['Public Safety']
  // Also match by product name keywords
  const name = (product.name || '').toLowerCase()
  if (name.includes('employee') || name.includes('headcount') || name.includes('workforce')) return schemaByDomain['HRIS']
  if (name.includes('payroll') || name.includes('compensation')) return schemaByDomain['Payroll']
  if (name.includes('budget') || name.includes('expenditure') || name.includes('finance')) return schemaByDomain['Budget']
  if (name.includes('property tax')) return schemaByDomain['Property Tax']
  if (name.includes('census') || name.includes('population') || name.includes('demographic')) return schemaByDomain['Demographics']
  return defaultSchema
}

const sensitivityConfig = {
  PUBLIC:       { label: 'Public',       color: 'bg-emerald-100 text-emerald-700 border-emerald-200', icon: ShieldCheck },
  INTERNAL:     { label: 'Internal',     color: 'bg-blue-100 text-blue-700 border-blue-200',           icon: Shield },
  CONFIDENTIAL: { label: 'Confidential', color: 'bg-amber-100 text-amber-700 border-amber-200',        icon: ShieldAlert },
  PII:          { label: 'PII',          color: 'bg-red-100 text-red-700 border-red-200',              icon: ShieldAlert },
}

function DataSchemaPanel({ product, accessGranted, onRequestAccess, onTableComment }) {
  const [expanded, setExpanded] = useState(true)
  const [schema, setSchema] = useState(null)
  const [loading, setLoading] = useState(true)
  const [schemaSource, setSchemaSource] = useState(null)

  useEffect(() => {
    if (!product?.product_ref) return
    setLoading(true)
    fetch(`/api/portal/products/${product.product_ref}/schema`)
      .then(r => r.json())
      .then(data => {
        setSchemaSource(data.source)
        if (data.table_comment && onTableComment) onTableComment(data.table_comment)
        if ((data.source === 'unity_catalog' || data.source === 'unity_catalog_rest') && data.columns?.length) {
          setSchema(data.columns)
        } else {
          setSchema(getSchema(product))
        }
      })
      .catch(() => setSchema(getSchema(product)))
      .finally(() => setLoading(false))
  }, [product?.product_ref])

  const cols = schema || []
  const piiCount    = cols.filter(c => c.sensitivity === 'PII').length
  const confCount   = cols.filter(c => c.sensitivity === 'CONFIDENTIAL').length
  const restrictedCount = cols.filter(c => c.masked).length

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 mt-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-gray-400" />
            <h3 className="font-semibold text-gray-900 text-sm">Data Schema & Sensitivity</h3>
            {(schemaSource === 'unity_catalog' || schemaSource === 'unity_catalog_rest') && (
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700 border border-blue-200">Live from UC</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {piiCount > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-red-100 text-red-700 border border-red-200">
                {piiCount} PII col{piiCount !== 1 ? 's' : ''}
              </span>
            )}
            {confCount > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-amber-100 text-amber-700 border border-amber-200">
                {confCount} Confidential
              </span>
            )}
          </div>
        </div>
        <button onClick={() => setExpanded(v => !v)} className="text-xs text-gray-400 hover:text-gray-700 flex items-center gap-1">
          {expanded ? <><EyeOff className="h-3.5 w-3.5" /> Hide</> : <><Eye className="h-3.5 w-3.5" /> Show</>}
        </button>
      </div>

      {expanded && (
        <>
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-gray-400 text-xs justify-center">
              <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Loading schema from Unity Catalog…
            </div>
          ) : cols.length === 0 ? (
            <p className="text-xs text-gray-400 py-4">No schema available — link a UC table to this product in Admin settings.</p>
          ) : (
            <div className="overflow-auto rounded-lg border border-gray-100">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-3 py-2 text-gray-500 font-medium">Column</th>
                    <th className="text-left px-3 py-2 text-gray-500 font-medium">Type</th>
                    <th className="text-left px-3 py-2 text-gray-500 font-medium">Description</th>
                    <th className="text-left px-3 py-2 text-gray-500 font-medium">Sensitivity</th>
                  </tr>
                </thead>
                <tbody>
                  {cols.map((col, i) => {
                    const cfg = sensitivityConfig[col.sensitivity] || sensitivityConfig.INTERNAL
                    const SIcon = cfg.icon
                    return (
                      <tr key={i} className="border-b border-gray-50 last:border-0">
                        <td className="px-3 py-2.5 font-mono text-gray-800 font-medium">{col.name}</td>
                        <td className="px-3 py-2.5 text-gray-400 font-mono">{col.type}</td>
                        <td className="px-3 py-2.5 text-gray-500">{col.description || '—'}</td>
                        <td className="px-3 py-2.5">
                          <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border font-medium ${cfg.color}`}>
                            <SIcon className="h-2.5 w-2.5" />
                            {cfg.label}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Access CTA — below table, only when no access */}
          {!loading && cols.length > 0 && !accessGranted && (
            <div className="mt-4 flex items-center justify-between gap-4 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
              <div>
                <p className="text-xs font-medium text-gray-800">Want to query this dataset?</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Request access to run SQL, use Genie, or connect via Excel and BI tools.
                  {restrictedCount > 0 && ` ${restrictedCount} sensitive column${restrictedCount !== 1 ? 's are' : ' is'} governed by Unity Catalog policy.`}
                </p>
              </div>
              <button onClick={onRequestAccess}
                className="shrink-0 px-4 py-2 rounded-lg text-xs font-medium text-white flex items-center gap-1.5 whitespace-nowrap"
                style={{ backgroundColor: DataMarket_BLUE }}>
                Request Access
              </button>
            </div>
          )}

          {/* Access granted confirmation */}
          {!loading && accessGranted && (
            <div className="mt-3 flex items-center gap-2 bg-emerald-50 border border-emerald-100 rounded-lg px-4 py-3">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <p className="text-xs text-emerald-800">
                <strong>Access granted</strong> — you can query this dataset in SQL, Genie, or any connected tool. UC policies are enforced at the query engine.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function SampleDataPreview({ product, accessGranted, onRequestAccess }) {
  const [expanded, setExpanded] = useState(false)
  const [liveData, setLiveData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [previewSource, setPreviewSource] = useState(null)

  useEffect(() => {
    if (!product?.product_ref) return
    setLoading(true)
    fetch(`/api/portal/products/${product.product_ref}/preview`)
      .then(r => r.json())
      .then(data => {
        setPreviewSource(data.source)
        if (data.source === 'unity_catalog' && data.columns?.length) {
          setLiveData({ columns: data.columns, rows: data.rows })
        } else {
          setLiveData(null)
        }
      })
      .catch(() => setLiveData(null))
      .finally(() => setLoading(false))
  }, [product?.product_ref])

  // Live UC data path
  if (!loading && liveData) {
    const { columns, rows } = liveData
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mt-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-gray-400" />
            <h3 className="font-semibold text-gray-900 text-sm">Sample Data Preview</h3>
            {!accessGranted && (
              <span className="flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                <Lock className="h-2.5 w-2.5" /> Restricted
              </span>
            )}
            <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700 border border-blue-200">Live from UC</span>
          </div>
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-xs text-gray-400 hover:text-gray-700 flex items-center gap-1"
          >
            {expanded ? <><EyeOff className="h-3.5 w-3.5" /> Hide</> : <><Eye className="h-3.5 w-3.5" /> Preview</>}
          </button>
        </div>

        {expanded ? (
          <div className="relative overflow-auto rounded-lg border border-gray-100">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {columns.map(col => (
                    <th key={col} className="text-left px-3 py-2 font-medium text-gray-500 whitespace-nowrap">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr key={ri} className={`border-b border-gray-50 last:border-0 ${!accessGranted ? 'select-none' : ''}`}>
                  {row.map((cell, ci) => (
                    <td key={ci} className={`px-3 py-2 text-gray-700 ${!accessGranted ? 'blur-[5px]' : ''}`}>
                      <span title={String(cell ?? '')} className="block max-w-[200px] truncate">
                        {cell ?? '—'}
                      </span>
                    </td>
                  ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {!accessGranted && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/60 backdrop-blur-[1px] rounded-lg">
                <Lock className="h-6 w-6 text-gray-400 mb-2" />
                <p className="text-sm font-medium text-gray-700 mb-3">Request access to view full data</p>
                <button
                  onClick={onRequestAccess}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-white flex items-center gap-1.5"
                  style={{ backgroundColor: DataMarket_BLUE }}
                >
                  <Lock className="h-3 w-3" /> Request Access
                </button>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-gray-400">
            {accessGranted
              ? `${rows.length} live rows from Unity Catalog — click Preview to explore`
              : 'Preview is blurred. Request access to unlock full dataset.'}
          </p>
        )}
      </div>
    )
  }

  // No warehouse configured — show a clear actionable message
  if (!loading && previewSource === 'no_warehouse') {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mt-6">
        <div className="flex items-center gap-2 mb-3">
          <Database className="h-4 w-4 text-gray-400" />
          <h3 className="font-semibold text-gray-900 text-sm">Sample Data Preview</h3>
        </div>
        <div className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-lg px-4 py-4">
          <Database className="h-4 w-4 text-gray-400 shrink-0" />
          <div>
            <p className="text-xs font-medium text-gray-700">SQL Warehouse required for live preview</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Go to <strong>Manage → Settings</strong> and set your SQL Warehouse ID to enable live sample data.
            </p>
          </div>
        </div>
      </div>
    )
  }

  // No UC table linked — no preview possible
  if (!loading && (previewSource === 'synthetic' || (!liveData && !product?.uc_full_name))) {
    return null
  }

  // Error state — warehouse is set but query failed
  if (!loading && !liveData && product?.uc_full_name) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mt-6">
        <div className="flex items-center gap-2 mb-3">
          <Database className="h-4 w-4 text-gray-400" />
          <h3 className="font-semibold text-gray-900 text-sm">Sample Data Preview</h3>
        </div>
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-lg px-4 py-4">
          <Database className="h-4 w-4 text-amber-500 shrink-0" />
          <div>
            <p className="text-xs font-medium text-amber-800">Could not load preview</p>
            <p className="text-xs text-amber-700 mt-0.5">Check that the app's service principal has <strong>Can use</strong> permission on the SQL Warehouse.</p>
          </div>
        </div>
      </div>
    )
  }

  // Fallback: synthetic rows (product has no uc_full_name at all)
  const { columns: synthCols, rows: synthRows, grantedRows } = getSampleData(product)
  const schema = getSchema(product)
  const elevatedIndices = new Set(
    synthCols.map((col, i) => {
      const key = col.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
      const match = schema.find(s => s.name.toLowerCase() === key || col.toLowerCase().includes(s.name.toLowerCase()))
      return match?.elevatedPII ? i : null
    }).filter(i => i !== null)
  )
  const displayRows = accessGranted ? grantedRows : synthRows

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-gray-400" />
          <h3 className="font-semibold text-gray-900 text-sm">Sample Data Preview</h3>
          {!accessGranted && (
            <span className="flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
              <Lock className="h-2.5 w-2.5" /> Restricted
            </span>
          )}
          {accessGranted && elevatedIndices.size > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
              <ShieldAlert className="h-2.5 w-2.5" /> {elevatedIndices.size} col{elevatedIndices.size !== 1 ? 's' : ''} elevated PII
            </span>
          )}
        </div>
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-xs text-gray-400 hover:text-gray-700 flex items-center gap-1"
        >
          {expanded ? <><EyeOff className="h-3.5 w-3.5" /> Hide</> : <><Eye className="h-3.5 w-3.5" /> Preview</>}
        </button>
      </div>

      {expanded && !loading && (
        <div className="relative overflow-auto rounded-lg border border-gray-100">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                {synthCols.map((col, i) => (
                  <th key={col} className={`text-left px-3 py-2 font-medium whitespace-nowrap ${accessGranted && elevatedIndices.has(i) ? 'text-red-400' : 'text-gray-500'}`}>
                    {col}
                    {accessGranted && elevatedIndices.has(i) && <ShieldAlert className="inline h-2.5 w-2.5 ml-1 text-red-400" />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, ri) => (
                <tr key={ri} className={`border-b border-gray-50 last:border-0 ${!accessGranted ? 'select-none' : ''}`}>
                  {row.map((cell, ci) => (
                    <td key={ci} className={`px-3 py-2 ${!accessGranted ? 'blur-[5px] text-gray-700' : elevatedIndices.has(ci) ? 'text-red-400 font-mono' : 'text-gray-700'}`}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          {!accessGranted && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/60 backdrop-blur-[1px] rounded-lg">
              <Lock className="h-6 w-6 text-gray-400 mb-2" />
              <p className="text-sm font-medium text-gray-700 mb-3">Request access to view full data</p>
              <button
                onClick={onRequestAccess}
                className="px-4 py-2 rounded-lg text-xs font-medium text-white flex items-center gap-1.5"
                style={{ backgroundColor: DataMarket_BLUE }}
              >
                <Lock className="h-3 w-3" /> Request Access
              </button>
            </div>
          )}
        </div>
      )}

      {loading && expanded && (
        <div className="flex items-center gap-2 py-6 text-gray-400 text-xs justify-center">
          <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Fetching preview rows…
        </div>
      )}

      {!expanded && (
        <p className="text-xs text-gray-400">
          {accessGranted
            ? `${displayRows.length} sample rows available — click Preview to explore`
            : 'Preview is blurred. Request access to unlock full dataset.'}
        </p>
      )}
    </div>
  )
}

function AccessRequestModal({ product, onClose }) {
  const { submitRequest, persona, myRequests } = usePersona()
  const [submitted, setSubmitted] = useState(false)
  const [form, setForm] = useState({ name: persona.name, team: persona.department, reason: '', agreed: false })

  const existingRequest = myRequests.find(r => r.productId === product.id)

  if (existingRequest && !submitted) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 bg-amber-50">
            <Clock className="h-8 w-8 text-amber-500" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Request Already Submitted</h3>
          <p className="text-gray-500 text-sm mb-2">You already have a <strong>{existingRequest.status}</strong> request for <strong>{product.name}</strong>.</p>
          {existingRequest.status === 'Pending' && <p className="text-xs text-gray-400 mb-6">Switch to the Admin persona to approve it.</p>}
          <button onClick={onClose} className="w-full py-2.5 rounded-lg text-white font-medium" style={{ backgroundColor: DataMarket_BLUE }}>OK</button>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: '#E8F0F7' }}>
            <CheckCircle2 className="h-8 w-8 text-emerald-500" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Request Submitted</h3>
          <p className="text-gray-500 text-sm mb-2">Your access request for <strong>{product.name}</strong> is pending approval.</p>
          <p className="text-xs text-gray-400 mb-6">Switch to the <strong>Admin persona</strong> to see it in the approval queue.</p>
          <button onClick={onClose} className="w-full py-2.5 rounded-lg text-white font-medium" style={{ backgroundColor: DataMarket_BLUE }}>
            Done
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl">
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
          <h3 className="text-lg font-bold text-gray-900">Submit Access Request</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div className="bg-blue-50 rounded-lg px-4 py-3 text-sm text-blue-800">
            Requesting access to: <strong>{product.name}</strong>
          </div>
          <p className="text-xs text-gray-500">Required fields marked with *</p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Requesting Name *</label>
            <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Requesting Team *</label>
            <input type="text" value={form.team} onChange={e => setForm({ ...form, team: e.target.value })}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Request Reason *</label>
            <textarea rows={3} placeholder="Describe why you need access..." value={form.reason}
              onChange={e => setForm({ ...form, reason: e.target.value })}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
          </div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" checked={form.agreed} onChange={e => setForm({ ...form, agreed: e.target.checked })} className="mt-0.5" />
            <span className="text-xs text-gray-500">
              By submitting, you acknowledge that access to this data is governed by the Your Organization Data Governance Policy and will be used only for authorized purposes.
            </span>
          </label>
        </div>
        <div className="px-6 pb-6 flex gap-3">
          <button onClick={onClose} className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
          <button
            onClick={() => { if (form.name && form.team && form.reason && form.agreed) { submitRequest(product, form); setSubmitted(true) } }}
            disabled={!form.name || !form.team || !form.reason || !form.agreed}
            className="flex-1 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style={{ backgroundColor: DataMarket_BLUE }}
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  )
}

export function DataMarketProductDetailPage({ product, onBack, onNavigate }) {
  const [showModal, setShowModal] = useState(false)
  const [ucDescription, setUcDescription] = useState('')
  const [descExpanded, setDescExpanded] = useState(false)
  const { getProductAccessState, isAdmin, revokeRequest, refreshRequests } = usePersona()
  const { databricksHost } = useAppConfig()
  const [copied, setCopied] = useState(false)
  const Icon = typeIcons[product.type] || BarChart3
  const productRef = product.product_ref || product.id
  const accessState = getProductAccessState(productRef)
  const accessGranted = accessState.canQuery

  // Strip markdown syntax for plain-text display
  const stripMarkdown = (text) => (text || '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/^#+\s+/gm, '')
    .replace(/^[\*\-]\s+/gm, '• ')
    .trim()

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Back + admin Edit */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        {isAdmin && onNavigate && (
          <button
            onClick={() => onNavigate('register', { editProduct: product })}
            className="flex items-center gap-2 text-sm font-medium text-white px-4 py-2 rounded-lg"
            style={{ backgroundColor: DataMarket_BLUE }}
          >
            <Edit3 className="h-4 w-4" /> Edit Product
          </button>
        )}
      </div>

      <div className="flex gap-8 flex-col lg:flex-row">
        {/* Main */}
        <div className="flex-1 min-w-0">
          <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8">
            <div className="flex items-start gap-4 mb-5">
              <div className="w-14 h-14 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: '#E8F0F7' }}>
                <Icon className="h-7 w-7" style={{ color: DataMarket_BLUE }} />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-2xl font-bold text-gray-900 leading-tight">{product.name}</h1>
                  {product.sourceType === 'Power BI' && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200 flex items-center gap-1">
                      📊 Power BI
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {product.tags.map(tag => (
                    <span key={tag} className={`text-xs px-2.5 py-1 rounded-full font-medium ${tagColors[tag] || 'bg-gray-100 text-gray-700'}`}>{tag}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-1">
              <p className={`text-gray-600 leading-relaxed text-sm ${!descExpanded ? 'line-clamp-3' : ''}`}>
                {stripMarkdown(ucDescription || product.description)}
              </p>
              {(ucDescription || product.description || '').length > 180 && (
                <button
                  onClick={() => setDescExpanded(v => !v)}
                  className="text-xs font-medium mt-1"
                  style={{ color: DataMarket_BLUE }}
                >
                  {descExpanded ? 'Show less' : 'Show more'}
                </button>
              )}
            </div>

            <div className="mt-6 flex gap-3 flex-wrap items-center">
              <button onClick={onBack} className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2">
                <ArrowLeft className="h-4 w-4" /> Back
              </button>

              {accessState.state === 'granted' ? (
                <span className="flex items-center gap-2 px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm font-medium text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" /> Access Granted
                </span>
              ) : accessState.state === 'admin' ? (
                <span className="flex items-center gap-2 px-4 py-2 bg-purple-50 border border-purple-200 rounded-lg text-sm font-medium text-purple-700">
                  <ShieldCheck className="h-4 w-4" /> Admin Access
                </span>
              ) : accessState.state === 'revoked' ? (
                <span className="flex items-center gap-2 px-4 py-2 bg-orange-50 border border-orange-200 rounded-lg text-sm font-medium text-orange-700">
                  <XCircle className="h-4 w-4" /> Access Revoked
                </span>
              ) : accessState.state === 'pending' ? (
                <span className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm font-medium text-amber-700">
                  <Clock className="h-4 w-4" /> Request Pending
                </span>
              ) : (
                <button
                  onClick={() => setShowModal(true)}
                  className="px-6 py-2 rounded-lg text-sm font-medium text-white flex items-center gap-2"
                  style={{ backgroundColor: DataMarket_BLUE }}
                >
                  <Lock className="h-4 w-4" /> Request Access
                </button>
              )}

              {accessState.state === 'revoked' && (
                <button
                  onClick={() => setShowModal(true)}
                  className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Request Again
                </button>
              )}

              {/* Query shortcuts — show for anyone with access on UC-backed tables */}
              {accessGranted && product.ucFullName && (() => {
                const parts = (product.ucFullName || product.uc_full_name || '').split('.')
                const fullName = parts.join('.')
                const explorerUrl = databricksHost
                  ? `${databricksHost}/explore/data/${parts.join('/')}`
                  : null
                const starterQuery = `SELECT *\nFROM ${fullName}\nLIMIT 100`
                return (
                  <>
                    {explorerUrl && (
                      <a href={explorerUrl} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors">
                        <ExternalLink className="h-4 w-4" /> Explore in UC
                      </a>
                    )}
                    <button
                      onClick={() => navigator.clipboard.writeText(starterQuery).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${copied ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'}`}
                    >
                      {copied ? <><Check className="h-4 w-4" /> Copied!</> : <><ClipboardList className="h-4 w-4" /> Copy SQL</>}
                    </button>
                  </>
                )
              })()}

              {accessGranted && product.productUrl && (
                <a
                  href={product.productUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  {typeOpenLabel[product.type] || 'Open Product'}
                </a>
              )}

              {accessGranted && product.reportUrl && (
                <a
                  href={product.reportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-lg text-sm font-medium text-yellow-800 hover:bg-yellow-100 flex items-center gap-2"
                >
                  <span>📊</span> View in Power BI
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Properties Panel */}
        <div className="lg:w-72 shrink-0">
          <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-5">
            <h3 className="font-semibold text-gray-900">Properties</h3>

            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                  <Database className="h-4 w-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Data Source Type</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">{product.type}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                  <span className="text-sm">{product.sourceType === 'Power BI' ? '📊' : '⚡'}</span>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Platform</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">{product.sourceType || 'Databricks'}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                  <Tag className="h-4 w-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Tags</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {product.tags.map(tag => (
                      <span key={tag} className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${tagColors[tag] || 'bg-gray-100 text-gray-700'}`}>{tag}</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                  <RefreshCw className="h-4 w-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Refresh Frequency</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">{product.refreshFrequency}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                  <User className="h-4 w-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Data Source Owner</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">{product.owner}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                  <Calendar className="h-4 w-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Last Updated</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">{product.lastUpdated || '02/11/2025'}</p>
                </div>
              </div>

              {product.productUrl && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                    <ExternalLink className="h-4 w-4 text-gray-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Product URL</p>
                    {accessGranted ? (
                      <a href={product.productUrl} target="_blank" rel="noopener noreferrer"
                        className="text-xs font-medium text-blue-600 hover:underline mt-0.5 break-all block">
                        {product.productUrl}
                      </a>
                    ) : (
                      <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                        <Lock className="h-3 w-3" /> Visible after access approved
                      </p>
                    )}
                  </div>
                </div>
              )}

              {product.reportUrl && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-yellow-50 flex items-center justify-center shrink-0">
                    <span className="text-sm">📊</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Power BI Report</p>
                    {accessGranted ? (
                      <a href={product.reportUrl} target="_blank" rel="noopener noreferrer"
                        className="text-xs font-medium text-yellow-700 hover:underline mt-0.5 break-all block">
                        Open Report ↗
                      </a>
                    ) : (
                      <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                        <Lock className="h-3 w-3" /> Available after access approved
                      </p>
                    )}
                  </div>
                </div>
              )}

            </div>
          </div>
        </div>
      </div>

      <DataSchemaPanel
        product={product}
        accessGranted={accessGranted}
        onRequestAccess={() => setShowModal(true)}
        onTableComment={setUcDescription}
      />

      {isAdmin && (
        <ProductGrantedAccessPanel
          productRef={productRef}
          revokeRequest={revokeRequest}
          onRevoked={refreshRequests}
        />
      )}

      {showModal && <AccessRequestModal product={product} onClose={() => setShowModal(false)} />}
    </div>
  )
}

function ProductGrantedAccessPanel({ productRef, revokeRequest, onRevoked }) {
  const [grants, setGrants] = useState([])
  const [loading, setLoading] = useState(true)
  const [revoking, setRevoking] = useState(null)
  const [revokeReason, setRevokeReason] = useState('')

  const loadGrants = useCallback(() => {
    setLoading(true)
    fetch(`/api/portal/products/${encodeURIComponent(productRef)}/granted-access`)
      .then(r => r.json())
      .then(rows => { if (Array.isArray(rows)) setGrants(rows) })
      .catch(() => setGrants([]))
      .finally(() => setLoading(false))
  }, [productRef])

  useEffect(() => { loadGrants() }, [loadGrants])

  const handleRevoke = async (requestRef) => {
    setRevoking(requestRef)
    await revokeRequest(requestRef, revokeReason || 'Access revoked by administrator')
    setRevokeReason('')
    setRevoking(null)
    loadGrants()
    onRevoked?.()
  }

  return (
    <div className="mt-8 bg-white rounded-2xl border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-1">
        <ShieldCheck className="h-5 w-5" style={{ color: DataMarket_BLUE }} />
        <h3 className="font-semibold text-gray-900">Granted Access</h3>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Users with approved access to this product. Revoking issues a Unity Catalog REVOKE and updates their portal status.
      </p>

      {loading && <p className="text-sm text-gray-400 py-4 text-center">Loading...</p>}
      {!loading && grants.length === 0 && (
        <p className="text-sm text-gray-400 py-4 text-center border border-dashed border-gray-200 rounded-lg">
          No approved access grants for this product yet.
        </p>
      )}
      {!loading && grants.length > 0 && (
        <div className="space-y-3">
          {grants.map(g => (
            <div key={g.request_ref} className="flex items-center justify-between gap-4 p-3 rounded-xl border border-gray-100 bg-gray-50/50">
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900">{g.requester_name || g.requester_email}</p>
                <p className="text-xs text-gray-500">{g.requester_email}</p>
                {g.resolved_at && (
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    Approved {new Date(g.resolved_at).toLocaleDateString()}
                    {g.expires_at ? ` · expires ${new Date(g.expires_at).toLocaleDateString()}` : ''}
                  </p>
                )}
              </div>
              {revoking === g.request_ref ? (
                <div className="flex items-center gap-2 shrink-0">
                  <input
                    type="text"
                    placeholder="Reason (optional)"
                    value={revokeReason}
                    onChange={e => setRevokeReason(e.target.value)}
                    className="px-2 py-1 border border-gray-200 rounded text-xs w-36 focus:outline-none focus:ring-1 focus:ring-orange-300"
                  />
                  <button
                    onClick={() => handleRevoke(g.request_ref)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-orange-600 hover:bg-orange-700"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => { setRevoking(null); setRevokeReason('') }}
                    className="px-2 py-1.5 rounded-lg text-xs text-gray-500 hover:bg-gray-100"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setRevoking(g.request_ref)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-orange-700 border border-orange-200 hover:bg-orange-50 shrink-0"
                >
                  <XCircle className="h-3.5 w-3.5" /> Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

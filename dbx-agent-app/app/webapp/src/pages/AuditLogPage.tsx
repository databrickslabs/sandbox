import { useState, useEffect, useCallback } from 'react'
import { registryApi } from '../api/registry'
import type { AuditLogEntry } from '../types'
import './AuditLogPage.css'

const ACTION_OPTIONS = ['', 'create', 'update', 'delete', 'crawl', 'clear', 'generate', 'add_item', 'remove_item']
const RESOURCE_TYPE_OPTIONS = ['', 'agent', 'collection', 'supervisor', 'catalog_asset', 'workspace_asset', 'lineage']

function formatRelativeTime(isoStr: string): string {
  const date = new Date(isoStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return 'just now'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 30) return `${diffDay}d ago`
  return date.toLocaleDateString()
}

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  // Filters
  const [actionFilter, setActionFilter] = useState('')
  const [resourceTypeFilter, setResourceTypeFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')

  const fetchEntries = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: 50 }
      if (actionFilter) params.action = actionFilter
      if (resourceTypeFilter) params.resource_type = resourceTypeFilter
      if (userFilter) params.user_email = userFilter
      const data = await registryApi.getAuditLog(params)
      setEntries(data.items)
      setTotalPages(data.total_pages)
      setTotal(data.total)
    } catch {
      setEntries([])
    } finally {
      setLoading(false)
    }
  }, [page, actionFilter, resourceTypeFilter, userFilter])

  useEffect(() => {
    fetchEntries()
  }, [fetchEntries])

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [actionFilter, resourceTypeFilter, userFilter])

  return (
    <div className="audit-log-page">
      <div className="audit-log-page-header">
        <div>
          <h2>Audit Log</h2>
          <p className="audit-log-subtitle">
            Track who did what, when, and to which resource
          </p>
        </div>
      </div>

      <div className="audit-log-filters">
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        >
          <option value="">All actions</option>
          {ACTION_OPTIONS.filter(Boolean).map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>

        <select
          value={resourceTypeFilter}
          onChange={(e) => setResourceTypeFilter(e.target.value)}
        >
          <option value="">All resource types</option>
          {RESOURCE_TYPE_OPTIONS.filter(Boolean).map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Filter by user email..."
          value={userFilter}
          onChange={(e) => setUserFilter(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="audit-log-loading">Loading audit log...</div>
      ) : entries.length === 0 ? (
        <div className="audit-log-empty">
          <p>No audit log entries found</p>
          <p>Entries will appear here as mutating actions are performed</p>
        </div>
      ) : (
        <>
          <div className="audit-log-table-container">
            <table className="audit-log-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Resource Type</th>
                  <th>Resource</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td className="audit-log-timestamp" title={entry.timestamp}>
                      {formatRelativeTime(entry.timestamp)}
                    </td>
                    <td>{entry.user_email}</td>
                    <td>
                      <span className={`audit-action-badge ${entry.action}`}>
                        {entry.action}
                      </span>
                    </td>
                    <td>{entry.resource_type}</td>
                    <td className="audit-log-resource" title={entry.resource_name || entry.resource_id || ''}>
                      {entry.resource_name || entry.resource_id || '-'}
                    </td>
                    <td>{entry.ip_address || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="audit-log-pagination">
            <span>{total} entries total</span>
            <div className="audit-log-pagination-controls">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

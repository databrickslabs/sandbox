import React, { useState } from 'react'
import { Search, BarChart3, FileText, Database, BookmarkCheck, ExternalLink, ClipboardList, Check } from 'lucide-react'
import { tagColors, statusConfig, DataMarket_BLUE } from './adminConstants'

function CopyQueryButton({ query }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(query).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }) }}
      title={`Copy: ${query}`}
      className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors whitespace-nowrap ${copied ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
    >
      {copied ? <><Check className="h-3 w-3" /> Copied</> : <><ClipboardList className="h-3 w-3" /> Copy SQL</>}
    </button>
  )
}

export function AnalystMyDataView({ filteredAnalyst, activeTab, search, setSearch, onOpenProduct, databricksHost }) {
  return (
    <>
      <div className="relative mb-4 max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input type="text" placeholder="Search" value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Name</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Tags</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Type</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Frequency</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Owner</th>
                <th className="text-center py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Status</th>
                {(activeTab === 'Data Product' || activeTab === 'My Data') && (
                  <th className="text-center py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Query</th>
                )}
              </tr>
            </thead>
            <tbody>
              {filteredAnalyst
                .filter(item => (activeTab === 'Data Product' || activeTab === 'My Data') ? item.status === 'Approved' : true)
                .map(item => {
                  const Icon = { Dashboard: BarChart3, Report: FileText, Dataset: Database }[item.type] || Database
                  const ucFullName = item.uc_full_name
                  const ucParts = ucFullName ? ucFullName.split('.') : []
                  const ucExplorerUrl = ucFullName && databricksHost
                    ? `${databricksHost}/explore/data/${ucParts.join('/')}`
                    : null
                  const starterQuery = ucFullName
                    ? `SELECT *\nFROM ${ucFullName}\nLIMIT 100`
                    : null
                  return (
                    <tr key={item.product_ref || item.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="py-3 px-4">
                        <button onClick={() => onOpenProduct(item)} className="flex items-center gap-2.5 hover:text-blue-700 transition-colors text-left">
                          <div className="w-7 h-7 rounded flex items-center justify-center shrink-0" style={{ backgroundColor: '#E8F0F7' }}>
                            <Icon className="h-3.5 w-3.5" style={{ color: DataMarket_BLUE }} />
                          </div>
                          <span className="font-medium text-gray-900 text-xs">{item.name}</span>
                        </button>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {(item.tags || []).map(tag => (
                            <span key={tag} className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${tagColors[tag] || 'bg-gray-100 text-gray-700'}`}>{tag}</span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-xs text-gray-600">{item.type}</td>
                      <td className="py-3 px-4 text-xs text-gray-600">{item.refreshFrequency}</td>
                      <td className="py-3 px-4 text-xs text-gray-600">{item.owner}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusConfig[item.status] || 'bg-gray-100 text-gray-700'}`}>
                          {item.status}
                        </span>
                      </td>
                      {(activeTab === 'Data Product' || activeTab === 'My Data') && (
                        <td className="py-3 px-4">
                          {item.status === 'Approved' && ucFullName ? (
                            <div className="flex items-center gap-1 justify-center">
                              {ucExplorerUrl && (
                                <a href={ucExplorerUrl} target="_blank" rel="noopener noreferrer"
                                  title="Open in UC Data Explorer"
                                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors whitespace-nowrap">
                                  <ExternalLink className="h-3 w-3" /> Explore
                                </a>
                              )}
                              {starterQuery && (
                                <CopyQueryButton query={starterQuery} />
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-gray-300">—</span>
                          )}
                        </td>
                      )}
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
        {filteredAnalyst.filter(item => (activeTab === 'Data Product' || activeTab === 'My Data') ? item.status === 'Approved' : true).length === 0 && (
          <div className="py-16 text-center text-gray-400">
            <BookmarkCheck className="h-10 w-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No items found.</p>
          </div>
        )}
      </div>
    </>
  )
}

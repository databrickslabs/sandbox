import { DiscoverFilters } from '../../types'
import './FilterBar.css'

interface FilterBarProps {
  filters: DiscoverFilters
  onFiltersChange: (filters: Partial<DiscoverFilters>) => void
  owners: string[]
  allTags: string[]
}

export default function FilterBar({ filters, onFiltersChange, owners, allTags }: FilterBarProps) {
  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label>Type:</label>
        <select
          value={filters.type}
          onChange={(e) => onFiltersChange({ type: e.target.value as DiscoverFilters['type'] })}
        >
          <option value="all">All</option>
          <optgroup label="Catalog">
            <option value="table">Tables</option>
            <option value="view">Views</option>
            <option value="function">Functions</option>
            <option value="model">Models</option>
            <option value="volume">Volumes</option>
          </optgroup>
          <optgroup label="Workspace">
            <option value="notebook">Notebooks</option>
            <option value="job">Jobs</option>
            <option value="dashboard">Dashboards</option>
            <option value="pipeline">Pipelines</option>
            <option value="cluster">Clusters</option>
            <option value="experiment">Experiments</option>
          </optgroup>
          <optgroup label="MCP">
            <option value="app">Apps</option>
            <option value="server">Servers</option>
            <option value="tool">Tools</option>
          </optgroup>
        </select>
      </div>

      <div className="filter-group">
        <label>Owner:</label>
        <select
          value={filters.owner}
          onChange={(e) => onFiltersChange({ owner: e.target.value })}
        >
          <option value="">All Owners</option>
          {owners.map((owner) => (
            <option key={owner} value={owner}>
              {owner}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label>Tags:</label>
        <select
          multiple
          value={filters.tags}
          onChange={(e) => {
            const selected = Array.from(e.target.selectedOptions, option => option.value)
            onFiltersChange({ tags: selected })
          }}
          size={3}
        >
          {allTags.map((tag) => (
            <option key={tag} value={tag}>
              {tag}
            </option>
          ))}
        </select>
      </div>

      {(filters.owner || filters.tags.length > 0 || filters.type !== 'all') && (
        <button
          className="filter-clear"
          onClick={() => onFiltersChange({ owner: '', tags: [], type: 'all' })}
        >
          Clear Filters
        </button>
      )}
    </div>
  )
}

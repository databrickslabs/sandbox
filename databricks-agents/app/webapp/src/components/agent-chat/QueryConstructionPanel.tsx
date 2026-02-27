import { SlotFillingInfo } from '../../types'
import './QueryConstructionPanel.css'

interface QueryConstructionPanelProps {
  slotFilling: SlotFillingInfo | null
}

export default function QueryConstructionPanel({ slotFilling }: QueryConstructionPanelProps) {
  return (
    <div className="query-panel">
      <h3 className="query-panel-title">Query Construction</h3>
      <p className="query-panel-subtitle">NL &rarr; SQL Slot Filling</p>

      {slotFilling ? (
        <div>
          {/* Entities Detected */}
          {slotFilling.slots.entities.length > 0 && (
            <div className="query-section">
              <span className="query-section-label">Entities Detected</span>
              <div className="query-chips">
                {slotFilling.slots.entities.map((entity, idx) => (
                  <span key={idx} className="query-chip query-chip-primary">{entity}</span>
                ))}
              </div>
            </div>
          )}

          {/* Search Terms */}
          {slotFilling.slots.searchTerms.length > 0 && (
            <div className="query-section">
              <span className="query-section-label">Search Terms</span>
              <div className="query-chips">
                {slotFilling.slots.searchTerms.map((term, idx) => (
                  <span key={idx} className="query-chip">{term}</span>
                ))}
              </div>
            </div>
          )}

          {/* NL to SQL Mappings */}
          {slotFilling.nlToSql.length > 0 && (
            <div className="query-section">
              <span className="query-section-label">NL &rarr; SQL Clauses</span>
              {slotFilling.nlToSql.map((mapping, idx) => (
                <div key={idx} className="nl-sql-mapping">
                  <div className="mapping-header">
                    <span className="mapping-type-badge">{mapping.type}</span>
                    <span className="mapping-nl">{mapping.naturalLanguage}</span>
                  </div>
                  <div className="mapping-arrow">&darr;</div>
                  <code className="mapping-sql">{mapping.sqlClause}</code>
                  <div className="mapping-confidence">
                    <div className="confidence-bar">
                      <div
                        className="confidence-fill"
                        style={{ width: `${mapping.confidence * 100}%` }}
                      />
                    </div>
                    <span className="confidence-label">
                      {(mapping.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Elasticsearch Query */}
          <details className="query-details">
            <summary className="query-details-summary">Elasticsearch Query</summary>
            <pre className="query-json">
              {JSON.stringify(slotFilling.elasticQuery, null, 2)}
            </pre>
          </details>
        </div>
      ) : (
        <p className="query-panel-empty">Send a message to see query construction...</p>
      )}
    </div>
  )
}

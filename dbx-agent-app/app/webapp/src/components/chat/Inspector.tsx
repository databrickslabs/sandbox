import { TraceEvent, Span } from '../../types'
import Badge from '../common/Badge'
import './Inspector.css'

interface InspectorProps {
  selectedEvent: TraceEvent | null
  spans: Span[]
}

export default function Inspector({ selectedEvent, spans }: InspectorProps) {
  if (!selectedEvent) {
    return (
      <div className="inspector">
        <div className="inspector-empty">
          <p>Select an event to inspect</p>
        </div>
      </div>
    )
  }

  return (
    <div className="inspector">
      <div className="inspector-header">
        <h3>Inspector</h3>
        <Badge>{selectedEvent.type}</Badge>
      </div>

      <div className="inspector-content">
        <section className="inspector-section">
          <h4>Event Details</h4>
          <div className="inspector-field">
            <label>Type:</label>
            <span>{selectedEvent.type}</span>
          </div>
          <div className="inspector-field">
            <label>Timestamp:</label>
            <span>{new Date(selectedEvent.timestamp).toLocaleString()}</span>
          </div>
          <div className="inspector-field">
            <label>Trace ID:</label>
            <code>{selectedEvent.trace_id}</code>
          </div>
        </section>

        <section className="inspector-section">
          <h4>Event Data</h4>
          <pre className="inspector-json">
            {JSON.stringify(selectedEvent.data, null, 2)}
          </pre>
        </section>

        {spans.length > 0 && (
          <section className="inspector-section">
            <h4>MLflow Spans ({spans.length})</h4>
            {spans.map((span) => (
              <div key={span.id} className="span-card">
                <div className="span-header">
                  <strong>{span.name}</strong>
                  <Badge variant={span.status === 'OK' ? 'success' : 'danger'}>
                    {span.status}
                  </Badge>
                </div>
                <div className="span-meta">
                  <span>
                    Duration: {Math.round(span.end_time - span.start_time)}ms
                  </span>
                </div>
                {Object.keys(span.attributes).length > 0 && (
                  <details className="span-attributes">
                    <summary>Attributes</summary>
                    <pre>{JSON.stringify(span.attributes, null, 2)}</pre>
                  </details>
                )}
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}

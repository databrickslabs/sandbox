import { TraceEvent } from '../../types'
import './TraceTimeline.css'

interface TraceTimelineProps {
  events: TraceEvent[]
  selectedEvent: TraceEvent | null
  onSelectEvent: (event: TraceEvent) => void
}

const eventIcons: Record<TraceEvent['type'], string> = {
  'request.started': '🚀',
  'tool.called': '🔧',
  'tool.output': '✅',
  'response.delta': '📝',
  'response.done': '🏁'
}

const eventColors: Record<TraceEvent['type'], string> = {
  'request.started': 'blue',
  'tool.called': 'purple',
  'tool.output': 'green',
  'response.delta': 'gray',
  'response.done': 'orange'
}

export default function TraceTimeline({ events, selectedEvent, onSelectEvent }: TraceTimelineProps) {
  return (
    <div className="trace-timeline">
      <div className="timeline-header">
        <h3>Trace Timeline</h3>
        <span className="event-count">{events.length} events</span>
      </div>

      <div className="timeline-events">
        {events.length === 0 ? (
          <div className="timeline-empty">
            <p>Send a message to see trace events...</p>
          </div>
        ) : (
          events.map((event) => {
            const icon = eventIcons[event.type]
            const color = eventColors[event.type]
            const isSelected = selectedEvent?.id === event.id

            return (
              <button
                key={event.id}
                type="button"
                className={`trace-event ${color} ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectEvent(event)}
              >
                <div className="event-icon">{icon}</div>
                <div className="event-content">
                  <div className="event-type">{event.type}</div>
                  <div className="event-time">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </div>
                  {event.data.tool_name && (
                    <div className="event-detail">{event.data.tool_name}</div>
                  )}
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}

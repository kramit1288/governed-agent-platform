import type { RunTimeline } from "../lib/api";

type TraceTimelineProps = {
  timeline: RunTimeline;
};

export function TraceTimeline({ timeline }: TraceTimelineProps) {
  return (
    <section className="panel">
      <div className="page-header">
        <div>
          <p className="eyebrow">Trace</p>
          <h3>Timeline</h3>
        </div>
        <span className="status-badge status-progress">{timeline.event_count} events</span>
      </div>
      <div className="timeline">
        {timeline.events.map((event) => (
          <article className="timeline-entry" key={`${event.sequence}-${event.event_type}`}>
            <div className="timeline-entry-header">
              <div>
                <div className="timeline-seq">#{event.sequence}</div>
                <strong>{event.title}</strong>
              </div>
              <div className="timeline-seq">
                {new Date(event.timestamp).toLocaleString()}
              </div>
            </div>
            {event.payload ? (
              <pre className="payload">{JSON.stringify(event.payload, null, 2)}</pre>
            ) : (
              <p className="panel-muted">No payload recorded.</p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

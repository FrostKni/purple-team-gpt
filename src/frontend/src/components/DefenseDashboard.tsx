import React from 'react';

interface Event {
  agent: 'red' | 'blue';
  event_type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

interface DefenseDashboardProps {
  status: string;
  events: Event[];
  steps: number;
  findings: number;
  detections: number;
}

const DefenseDashboard: React.FC<DefenseDashboardProps> = ({
  status,
  events,
  steps,
  findings,
  detections,
}) => {
  const defenseEvents = events.filter(e => e.agent === 'blue');

  return (
    <div className="card defense-card">
      <h2>Blue Agent - Defense Dashboard</h2>
      
      <div className="metric-grid" style={{ marginBottom: '16px' }}>
        <div className="metric-item">
          <div className="metric-value">{steps}</div>
          <div className="metric-label">Steps</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{detections}</div>
          <div className="metric-label">Detections</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{findings}</div>
          <div className="metric-label">Findings</div>
        </div>
        <div className="metric-item">
          <div className="metric-value" style={{ color: status === 'running' ? '#28a745' : '#aaa' }}>
            {status === 'running' ? 'Active' : 'Idle'}
          </div>
          <div className="metric-label">Status</div>
        </div>
      </div>

      <h3>Recent Events</h3>
      <div className="event-list">
        {defenseEvents.length === 0 ? (
          <div className="empty-state">No defense events yet</div>
        ) : (
          defenseEvents.slice(-20).reverse().map((event, i) => (
            <div key={i} className="event-item blue">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{event.event_type}</strong>
                <span className="timestamp">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
              {typeof event.data.message === 'string' && (
                <p style={{ marginTop: '4px', color: '#aaa' }}>
                  {event.data.message}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default DefenseDashboard;
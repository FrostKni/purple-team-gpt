import React from 'react';

interface Event {
  agent: 'red' | 'blue';
  event_type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

interface AttackDashboardProps {
  status: string;
  events: Event[];
  steps: number;
  findings: number;
  toolsUsed: string[];
}

const AttackDashboard: React.FC<AttackDashboardProps> = ({
  status: _status,
  events,
  steps,
  findings,
  toolsUsed,
}) => {
  const attackEvents = events.filter(e => e.agent === 'red');

  return (
    <div className="card attack-card">
      <h2>Red Agent - Attack Dashboard</h2>
      
      <div className="metric-grid" style={{ marginBottom: '16px' }}>
        <div className="metric-item">
          <div className="metric-value">{steps}</div>
          <div className="metric-label">Steps</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{findings}</div>
          <div className="metric-label">Findings</div>
        </div>
      </div>

      {toolsUsed.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <h3>Tools Used</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {toolsUsed.map((tool, i) => (
              <span
                key={i}
                style={{
                  background: '#e94560',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '0.8rem',
                }}
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      )}

      <h3>Recent Events</h3>
      <div className="event-list">
        {attackEvents.length === 0 ? (
          <div className="empty-state">No attack events yet</div>
        ) : (
          attackEvents.slice(-20).reverse().map((event, i) => (
            <div key={i} className="event-item red">
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

export default AttackDashboard;
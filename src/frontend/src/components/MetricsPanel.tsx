import React from 'react';

interface MetricsPanelProps {
  sessionId: string | null;
  target: string;
  status: string;
  duration: string;
  totalFindings: number;
  totalEvents: number;
  redSteps: number;
  blueSteps: number;
  redFindings: number;
  blueFindings: number;
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({
  sessionId,
  target,
  status,
  duration,
  totalFindings,
  totalEvents,
  redSteps,
  blueSteps,
  redFindings,
  blueFindings,
}) => {
  return (
    <div className="card">
      <h2>Session Metrics</h2>
      
      {!sessionId ? (
        <div className="empty-state">Select a session to view metrics</div>
      ) : (
        <>
          <div style={{ marginBottom: '16px' }}>
            <p><strong>Target:</strong> {target || 'N/A'}</p>
            <p>
              <strong>Status:</strong>{' '}
              <span className={`status-badge status-${status}`}>{status}</span>
            </p>
            <p><strong>Duration:</strong> {duration || 'N/A'}</p>
          </div>

          <div className="metric-grid">
            <div className="metric-item">
              <div className="metric-value">{totalFindings}</div>
              <div className="metric-label">Total Findings</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">{totalEvents}</div>
              <div className="metric-label">Total Events</div>
            </div>
            <div className="metric-item" style={{ borderLeft: '3px solid #e94560' }}>
              <div className="metric-value">{redSteps}</div>
              <div className="metric-label">Red Steps</div>
            </div>
            <div className="metric-item" style={{ borderLeft: '3px solid #4db6e9' }}>
              <div className="metric-value">{blueSteps}</div>
              <div className="metric-label">Blue Steps</div>
            </div>
          </div>

          <div style={{ marginTop: '16px' }}>
            <h3>Findings Summary</h3>
            <div style={{ display: 'flex', gap: '20px', marginTop: '8px' }}>
              <div style={{ flex: 1, padding: '12px', background: '#0f3460', borderRadius: '6px', borderLeft: '3px solid #e94560' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{redFindings}</div>
                <div style={{ fontSize: '0.8rem', color: '#e94560' }}>Red Team Findings</div>
              </div>
              <div style={{ flex: 1, padding: '12px', background: '#0f3460', borderRadius: '6px', borderLeft: '3px solid #4db6e9' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{blueFindings}</div>
                <div style={{ fontSize: '0.8rem', color: '#4db6e9' }}>Blue Team Findings</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default MetricsPanel;
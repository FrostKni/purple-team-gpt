import React from 'react';
import { Session } from '../api';

interface SessionListProps {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (session: Session) => void;
  onDelete: (sessionId: string) => void;
  onStart: (sessionId: string) => void;
  onPause: (sessionId: string) => void;
  onResume: (sessionId: string) => void;
  onStop: (sessionId: string) => void;
  loading: boolean;
}

const SessionList: React.FC<SessionListProps> = ({
  sessions,
  selectedId,
  onSelect,
  onDelete,
  onStart,
  onPause,
  onResume,
  onStop,
  loading,
}) => {
  const getStatusBadge = (status: string) => {
    return <span className={`status-badge status-${status}`}>{status}</span>;
  };

  return (
    <div className="card">
      <h2>Sessions ({sessions.length})</h2>
      
      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      ) : sessions.length === 0 ? (
        <div className="empty-state">No sessions yet. Create one to get started.</div>
      ) : (
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {sessions.map((session) => (
            <div
              key={session.id}
              className="session-item"
              style={{
                cursor: 'pointer',
                border: selectedId === session.id ? '2px solid #e94560' : 'none',
              }}
              onClick={() => onSelect(session)}
            >
              <div className="session-info">
                <h4>{session.target}</h4>
                <p>
                  ID: {session.id.slice(0, 8)}... | {getStatusBadge(session.status)}
                </p>
                <p className="timestamp">
                  Created: {session.created_at ? new Date(session.created_at).toLocaleString() : 'N/A'}
                </p>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {session.status === 'pending' && (
                  <button
                    className="btn btn-primary"
                    onClick={(e) => { e.stopPropagation(); onStart(session.id); }}
                  >
                    Start
                  </button>
                )}
                {session.status === 'running' && (
                  <>
                    <button
                      className="btn btn-warning"
                      onClick={(e) => { e.stopPropagation(); onPause(session.id); }}
                    >
                      Pause
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={(e) => { e.stopPropagation(); onStop(session.id); }}
                    >
                      Stop
                    </button>
                  </>
                )}
                {session.status === 'paused' && (
                  <>
                    <button
                      className="btn btn-secondary"
                      onClick={(e) => { e.stopPropagation(); onResume(session.id); }}
                    >
                      Resume
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={(e) => { e.stopPropagation(); onStop(session.id); }}
                    >
                      Stop
                    </button>
                  </>
                )}
                {session.status === 'completed' && (
                  <button
                    className="btn btn-danger"
                    onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SessionList;
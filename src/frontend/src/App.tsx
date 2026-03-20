import React, { useState, useEffect, useCallback } from 'react';
import SessionList from './components/SessionList';
import AttackDashboard from './components/AttackDashboard';
import DefenseDashboard from './components/DefenseDashboard';
import MetricsPanel from './components/MetricsPanel';
import { useWebSocket, WebSocketMessage } from './hooks/useWebSocket';
import {
  Session,
  SessionMetrics,
  listSessions,
  createSession,
  startSession,
  pauseSession,
  resumeSession,
  stopSession,
  deleteSession,
  getSessionMetrics,
  checkHealth,
} from './api';

interface Event {
  agent: 'red' | 'blue';
  event_type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  // New session form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTarget, setNewTarget] = useState('');
  const [newScope, setNewScope] = useState('');

  // Fetch sessions
  const fetchSessions = useCallback(async () => {
    try {
      const response = await listSessions();
      setSessions(response.sessions);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      setError('Failed to fetch sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  // Check backend health
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await checkHealth();
        setBackendStatus('online');
      } catch {
        setBackendStatus('offline');
      }
    };
    checkBackend();
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  // Initial session fetch
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Fetch metrics when session is selected
  useEffect(() => {
    if (selectedSession) {
      getSessionMetrics(selectedSession.id)
        .then(setMetrics)
        .catch(console.error);
    }
  }, [selectedSession]);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'event':
        setEvents((prev) => [
          ...prev,
          {
            agent: message.agent as 'red' | 'blue',
            event_type: message.event_type as string,
            data: message.data as Record<string, unknown>,
            timestamp: message.timestamp as string,
          },
        ]);
        break;
      case 'session_state':
        // Update session state
        if (message.session) {
          setSelectedSession((prev) =>
            prev ? { ...prev, ...(message.session as Partial<Session>) } : null
          );
        }
        break;
      case 'metrics':
        if (message.data) {
          setMetrics(message.data as SessionMetrics);
        }
        break;
      case 'command_result':
        // Refresh session list after commands
        fetchSessions();
        break;
    }
  }, [fetchSessions]);

  // WebSocket connection
  const { isConnected } = useWebSocket(
    selectedSession?.id || null,
    {
      onMessage: handleWebSocketMessage,
      onOpen: () => console.log('WebSocket connected'),
      onClose: () => console.log('WebSocket disconnected'),
    }
  );

  // Session actions
  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTarget.trim()) return;

    try {
      const session = await createSession({ target: newTarget, scope: newScope });
      setSessions((prev) => [...prev, session]);
      setSelectedSession(session);
      setShowCreateForm(false);
      setNewTarget('');
      setNewScope('');
    } catch (err) {
      setError('Failed to create session');
    }
  };

  const handleStartSession = async (sessionId: string) => {
    try {
      await startSession(sessionId);
      setEvents([]); // Clear events for fresh start
      await fetchSessions();
    } catch (err) {
      setError('Failed to start session');
    }
  };

  const handlePauseSession = async (sessionId: string) => {
    try {
      await pauseSession(sessionId);
      await fetchSessions();
    } catch (err) {
      setError('Failed to pause session');
    }
  };

  const handleResumeSession = async (sessionId: string) => {
    try {
      await resumeSession(sessionId);
      await fetchSessions();
    } catch (err) {
      setError('Failed to resume session');
    }
  };

  const handleStopSession = async (sessionId: string) => {
    try {
      await stopSession(sessionId);
      await fetchSessions();
    } catch (err) {
      setError('Failed to stop session');
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      if (selectedSession?.id === sessionId) {
        setSelectedSession(null);
        setEvents([]);
        setMetrics(null);
      }
      await fetchSessions();
    } catch (err) {
      setError('Failed to delete session');
    }
  };

  const handleSelectSession = (session: Session) => {
    setSelectedSession(session);
    setEvents([]); // Clear events when switching sessions
    setMetrics(null);
  };

  return (
    <div className="container">
      <header>
        <h1>Purple Team GPT</h1>
        <div className="connection-status">
          <span
            className={`connection-dot ${backendStatus === 'online' ? 'connected' : 'disconnected'}`}
          />
          <span>Backend: {backendStatus}</span>
          {selectedSession && (
            <>
              <span style={{ margin: '0 10px' }}>|</span>
              <span
                className={`connection-dot ${isConnected ? 'connected' : 'disconnected'}`}
              />
              <span>WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</span>
            </>
          )}
        </div>
      </header>

      {error && (
        <div style={{ background: '#dc3545', padding: '12px', borderRadius: '4px', marginBottom: '16px' }}>
          {error}
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: '12px', background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="grid">
        <div>
          <SessionList
            sessions={sessions}
            selectedId={selectedSession?.id || null}
            onSelect={handleSelectSession}
            onDelete={handleDeleteSession}
            onStart={handleStartSession}
            onPause={handlePauseSession}
            onResume={handleResumeSession}
            onStop={handleStopSession}
            loading={loading}
          />

          <div className="card">
            <h2>Create New Session</h2>
            {showCreateForm ? (
              <form onSubmit={handleCreateSession}>
                <div className="form-group">
                  <label>Target *</label>
                  <input
                    type="text"
                    value={newTarget}
                    onChange={(e) => setNewTarget(e.target.value)}
                    placeholder="e.g., 192.168.1.0/24 or example.com"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Scope (Optional)</label>
                  <textarea
                    value={newScope}
                    onChange={(e) => setNewScope(e.target.value)}
                    placeholder="Scope restrictions, allowed ports, etc."
                    rows={3}
                  />
                </div>
                <div>
                  <button type="submit" className="btn btn-primary">Create</button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setShowCreateForm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button
                className="btn btn-primary"
                onClick={() => setShowCreateForm(true)}
              >
                + New Session
              </button>
            )}
          </div>

          <MetricsPanel
            sessionId={selectedSession?.id || null}
            target={selectedSession?.target || ''}
            status={selectedSession?.status || ''}
            duration={metrics?.duration || ''}
            totalFindings={metrics?.total_findings || 0}
            totalEvents={metrics?.total_events || 0}
            redSteps={metrics?.red_agent?.steps || 0}
            blueSteps={metrics?.blue_agent?.steps || 0}
            redFindings={metrics?.red_agent?.findings || 0}
            blueFindings={metrics?.blue_agent?.findings || 0}
          />
        </div>

        <div>
          <AttackDashboard
            status={selectedSession?.status || ''}
            events={events}
            steps={metrics?.red_agent?.steps || 0}
            findings={metrics?.red_agent?.findings || 0}
            toolsUsed={metrics?.red_agent?.tools_used || []}
          />

          <DefenseDashboard
            status={selectedSession?.status || ''}
            events={events}
            steps={metrics?.blue_agent?.steps || 0}
            findings={metrics?.blue_agent?.findings || 0}
            detections={metrics?.blue_agent?.detections || 0}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
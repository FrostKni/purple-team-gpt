// API types
export interface Session {
  id: string;
  target: string;
  scope: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'error';
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
}

export interface SessionMetrics {
  session_id: string;
  target: string;
  scope: string;
  status: string;
  duration: string;
  red_agent: {
    steps: number;
    findings: number;
    tools_used: string[];
  };
  blue_agent: {
    steps: number;
    findings: number;
    detections: number;
  };
  total_findings: number;
  total_events: number;
}

export interface CreateSessionRequest {
  target: string;
  scope?: string;
  metadata?: Record<string, unknown>;
}

const API_BASE = '/api/v1/sessions';

export async function listSessions(status?: string): Promise<SessionListResponse> {
  const url = status ? `${API_BASE}/?status=${status}` : API_BASE;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to list sessions: ${res.statusText}`);
  return res.json();
}

export async function getSession(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to get session: ${res.statusText}`);
  return res.json();
}

export async function createSession(data: CreateSessionRequest): Promise<Session> {
  const res = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
  return res.json();
}

export async function startSession(sessionId: string): Promise<{ message: string; session_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/${sessionId}/start`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to start session: ${res.statusText}`);
  return res.json();
}

export async function pauseSession(sessionId: string): Promise<{ message: string; session_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/${sessionId}/pause`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to pause session: ${res.statusText}`);
  return res.json();
}

export async function resumeSession(sessionId: string): Promise<{ message: string; session_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/${sessionId}/resume`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to resume session: ${res.statusText}`);
  return res.json();
}

export async function stopSession(sessionId: string): Promise<{ message: string; session_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/${sessionId}/stop`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to stop session: ${res.statusText}`);
  return res.json();
}

export async function getSessionMetrics(sessionId: string): Promise<SessionMetrics> {
  const res = await fetch(`${API_BASE}/${sessionId}/metrics`);
  if (!res.ok) throw new Error(`Failed to get metrics: ${res.statusText}`);
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/${sessionId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete session: ${res.statusText}`);
}

export async function checkHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch('/health');
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}
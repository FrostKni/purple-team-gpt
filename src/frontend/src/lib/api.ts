const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Session {
  id: string;
  target: string;
  scope: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'error';
  created_at: string;
  completed_at?: string;
}

export interface Finding {
  title: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low' | 'Info';
  description: string;
  evidence: string;
  recommendation: string;
  tool: string;
  timestamp: string;
}

export interface AgentStep {
  step_num: number;
  action: string;
  description: string;
  result?: string;
  success: boolean;
  timestamp: string;
}

export interface Metrics {
  session_id: string;
  target: string;
  status: string;
  duration: string;
  red_findings: number;
  blue_findings: number;
  red_steps: number;
  blue_steps: number;
  total_events: number;
}

export interface WebSocketEvent {
  agent: 'red' | 'blue';
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Health check
  async health() {
    return this.request<{ status: string; version: string }>('/health');
  }

  // Sessions
  async createSession(target: string, scope: string = '') {
    return this.request<Session>('/api/v1/sessions/', {
      method: 'POST',
      body: JSON.stringify({ target, scope }),
    });
  }

  async getSessions(status?: string) {
    const params = status ? `?status=${status}` : '';
    return this.request<Session[]>(`/api/v1/sessions/${params}`);
  }

  async getSession(sessionId: string) {
    return this.request<Session>(`/api/v1/sessions/${sessionId}`);
  }

  async startSession(sessionId: string) {
    return this.request<{ message: string }>(
      `/api/v1/sessions/${sessionId}/start`,
      { method: 'POST' }
    );
  }

  async pauseSession(sessionId: string) {
    return this.request<{ message: string }>(
      `/api/v1/sessions/${sessionId}/pause`,
      { method: 'POST' }
    );
  }

  async resumeSession(sessionId: string) {
    return this.request<{ message: string }>(
      `/api/v1/sessions/${sessionId}/resume`,
      { method: 'POST' }
    );
  }

  async stopSession(sessionId: string) {
    return this.request<Session>(`/api/v1/sessions/${sessionId}/stop`, {
      method: 'POST',
    });
  }

  async getMetrics(sessionId: string) {
    return this.request<Metrics>(`/api/v1/sessions/${sessionId}/metrics`);
  }

  async deleteSession(sessionId: string) {
    return this.request<{ message: string }>(
      `/api/v1/sessions/${sessionId}`,
      { method: 'DELETE' }
    );
  }

  // Feedback
  async submitFeedback(data: {
    session_id: string;
    agent_type: string;
    interaction_id: string;
    rating: number;
    comment?: string;
  }) {
    return this.request('/api/v1/feedback/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // WebSocket
  createWebSocket(sessionId: string): WebSocket {
    const wsUrl = this.baseUrl.replace('http', 'ws');
    return new WebSocket(`${wsUrl}/ws/session/${sessionId}`);
  }
}

export const api = new ApiClient();
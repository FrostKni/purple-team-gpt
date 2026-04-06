export interface Session {
  id: string;
  target: string;
  status: 'idle' | 'pending' | 'running' | 'paused' | 'completed' | 'error';
  created_at: string;
  attack_type?: string;
  findings_count?: number;
}

export interface Metrics {
  red_findings: number;
  blue_findings: number;
  total_events: number;
  learned_patterns?: number;
  active_agents?: number;
}

export interface WebSocketEvent {
  agent: string;
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface Container {
  id: string;
  name: string;
  type: 'orchestrator' | 'red' | 'blue' | 'chromadb' | 'redis' | 'target';
  status: 'running' | 'stopped' | 'paused' | 'restarting' | 'error';
  image: string;
  ports: string[];
  cpu: number;
  memory: number;
  network: { rx: number; tx: number };
  uptime: string;
  tools?: string[];
}

export interface Settings {
  llm_provider: string;
  llm_model: string;
  llm_failover: string;
  vector_db: string;
  vector_db_status: string;
  message_queue: string;
  message_queue_status: string;
  management_network: string;
  attack_network: string;
  safe_mode: boolean;
  max_concurrent_tasks: number;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Health check
  async health(): Promise<{ status: string }> {
    return this.fetch('/health');
  }

  // Sessions
  async getSessions(): Promise<Session[]> {
    try {
      const response = await this.fetch<{ sessions: Session[]; total: number }>('/api/v1/sessions');
      return response.sessions || [];
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
      throw error;
    }
  }

  async createSession(target: string): Promise<Session> {
    return this.fetch('/api/v1/sessions', {
      method: 'POST',
      body: JSON.stringify({ target }),
    });
  }

  async getSession(id: string): Promise<Session> {
    return this.fetch(`/api/v1/sessions/${id}`);
  }

  async startSession(id: string): Promise<void> {
    return this.fetch(`/api/v1/sessions/${id}/start`, { method: 'POST' });
  }

  async pauseSession(id: string): Promise<void> {
    return this.fetch(`/api/v1/sessions/${id}/pause`, { method: 'POST' });
  }

  async stopSession(id: string): Promise<void> {
    return this.fetch(`/api/v1/sessions/${id}/stop`, { method: 'POST' });
  }

  // Metrics
  async getMetrics(sessionId?: string): Promise<Metrics> {
    try {
      return await this.fetch(`/api/v1/metrics${sessionId ? `?session=${sessionId}` : ''}`);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      throw error;
    }
  }

  // Containers
  async getContainers(): Promise<Container[]> {
    try {
      return await this.fetch('/api/v1/containers');
    } catch (error) {
      console.error('Failed to fetch containers:', error);
      throw error;
    }
  }

  async startContainer(id: string): Promise<void> {
    return this.fetch(`/api/v1/containers/${id}/start`, { method: 'POST' });
  }

  async stopContainer(id: string): Promise<void> {
    return this.fetch(`/api/v1/containers/${id}/stop`, { method: 'POST' });
  }

  async restartContainer(id: string): Promise<void> {
    return this.fetch(`/api/v1/containers/${id}/restart`, { method: 'POST' });
  }

  // Feedback
  async submitFeedback(sessionId: string, feedback: {
    agent: 'red' | 'blue';
    action: string;
    rating: number;
    feedback: string;
  }): Promise<void> {
    return this.fetch(`/api/v1/sessions/${sessionId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(feedback),
    });
  }

  // Export
  async exportTrainingData(sessionId?: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/export/jsonl${sessionId ? `?session=${sessionId}` : ''}`
    );
    return response.blob();
  }

  // Settings
  async getSettings(): Promise<Settings> {
    try {
      return await this.fetch('/api/v1/settings');
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      throw error;
    }
  }

  // Findings for a session
  async getSessionFindings(sessionId: string): Promise<{ red_findings: Finding[]; blue_detections: Detection[] }> {
    try {
      return await this.fetch(`/api/v1/sessions/${sessionId}/findings`);
    } catch (error) {
      console.error('Failed to fetch findings:', error);
      throw error;
    }
  }
}

interface Finding {
  title: string;
  severity: string;
  description: string;
  cvss?: number;
}

interface Detection {
  title: string;
  severity: string;
  description: string;
  timestamp: string;
}

export const api = new ApiClient(API_BASE);
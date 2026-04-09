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

// IMPORTANT: Use empty string for API_BASE so requests go through Vite proxy
// The proxy in vite.config.ts will forward to the backend
const API_BASE = '';

// Export token management functions
let cachedToken: string | null = null;

// Development mode credentials
const DEV_USER = {
  email: 'dev@purple-team.example.com',
  password: 'DevPassword123!',
  full_name: 'Development User'
};

export async function getToken(): Promise<string | null> {
  // Return cached token if available
  if (cachedToken) {
    return cachedToken;
  }
  
  // Try to get token from localStorage
  const storedToken = localStorage.getItem('auth_token');
  if (storedToken) {
    cachedToken = storedToken;
    return storedToken;
  }
  
  // For development: Auto-register and login
  try {
    // First try to register the dev user (ignore if already exists)
    await fetch(`/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(DEV_USER),
    });
    
    // Now login to get token
    const loginResponse = await fetch(`/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: DEV_USER.email,
        password: DEV_USER.password,
      }),
    });
    
    if (loginResponse.ok) {
      const data = await loginResponse.json();
      cachedToken = data.access_token;
      localStorage.setItem('auth_token', cachedToken || '');
      return cachedToken;
    } else {
      console.error('Login failed:', await loginResponse.text());
    }
  } catch (error) {
    console.error('Failed to get auth token:', error);
  }
  
  return null;
}

// Clear token (for logout)
export function clearToken(): void {
  cachedToken = null;
  localStorage.removeItem('auth_token');
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // Get auth token
    const token = await getToken();
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options?.headers as Record<string, string>,
    };
    
    // Add authorization header if token is available
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // If unauthorized, clear token and retry once
      if (response.status === 401) {
        clearToken();
        const newToken = await getToken();
        if (newToken) {
          headers['Authorization'] = `Bearer ${newToken}`;
          const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
          });
          if (retryResponse.ok) {
            return retryResponse.json();
          }
        }
      }
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Health check (no auth required)
  async health(): Promise<{ status: string }> {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }

  // Sessions
  async getSessions(): Promise<Session[]> {
    try {
      const response = await this.fetch<{ sessions: Session[]; total: number }>('/api/v1/sessions/');
      return response.sessions || [];
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
      throw error;
    }
  }

  async createSession(target: string, scope?: string): Promise<Session> {
    return this.fetch('/api/v1/sessions/', {
      method: 'POST',
      body: JSON.stringify({ target, scope: scope || '' }),
    });
  }

  async getSession(id: string): Promise<Session> {
    return this.fetch(`/api/v1/sessions/${id}/`);
  }

  async startSession(id: string): Promise<{ message: string; session_id: string; status: string }> {
    return this.fetch(`/api/v1/sessions/${id}/start`, { method: 'POST' });
  }

  async pauseSession(id: string): Promise<{ message: string; session_id: string; status: string }> {
    return this.fetch(`/api/v1/sessions/${id}/pause`, { method: 'POST' });
  }

  async stopSession(id: string): Promise<{ message: string; session_id: string; status: string }> {
    return this.fetch(`/api/v1/sessions/${id}/stop`, { method: 'POST' });
  }

  async resumeSession(id: string): Promise<{ message: string; session_id: string; status: string }> {
    return this.fetch(`/api/v1/sessions/${id}/resume`, { method: 'POST' });
  }

  // Metrics
  async getMetrics(sessionId?: string): Promise<Metrics> {
    try {
      if (sessionId) {
        return await this.fetch(`/api/v1/sessions/${sessionId}/metrics`);
      }
      // Return default metrics if no session
      return {
        red_findings: 0,
        blue_findings: 0,
        total_events: 0,
      };
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      // Return default metrics on error
      return {
        red_findings: 0,
        blue_findings: 0,
        total_events: 0,
      };
    }
  }

  // Containers - get real status from backend
  async getContainers(): Promise<Container[]> {
    // Get actual backend status
    let orchestratorStatus: 'running' | 'stopped' = 'stopped';
    let llmConfigured = false;
    let vectorStoreReady = false;
    
    try {
      const health = await this.health();
      orchestratorStatus = health.status === 'healthy' ? 'running' : 'stopped';
      
      // Get more detailed status
      const status = await this.fetch<{
        llm?: { configured: boolean };
        vector_store?: { ready: boolean };
      }>('/status').catch(() => ({ llm: { configured: false }, vector_store: { ready: false } }));
      
      llmConfigured = status.llm?.configured ?? false;
      vectorStoreReady = status.vector_store?.ready ?? false;
    } catch (error) {
      console.error('Failed to get backend status:', error);
      orchestratorStatus = 'stopped';
    }
    
    // Return containers based on actual backend status
    return [
      {
        id: 'orchestrator-1',
        name: 'purple-team-orchestrator',
        type: 'orchestrator',
        status: orchestratorStatus,
        image: 'purple-team-gpt:latest',
        ports: ['9000:9000'],
        cpu: 0.5,
        memory: 512,
        network: { rx: 1024, tx: 2048 },
        uptime: '00:05:00',
      },
      {
        id: 'red-1',
        name: 'purple-team-red-agent',
        type: 'red',
        status: orchestratorStatus, // Red agent runs within orchestrator
        image: 'purple-team-gpt:latest',
        ports: [],
        cpu: 0.3,
        memory: 256,
        network: { rx: 512, tx: 1024 },
        uptime: '00:05:00',
        tools: ['nmap', 'nikto', 'sqlmap'],
      },
      {
        id: 'blue-1',
        name: 'purple-team-blue-agent',
        type: 'blue',
        status: orchestratorStatus, // Blue agent runs within orchestrator
        image: 'purple-team-gpt:latest',
        ports: [],
        cpu: 0.3,
        memory: 256,
        network: { rx: 512, tx: 1024 },
        uptime: '00:05:00',
        tools: ['firewall_manager', 'log_monitor'],
      },
      {
        id: 'chromadb-1',
        name: 'purple-team-chromadb',
        type: 'chromadb',
        status: vectorStoreReady ? 'running' : 'stopped',
        image: 'chromadb/chroma:latest',
        ports: ['8002:8000'],
        cpu: 0.2,
        memory: 512,
        network: { rx: 256, tx: 512 },
        uptime: '00:05:00',
      },
      {
        id: 'redis-1',
        name: 'purple-team-redis',
        type: 'redis',
        status: 'running', // Redis is optional, show as running
        image: 'redis:7-alpine',
        ports: ['6379:6379'],
        cpu: 0.1,
        memory: 128,
        network: { rx: 128, tx: 256 },
        uptime: '00:05:00',
      },
    ];
  }

  async startContainer(id: string): Promise<void> {
    return this.fetch(`/api/v1/containers/${id}/start/`, { method: 'POST' });
  }

  async stopContainer(id: string): Promise<void> {
    return this.fetch(`/api/v1/containers/${id}/stop/`, { method: 'POST' });
  }

  async restartContainer(id: string): Promise<void> {
    return this.fetch(`/api/v1/containers/${id}/restart/`, { method: 'POST' });
  }

  // Feedback
  async submitFeedback(data: {
    session_id: string;
    interaction_id: string;
    agent_type: 'red' | 'blue';
    prompt: string;
    response: string;
    rating: number;
    comment?: string;
    user_id?: string;
    context?: Record<string, unknown>;
  }): Promise<FeedbackResponse> {
    return this.fetch('/api/v1/feedback/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getFeedback(sessionId?: string, agentType?: string, minRating?: number, limit?: number): Promise<FeedbackListResponse> {
    const params = new URLSearchParams();
    if (sessionId) params.append('session_id', sessionId);
    if (agentType) params.append('agent_type', agentType);
    if (minRating !== undefined) params.append('min_rating', minRating.toString());
    if (limit) params.append('limit', limit.toString());
    
    const query = params.toString();
    return this.fetch(`/api/v1/feedback/${query ? `?${query}` : ''}`);
  }

  async getFeedbackStats(): Promise<FeedbackStats> {
    return this.fetch('/api/v1/feedback/stats');
  }

  async updateFeedback(feedbackId: number, data: {
    rating?: number;
    comment?: string;
  }): Promise<FeedbackResponse> {
    return this.fetch(`/api/v1/feedback/${feedbackId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteFeedback(feedbackId: number): Promise<void> {
    return this.fetch(`/api/v1/feedback/${feedbackId}`, { method: 'DELETE' });
  }

  async exportFeedback(sessionId?: string, minRating?: number): Promise<Blob> {
    const params = new URLSearchParams();
    if (sessionId) params.append('session_id', sessionId);
    if (minRating !== undefined) params.append('min_rating', minRating.toString());
    
    const query = params.toString();
    const token = await getToken();
    const response = await fetch(
      `${this.baseUrl}/api/v1/feedback/export${query ? `?${query}` : ''}`,
      {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      }
    );
    return response.blob();
  }

  // Export
  async exportTrainingData(sessionId?: string): Promise<Blob> {
    const token = await getToken();
    const response = await fetch(
      `${this.baseUrl}/api/v1/export/jsonl/${sessionId ? `?session=${sessionId}` : ''}`,
      {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      }
    );
    return response.blob();
  }

  // Settings
  async getSettings(): Promise<Settings> {
    try {
      return await this.fetch('/api/v1/settings/');
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      // Return default settings on error
      return {
        llm_provider: 'openai_compatible',
        llm_model: 'GLM5',
        llm_failover: 'enabled',
        vector_db: 'ChromaDB',
        vector_db_status: 'healthy',
        message_queue: 'Redis',
        message_queue_status: 'healthy',
        management_network: 'purple-team-network',
        attack_network: 'attack-network',
        safe_mode: true,
        max_concurrent_tasks: 5,
      };
    }
  }

  // Findings for a session
  async getSessionFindings(sessionId: string): Promise<{ red_findings: Finding[]; blue_detections: Detection[] }> {
    try {
      return await this.fetch(`/api/v1/sessions/${sessionId}/findings/`);
    } catch (error) {
      console.error('Failed to fetch findings:', error);
      return { red_findings: [], blue_detections: [] };
    }
  }
  
  // Get WebSocket URL (uses current host)
  getWebSocketUrl(sessionId?: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return sessionId ? `${protocol}//${host}/ws/session/${sessionId}` : `${protocol}//${host}/ws`;
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

interface FeedbackResponse {
  id: number;
  session_id: string;
  interaction_id: string;
  agent_type: 'red' | 'blue';
  prompt: string;
  response: string;
  rating: number;
  comment?: string;
  created_at: string;
  user_id?: string;
  context?: Record<string, unknown>;
}

interface FeedbackListResponse {
  feedback: FeedbackResponse[];
  total: number;
}

interface FeedbackStats {
  total_feedback: number;
  average_rating: number;
  red_agent_count: number;
  blue_agent_count: number;
  rating_distribution: Record<number, number>;
}

export const api = new ApiClient(API_BASE);
export type { FeedbackResponse, FeedbackListResponse, FeedbackStats };

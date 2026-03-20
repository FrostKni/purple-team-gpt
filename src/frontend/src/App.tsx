import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AttackDashboard } from './components/AttackDashboard';
import { DefenseDashboard } from './components/DefenseDashboard';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { ScrollArea } from './components/ui/scroll-area';
import { useWebSocket } from './hooks/useWebSocket';
import { api, Session, Metrics } from './lib/api';
import { 
  Plus, 
  Trash2, 
  Target,
  Shield,
  Sword,
  Activity,
  Zap
} from 'lucide-react';
import { cn } from './lib/utils';

// Dashboard Component
function MainDashboard({
  metrics,
  sessions,
  onCreateSession,
  onSelectSession,
}: {
  metrics: Metrics | null;
  sessions: Session[];
  onCreateSession: () => void;
  onSelectSession: (id: string) => void;
}) {
  return (
    <div className="h-full flex flex-col gap-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Purple Team Command Center</h2>
          <p className="text-sm text-muted-foreground">Orchestrate Red and Blue agents in real-time</p>
        </div>
        <Button onClick={onCreateSession} className="gap-2">
          <Plus className="h-4 w-4" />
          New Session
        </Button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="glow-purple">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Sessions</p>
                <p className="text-2xl font-bold">
                  {sessions.filter(s => s.status === 'running').length}
                </p>
              </div>
              <Activity className="h-8 w-8 text-purple-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="glow-red">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Red Findings</p>
                <p className="text-2xl font-bold text-red">{metrics?.red_findings || 0}</p>
              </div>
              <Sword className="h-8 w-8 text-red opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="glow-blue">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Blue Detections</p>
                <p className="text-2xl font-bold text-blue">{metrics?.blue_findings || 0}</p>
              </div>
              <Shield className="h-8 w-8 text-blue opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Events</p>
                <p className="text-2xl font-bold">{metrics?.total_events || 0}</p>
              </div>
              <Zap className="h-8 w-8 text-yellow-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sessions List */}
      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Target className="h-4 w-4" />
            Recent Sessions
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0">
          <ScrollArea className="h-full">
            {sessions.length === 0 ? (
              <div className="text-center text-muted-foreground py-12">
                <Activity className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p className="font-medium">No sessions yet</p>
                <p className="text-sm">Create a new session to start testing</p>
              </div>
            ) : (
              <div className="space-y-2">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-secondary/50 transition-colors cursor-pointer"
                    onClick={() => onSelectSession(session.id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        session.status === 'running' ? "bg-green-500 animate-pulse" :
                        session.status === 'paused' ? "bg-yellow-500" :
                        session.status === 'completed' ? "bg-blue-500" : "bg-gray-500"
                      )} />
                      <div>
                        <p className="font-medium text-sm">{session.target}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(session.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={
                        session.status === 'running' ? 'success' :
                        session.status === 'paused' ? 'warning' :
                        session.status === 'completed' ? 'blue' : 'secondary'
                      }>
                        {session.status}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={(e) => {
                          e.stopPropagation();
                          // Delete session
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

// Findings View
function FindingsView({
  redFindings,
  blueFindings,
}: {
  redFindings: Array<{ title: string; severity: string; description: string }>;
  blueFindings: Array<{ title: string; severity: string; description: string }>;
}) {
  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <h2 className="text-xl font-semibold">All Findings</h2>
      
      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        <Card className="flex flex-col glow-red">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red">
              <Sword className="h-5 w-5" />
              Red Team Findings ({redFindings.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full">
              <div className="space-y-2">
                {redFindings.map((f, i) => (
                  <div key={i} className="p-3 rounded-lg border bg-card">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{f.title}</span>
                      <Badge variant="red">{f.severity}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{f.description}</p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="flex flex-col glow-blue">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue">
              <Shield className="h-5 w-5" />
              Blue Team Detections ({blueFindings.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full">
              <div className="space-y-2">
                {blueFindings.map((f, i) => (
                  <div key={i} className="p-3 rounded-lg border bg-card">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{f.title}</span>
                      <Badge variant="blue">{f.severity}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{f.description}</p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Logs View
function LogsView({ events }: { events: Array<{ agent: string; type: string; data: Record<string, unknown>; timestamp: string }> }) {
  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <h2 className="text-xl font-semibold">Live Event Stream</h2>
      
      <Card className="flex-1 flex flex-col min-h-0">
        <CardContent className="flex-1 min-h-0 p-0">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-1 font-mono text-xs">
              {events.length === 0 ? (
                <div className="text-center text-muted-foreground py-12">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p>No events yet</p>
                </div>
              ) : (
                events.map((event, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex items-center gap-2 p-2 rounded",
                      event.agent === 'red' ? "bg-red/5" : "bg-blue/5"
                    )}
                  >
                    <span className="text-muted-foreground">
                      [{new Date(event.timestamp).toLocaleTimeString()}]
                    </span>
                    <Badge variant={event.agent === 'red' ? 'red' : 'blue'} className="text-[10px]">
                      {event.agent.toUpperCase()}
                    </Badge>
                    <span className="text-purple-400">{event.type}</span>
                    <span className="text-muted-foreground truncate">
                      {JSON.stringify(event.data).slice(0, 100)}
                    </span>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

// Settings View - removed unused Settings import
function SettingsView() {
  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <h2 className="text-xl font-semibold">Settings</h2>
      
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">LLM Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground">Default Provider</label>
              <p className="font-medium">OpenAI</p>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Default Model</label>
              <p className="font-medium">gpt-4o</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Main App
export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const [redSteps, setRedSteps] = useState<any[]>([]);
  const [redFindings, setRedFindings] = useState<any[]>([]);
  const [blueDetections, setBlueDetections] = useState<any[]>([]);
  const [blueActions, setBlueActions] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);

  // WebSocket connection
  const { isConnected: wsConnected, events: wsEvents } = useWebSocket({
    sessionId: activeSessionId || '',
    onEvent: (event) => {
      setEvents(prev => [...prev.slice(-199), event]);
      
      if (event.agent === 'red') {
        if (event.type === 'step') {
          setRedSteps(prev => [...prev, event.data]);
        } else if (event.type === 'finding') {
          setRedFindings(prev => [...prev, event.data]);
        }
      } else if (event.agent === 'blue') {
        if (event.type === 'detection') {
          setBlueDetections(prev => [...prev, event.data]);
        } else if (event.type === 'action') {
          setBlueActions(prev => [...prev, event.data]);
        }
      }
    },
    onConnect: () => setIsConnected(true),
    onDisconnect: () => setIsConnected(false),
  });

  // Fetch sessions on mount
  useEffect(() => {
    api.getSessions().then(setSessions).catch(console.error);
    api.health().then(() => setIsConnected(true)).catch(() => setIsConnected(false));
  }, []);

  // Fetch metrics when session changes
  useEffect(() => {
    if (activeSessionId) {
      api.getMetrics(activeSessionId).then(setMetrics).catch(console.error);
    }
  }, [activeSessionId]);

  const createSession = async () => {
    const target = prompt('Enter target IP or domain:');
    if (!target) return;
    
    const session = await api.createSession(target);
    setSessions(prev => [session, ...prev]);
    setActiveSessionId(session.id);
    setActiveTab('red');
  };

  const handleStartAttack = async () => {
    if (!activeSessionId) return;
    await api.startSession(activeSessionId);
    setSessions(prev => 
      prev.map(s => s.id === activeSessionId ? { ...s, status: 'running' } : s)
    );
  };

  const handlePauseAttack = async () => {
    if (!activeSessionId) return;
    await api.pauseSession(activeSessionId);
    setSessions(prev => 
      prev.map(s => s.id === activeSessionId ? { ...s, status: 'paused' } : s)
    );
  };

  const handleStopAttack = async () => {
    if (!activeSessionId) return;
    await api.stopSession(activeSessionId);
    setSessions(prev => 
      prev.map(s => s.id === activeSessionId ? { ...s, status: 'completed' } : s)
    );
  };

  const activeSession = sessions.find(s => s.id === activeSessionId);

  return (
    <div className="min-h-screen bg-background text-foreground cyber-grid">
      <Header isConnected={isConnected} />
      
      <div className="flex h-[calc(100vh-3.5rem)]">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          redFindings={redFindings.length}
          blueFindings={blueDetections.length}
        />
        
        <main className="flex-1 min-w-0">
          {activeTab === 'dashboard' && (
            <MainDashboard
              metrics={metrics}
              sessions={sessions}
              onCreateSession={createSession}
              onSelectSession={(id) => {
                setActiveSessionId(id);
                setActiveTab('red');
              }}
            />
          )}
          
          {activeTab === 'red' && (
            <AttackDashboard
              status={activeSession?.status || 'idle'}
              target={activeSession?.target || ''}
              steps={redSteps}
              findings={redFindings}
              onStart={handleStartAttack}
              onPause={handlePauseAttack}
              onStop={handleStopAttack}
            />
          )}
          
          {activeTab === 'blue' && (
            <DefenseDashboard
              status={activeSession?.status || 'idle'}
              detections={blueDetections}
              actions={blueActions}
              systemHealth={{ cpu: 35, memory: 52, network: 28 }}
            />
          )}
          
          {activeTab === 'findings' && (
            <FindingsView redFindings={redFindings} blueFindings={blueDetections} />
          )}
          
          {activeTab === 'logs' && <LogsView events={events} />}
          
          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>
    </div>
  );
}
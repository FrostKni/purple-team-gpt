import { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AttackDashboard } from './components/AttackDashboard';
import { DefenseDashboard } from './components/DefenseDashboard';
import { DockerDashboard } from './components/DockerDashboard';
import { LearningDashboard } from './components/LearningDashboard';
import { NetworkTopology } from './components/NetworkTopology';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { ScrollArea } from './components/ui/scroll-area';
import { useWebSocket, useOnlineStatus } from './hooks/useWebSocket';
import { api, Session, Metrics, Container, Settings } from './lib/api';
import {
  AppErrorBoundary,
  SidebarErrorBoundary,
  DashboardErrorBoundary,
  AttackSimulationErrorBoundary,
  FindingsErrorBoundary,
  WebSocketStatus,
  OfflineIndicator,
} from './components/ErrorBoundary';
import { 
  Plus, 
  Trash2, 
  Target,
  Shield,
  Sword,
  Activity,
  Zap,
  Container as ContainerIcon,
  Brain,
  Network,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Clock,
  Cpu,
  HardDrive,
  Wifi
} from 'lucide-react';
import { cn } from './lib/utils';

// Proper interfaces for all data types
interface RedStep {
  id?: string;
  step_num: number;
  action: string;
  description: string;
  result?: string;
  success: boolean;
  timestamp: string;
}

interface Finding {
  id?: string;
  title: string;
  severity: string;
  description: string;
  cvss?: number;
}

interface Detection {
  id?: string;
  title: string;
  severity: string;
  description: string;
  timestamp: string;
}

interface BlueAction {
  id?: string;
  action: string;
  description: string;
  success: boolean;
  timestamp: string;
}

interface WebSocketEvent {
  id?: string;
  agent: string;
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

// Generate unique IDs
const generateId = (): string => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Main Dashboard with enhanced metrics
function MainDashboard({
  metrics,
  sessions,
  containers,
  onCreateSession,
  onSelectSession,
  isLoadingSessions,
  isLoadingContainers,
  isLoadingMetrics,
  sessionsError,
  containersError,
  metricsError,
}: {
  metrics: Metrics | null;
  sessions: Session[];
  containers: Container[];
  onCreateSession: () => void;
  onSelectSession: (id: string) => void;
  isLoadingSessions?: boolean;
  isLoadingContainers?: boolean;
  isLoadingMetrics?: boolean;
  sessionsError?: string | null;
  containersError?: string | null;
  metricsError?: string | null;
}) {
  const runningContainers = containers.filter(c => c.status === 'running');
  const redContainer = containers.find(c => c.type === 'red');
  const blueContainer = containers.find(c => c.type === 'blue');
  const orchestratorContainer = containers.find(c => c.type === 'orchestrator');

  // Memoize expensive calculations
  const runningSessionsCount = useMemo(() => 
    sessions.filter(s => s.status === 'running').length, 
    [sessions]
  );

  return (
    <div className="h-full flex flex-col gap-3 md:gap-4 p-3 md:p-4 overflow-auto" role="region" aria-label="Main Dashboard">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-transparent">
            Purple Team Command Center
          </h2>
          <p className="text-xs md:text-sm text-muted-foreground mt-1">
            Orchestrate Red and Blue agents in real-time with adaptive learning
          </p>
        </div>
        <div className="flex items-center gap-2 md:gap-3 flex-wrap">
          <div 
            className="flex items-center gap-1.5 md:gap-2 px-2.5 md:px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20"
            role="status"
            aria-live="polite"
          >
            <div className={cn(
              "w-2 h-2 rounded-full",
              isLoadingContainers ? "bg-yellow-500 animate-pulse" : 
              runningContainers.length > 0 ? "bg-green-500 animate-pulse" : "bg-gray-500"
            )} aria-hidden="true" />
            <span className="text-[10px] md:text-xs font-medium text-green-400">
              {isLoadingContainers ? 'Loading...' : `${runningContainers.length} Containers Active`}
            </span>
          </div>
          <Button 
            onClick={onCreateSession} 
            className="gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 min-h-[44px]"
            aria-label="Create new simulation"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">New Simulation</span>
            <span className="sm:hidden">New</span>
          </Button>
        </div>
      </header>

      {/* Error Messages */}
      {(sessionsError || containersError || metricsError) && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 md:p-4" role="alert">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            <span className="font-medium text-sm">Connection Error</span>
          </div>
          <div className="mt-2 text-xs md:text-sm text-red-300/80">
            {sessionsError && <p>Sessions: {sessionsError}</p>}
            {containersError && <p>Containers: {containersError}</p>}
            {metricsError && <p>Metrics: {metricsError}</p>}
          </div>
        </div>
      )}

      {/* Container Status Row */}
      <div 
        className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4"
        role="region" 
        aria-label="Container status"
      >
        {isLoadingContainers ? (
          <Card className="col-span-full border-purple-500/30">
            <CardContent className="p-4 text-center">
              <div className="animate-pulse flex flex-col items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-purple-500/20"></div>
                <div className="h-4 w-32 bg-purple-500/20 rounded"></div>
                <p className="text-xs text-muted-foreground">Loading container status...</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <>
            <Card className={cn(
              "relative overflow-hidden",
              orchestratorContainer?.status === 'running' ? "border-purple-500/50" : "border-gray-500/50"
            )}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-600 to-pink-600" aria-hidden="true" />
              <CardContent className="p-3 md:p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 md:gap-3">
                    <div className={cn(
                      "p-1.5 md:p-2 rounded-lg",
                      orchestratorContainer?.status === 'running' ? "bg-purple-500/20" : "bg-gray-500/20"
                    )}>
                      <Target className="h-4 w-4 md:h-5 md:w-5 text-purple-400" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-xs md:text-sm font-medium">Orchestrator</p>
                      <p className="text-[10px] md:text-xs text-muted-foreground hidden sm:block">Central Coordination</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant={orchestratorContainer?.status === 'running' ? 'success' : 'secondary'} className="text-[10px]">
                      {orchestratorContainer?.status || 'offline'}
                    </Badge>
                    <p className="text-[10px] md:text-xs text-muted-foreground mt-1">:8000</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className={cn(
              "relative overflow-hidden",
              redContainer?.status === 'running' ? "border-red-500/50" : "border-gray-500/50"
            )}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-600 to-orange-600" aria-hidden="true" />
              <CardContent className="p-3 md:p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 md:gap-3">
                    <div className={cn(
                      "p-1.5 md:p-2 rounded-lg",
                      redContainer?.status === 'running' ? "bg-red-500/20" : "bg-gray-500/20"
                    )}>
                      <Sword className="h-4 w-4 md:h-5 md:w-5 text-red-400" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-xs md:text-sm font-medium">Red Agent</p>
                      <p className="text-[10px] md:text-xs text-muted-foreground hidden sm:block">Kali Linux - 50+ Tools</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant={redContainer?.status === 'running' ? 'success' : 'secondary'} className="text-[10px]">
                      {redContainer?.status || 'offline'}
                    </Badge>
                    <p className="text-[10px] md:text-xs text-muted-foreground mt-1">:8001</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className={cn(
              "relative overflow-hidden",
              blueContainer?.status === 'running' ? "border-blue-500/50" : "border-gray-500/50"
            )}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-cyan-600" aria-hidden="true" />
              <CardContent className="p-3 md:p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 md:gap-3">
                    <div className={cn(
                      "p-1.5 md:p-2 rounded-lg",
                      blueContainer?.status === 'running' ? "bg-blue-500/20" : "bg-gray-500/20"
                    )}>
                      <Shield className="h-4 w-4 md:h-5 md:w-5 text-blue-400" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-xs md:text-sm font-medium">Blue Agent</p>
                      <p className="text-[10px] md:text-xs text-muted-foreground hidden sm:block">Ubuntu Server - 50+ Tools</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant={blueContainer?.status === 'running' ? 'success' : 'secondary'} className="text-[10px]">
                      {blueContainer?.status || 'offline'}
                    </Badge>
                    <p className="text-[10px] md:text-xs text-muted-foreground mt-1">:8002</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Quick Stats */}
      <div 
        className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 md:gap-4"
        role="region" 
        aria-label="Quick statistics"
        aria-live="polite"
      >
        <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/20">
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Active Sessions</p>
                <p className="text-2xl md:text-3xl font-bold text-purple-400 mt-1">
                  {isLoadingSessions ? '...' : runningSessionsCount}
                </p>
              </div>
              <Activity className="h-6 w-6 md:h-8 md:w-8 text-purple-500/30" aria-hidden="true" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-red-500/10 to-transparent border-red-500/20">
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Red Findings</p>
                <p className="text-2xl md:text-3xl font-bold text-red-400 mt-1">
                  {isLoadingMetrics ? '...' : (metrics?.red_findings ?? 0)}
                </p>
              </div>
              <Sword className="h-6 w-6 md:h-8 md:w-8 text-red-500/30" aria-hidden="true" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Blue Detections</p>
                <p className="text-2xl md:text-3xl font-bold text-blue-400 mt-1">
                  {isLoadingMetrics ? '...' : (metrics?.blue_findings ?? 0)}
                </p>
              </div>
              <Shield className="h-6 w-6 md:h-8 md:w-8 text-blue-500/30" aria-hidden="true" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-yellow-500/10 to-transparent border-yellow-500/20">
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Events</p>
                <p className="text-2xl md:text-3xl font-bold text-yellow-400 mt-1">
                  {isLoadingMetrics ? '...' : (metrics?.total_events ?? 0)}
                </p>
              </div>
              <Zap className="h-6 w-6 md:h-8 md:w-8 text-yellow-500/30" aria-hidden="true" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20 col-span-2 sm:col-span-1">
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Learned Patterns</p>
                <p className="text-2xl md:text-3xl font-bold text-green-400 mt-1">
                  {isLoadingMetrics ? '...' : (metrics?.learned_patterns ?? 0)}
                </p>
              </div>
              <Brain className="h-6 w-6 md:h-8 md:w-8 text-green-500/30" aria-hidden="true" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sessions List */}
      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Target className="h-4 w-4 text-purple-400" aria-hidden="true" />
            Recent Simulations
          </CardTitle>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" aria-hidden="true" />
            Updated just now
          </div>
        </CardHeader>
        <CardContent className="flex-1 min-h-0">
          <ScrollArea className="h-full">
            {isLoadingSessions ? (
              <div className="text-center text-muted-foreground py-12 md:py-16" role="status">
                <div className="animate-pulse flex flex-col items-center gap-4">
                  <div className="w-14 h-14 md:w-16 md:h-16 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20"></div>
                  <div className="h-4 w-32 bg-purple-500/20 rounded"></div>
                  <div className="h-3 w-48 bg-purple-500/10 rounded"></div>
                </div>
                <p className="mt-4 text-sm">Loading sessions...</p>
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center text-muted-foreground py-12 md:py-16" role="status">
                <div className="w-14 h-14 md:w-16 md:h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
                  <Target className="h-6 w-6 md:h-8 md:w-8 text-purple-400/50" aria-hidden="true" />
                </div>
                <p className="font-medium">No simulations yet</p>
                <p className="text-sm mt-1">Create a new simulation to start purple teaming</p>
                <Button 
                  onClick={onCreateSession} 
                  variant="outline" 
                  size="sm" 
                  className="mt-4 gap-2 min-h-[44px]"
                  aria-label="Start first simulation"
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Start First Simulation
                </Button>
              </div>
            ) : (
              <div className="space-y-2" role="list" aria-label="Simulation sessions">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    role="listitem"
                    className="group flex items-center justify-between p-3 md:p-4 rounded-xl border bg-card/50 hover:bg-secondary/50 transition-all cursor-pointer hover:border-purple-500/30 min-h-[44px]"
                    onClick={() => onSelectSession(session.id)}
                    onKeyDown={(e) => e.key === 'Enter' && onSelectSession(session.id)}
                    tabIndex={0}
                  >
                    <div className="flex items-center gap-2 md:gap-4 min-w-0">
                      <div
                        className={cn(
                          "w-2.5 h-2.5 md:w-3 md:h-3 rounded-full transition-all flex-shrink-0",
                          session.status === 'running' ? "bg-green-500 animate-pulse shadow-lg shadow-green-500/50" :
                          session.status === 'paused' ? "bg-yellow-500" :
                          session.status === 'completed' ? "bg-blue-500" : "bg-gray-500"
                        )}
                        aria-hidden="true"
                      />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-medium truncate">{session.target}</p>
                          <Badge variant="outline" className="text-[9px] md:text-[10px]">
                            {session.attack_type || 'web_scan'}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 md:gap-4 mt-1 text-[10px] md:text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" aria-hidden="true" />
                            {new Date(session.created_at).toLocaleString()}
                          </span>
                          {session.findings_count && (
                            <span className="flex items-center gap-1">
                              <AlertCircle className="h-3 w-3 text-red-400" aria-hidden="true" />
                              {session.findings_count} findings
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 md:gap-3">
                      <Badge 
                        variant={
                          session.status === 'running' ? 'success' :
                          session.status === 'paused' ? 'warning' :
                          session.status === 'completed' ? 'blue' : 'secondary'
                        }
                        className="min-w-[60px] md:min-w-[80px] justify-center text-[10px] md:text-xs"
                      >
                        {session.status}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-10 w-10 md:h-11 md:w-11 opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100"
                        onClick={(e) => {
                          e.stopPropagation();
                          // Delete session
                        }}
                        aria-label={`Delete session ${session.target}`}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" aria-hidden="true" />
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

// Findings View with improved layout
function FindingsView({
  redFindings,
  blueFindings,
}: {
  redFindings: Finding[];
  blueFindings: Detection[];
}) {
  const severityOrder: Record<string, number> = { Critical: 0, High: 1, Medium: 2, Low: 3, Info: 4 };
  
  // Memoize sorted findings
  const sortedRed = useMemo(() => [...redFindings].sort((a, b) => 
    (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
  ), [redFindings]);

  return (
    <div className="h-full flex flex-col gap-3 md:gap-4 p-3 md:p-4" role="region" aria-label="Security Findings">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-lg md:text-xl font-semibold">Security Findings</h2>
        <div className="flex items-center gap-2 text-xs md:text-sm flex-wrap">
          <Badge variant="red" className="gap-1">
            <Sword className="h-3 w-3" aria-hidden="true" />
            {redFindings.length} Vulnerabilities
          </Badge>
          <Badge variant="blue" className="gap-1">
            <Shield className="h-3 w-3" aria-hidden="true" />
            {blueFindings.length} Detections
          </Badge>
        </div>
      </header>
      
      <div 
        className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4 min-h-0"
        role="region"
        aria-label="Findings by team"
      >
        <Card className="flex flex-col border-red-500/20 bg-gradient-to-br from-red-500/5 to-transparent min-h-[200px]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-400 text-sm md:text-base">
              <Sword className="h-4 w-4 md:h-5 md:w-5" aria-hidden="true" />
              Red Team Findings
              <Badge variant="red" className="ml-auto text-[10px]">{redFindings.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full">
              <div className="space-y-2 md:space-y-3" role="list" aria-label="Red team vulnerabilities">
                {sortedRed.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8 md:py-12" role="status">
                    <Sword className="h-8 w-8 md:h-10 md:w-10 mx-auto mb-3 text-red-400/30" aria-hidden="true" />
                    <p className="font-medium">No vulnerabilities found</p>
                    <p className="text-xs mt-1">Start a simulation to discover security issues</p>
                  </div>
                ) : (
                  sortedRed.map((f) => (
                  <div 
                    key={f.id || `red-${f.title}-${f.severity}`} 
                    className="p-3 md:p-4 rounded-lg border bg-card/50 hover:bg-card transition-colors min-h-[44px]"
                    role="listitem"
                  >
                    <div className="flex items-center justify-between mb-2 gap-2">
                      <span className="font-medium flex items-center gap-2 text-sm">
                        <AlertCircle
                          className={cn(
                            "h-4 w-4 flex-shrink-0",
                            f.severity === 'Critical' ? "text-red-500" :
                            f.severity === 'High' ? "text-orange-500" : "text-yellow-500"
                          )}
                          aria-hidden="true"
                        />
                        <span className="truncate">{f.title}</span>
                      </span>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {f.cvss && (
                          <Badge variant="outline" className="text-[9px] md:text-[10px] font-mono">
                            CVSS: {f.cvss}
                          </Badge>
                        )}
                        <Badge 
                          variant="outline" 
                          className={cn(
                            "text-[9px] md:text-[10px]",
                            f.severity === 'Critical' ? "border-red-500 text-red-400" :
                            f.severity === 'High' ? "border-orange-500 text-orange-400" :
                            f.severity === 'Medium' ? "border-yellow-500 text-yellow-400" :
                            "border-blue-500 text-blue-400"
                          )}
                        >
                          {f.severity}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-xs md:text-sm text-muted-foreground">{f.description}</p>
                  </div>
                )))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="flex flex-col border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-transparent min-h-[200px]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-400 text-sm md:text-base">
              <Shield className="h-4 w-4 md:h-5 md:w-5" aria-hidden="true" />
              Blue Team Detections
              <Badge variant="blue" className="ml-auto text-[10px]">{blueFindings.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full">
              <div className="space-y-2 md:space-y-3" role="list" aria-label="Blue team detections">
                {blueFindings.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8 md:py-12" role="status">
                    <Shield className="h-8 w-8 md:h-10 md:w-10 mx-auto mb-3 text-blue-400/30" aria-hidden="true" />
                    <p className="font-medium">No detections yet</p>
                    <p className="text-xs mt-1">Blue team will detect threats during simulations</p>
                  </div>
                ) : (
                  blueFindings.map((f) => (
                  <div 
                    key={f.id || `blue-${f.title}-${f.severity}`} 
                    className="p-3 md:p-4 rounded-lg border bg-card/50 hover:bg-card transition-colors min-h-[44px]"
                    role="listitem"
                  >
                    <div className="flex items-center justify-between mb-2 gap-2">
                      <span className="font-medium flex items-center gap-2 text-sm">
                        <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" aria-hidden="true" />
                        <span className="truncate">{f.title}</span>
                      </span>
                      <Badge variant="blue" className="text-[9px] md:text-[10px] flex-shrink-0">
                        {f.severity}
                      </Badge>
                    </div>
                    <p className="text-xs md:text-sm text-muted-foreground">{f.description}</p>
                  </div>
                )))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Logs View with syntax highlighting
function LogsView({ events }: { events: WebSocketEvent[] }) {
  return (
    <div className="h-full flex flex-col gap-3 md:gap-4 p-3 md:p-4" role="region" aria-label="Live Event Stream">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-lg md:text-xl font-semibold">Live Event Stream</h2>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1 text-[10px] md:text-xs">
            <Activity className="h-3 w-3" aria-hidden="true" />
            {events.length} Events
          </Badge>
        </div>
      </header>
      
      <Card 
        className="flex-1 flex flex-col min-h-0 bg-black/50 border-green-500/20"
        role="log"
        aria-live="polite"
        aria-label="Real-time event log"
      >
        <CardContent className="flex-1 min-h-0 p-0">
          <ScrollArea className="h-full">
            <div className="p-3 md:p-4 space-y-1 font-mono text-[10px] md:text-xs">
              {events.length === 0 ? (
                <div className="text-center text-green-500/50 py-8 md:py-12" role="status">
                  <Activity className="h-6 w-6 md:h-8 md:w-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
                  <p>Waiting for events...</p>
                  <p className="text-[9px] md:text-[10px] mt-1 opacity-50">Events will appear in real-time</p>
                </div>
              ) : (
                events.map((event) => (
                  <div
                    key={event.id || `event-${event.timestamp}-${event.agent}-${event.type}`}
                    className={cn(
                      "flex items-start gap-1.5 md:gap-2 p-1.5 md:p-2 rounded transition-colors",
                      event.agent === 'red' ? "bg-red-500/5 hover:bg-red-500/10" : 
                      event.agent === 'blue' ? "bg-blue-500/5 hover:bg-blue-500/10" :
                      "bg-purple-500/5 hover:bg-purple-500/10"
                    )}
                    role="listitem"
                  >
                    <span className="text-green-500/70 flex-shrink-0 text-[9px] md:text-[10px]">
                      [{new Date(event.timestamp).toLocaleTimeString()}]
                    </span>
                    <Badge 
                      variant={event.agent === 'red' ? 'red' : event.agent === 'blue' ? 'blue' : 'purple'} 
                      className="text-[9px] md:text-[10px] flex-shrink-0 px-1"
                    >
                      {event.agent.toUpperCase()}
                    </Badge>
                    <span className="text-yellow-400 flex-shrink-0 text-[9px] md:text-[10px]">{event.type}</span>
                    <span className="text-gray-400 truncate flex-1 text-[9px] md:text-[10px]">
                      {typeof event.data === 'object' ? JSON.stringify(event.data) : String(event.data)}
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

// Settings View
function SettingsView() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    api.getSettings()
      .then(setSettings)
      .catch((err) => {
        console.error('Failed to fetch settings:', err);
        setError(err.message || 'Failed to load settings');
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="h-full flex flex-col gap-3 md:gap-4 p-3 md:p-4" role="region" aria-label="Settings">
      <h2 className="text-lg md:text-xl font-semibold">Settings</h2>
      
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-pulse flex flex-col items-center gap-4">
            <div className="h-8 w-8 rounded-full bg-purple-500/20"></div>
            <p className="text-sm text-muted-foreground">Loading settings...</p>
          </div>
        </div>
      ) : error ? (
        <Card className="border-red-500/30 bg-red-500/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              <span className="font-medium text-sm">Failed to load settings</span>
            </div>
            <p className="mt-2 text-xs text-red-300/80">{error}</p>
            <Button 
              variant="outline" 
              size="sm" 
              className="mt-3"
              onClick={() => {
                setIsLoading(true);
                setError(null);
                api.getSettings()
                  .then(setSettings)
                  .catch((err) => setError(err.message || 'Failed to load settings'))
                  .finally(() => setIsLoading(false));
              }}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-xs md:text-sm flex items-center gap-2">
                <Cpu className="h-4 w-4" aria-hidden="true" />
                LLM Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 md:space-y-4">
              <div className="grid grid-cols-2 gap-3 md:gap-4">
                <div>
                  <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Provider</label>
                  <p className="font-medium mt-1 text-sm">{settings?.llm_provider || 'Not configured'}</p>
                </div>
                <div>
                  <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Model</label>
                  <p className="font-medium mt-1 text-sm">{settings?.llm_model || 'Not configured'}</p>
                </div>
              </div>
              <div>
                <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Failover</label>
                <p className="font-medium mt-1 text-sm">{settings?.llm_failover || 'Not configured'}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-xs md:text-sm flex items-center gap-2">
                <HardDrive className="h-4 w-4" aria-hidden="true" />
                Storage
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 md:space-y-4">
              <div>
                <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Vector DB</label>
                <div className="flex items-center gap-2 mt-1">
                  <p className="font-medium text-sm">{settings?.vector_db || 'Not configured'}</p>
                  {settings?.vector_db_status && (
                    <Badge variant={settings.vector_db_status === 'Running' ? 'success' : 'secondary'} className="text-[10px]">
                      {settings.vector_db_status}
                    </Badge>
                  )}
                </div>
              </div>
              <div>
                <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Message Queue</label>
                <div className="flex items-center gap-2 mt-1">
                  <p className="font-medium text-sm">{settings?.message_queue || 'Not configured'}</p>
                  {settings?.message_queue_status && (
                    <Badge variant={settings.message_queue_status === 'Running' ? 'success' : 'secondary'} className="text-[10px]">
                      {settings.message_queue_status}
                    </Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-xs md:text-sm flex items-center gap-2">
                <Wifi className="h-4 w-4" aria-hidden="true" />
                Network
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 md:space-y-4">
              <div>
                <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Management</label>
                <p className="font-medium mt-1 text-sm">{settings?.management_network || 'Not configured'}</p>
              </div>
              <div>
                <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Attack Network</label>
                <p className="font-medium mt-1 text-sm">{settings?.attack_network || 'Not configured'}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-xs md:text-sm flex items-center gap-2">
                <TrendingUp className="h-4 w-4" aria-hidden="true" />
                Performance
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 md:space-y-4">
              <div>
                <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Safe Mode</label>
                <Badge variant={settings?.safe_mode ? 'success' : 'secondary'} className="mt-1 text-[10px]">
                  {settings?.safe_mode ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              <div>
                <label className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">Max Concurrent Tasks</label>
                <p className="font-medium mt-1 text-sm">{settings?.max_concurrent_tasks ?? 'Not configured'}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// Main App
function AppContent() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [containers, setContainers] = useState<Container[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [wsStatusDismissed, setWsStatusDismissed] = useState(false);
  const isOnline = useOnlineStatus();
  
  // Loading and error states
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingContainers, setIsLoadingContainers] = useState(true);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [containersError, setContainersError] = useState<string | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  
  const [redSteps, setRedSteps] = useState<RedStep[]>([]);
  const [redFindings, setRedFindings] = useState<Finding[]>([]);
  const [blueDetections, setBlueDetections] = useState<Detection[]>([]);
  const [blueActions, setBlueActions] = useState<BlueAction[]>([]);
  const [events, setEvents] = useState<WebSocketEvent[]>([]);

  // WebSocket connection with enhanced error handling
  const { 
    isConnected: wsConnected, 
    events: wsEvents, 
    isReconnecting,
    reconnectAttempts,
    reconnectCountdown,
    lastError: wsError,
    reconnect: wsReconnect,
  } = useWebSocket({
    sessionId: activeSessionId || '',
    maxReconnectAttempts: 10,
    onEvent: (event: WebSocketEvent) => {
      const eventWithId = { ...event, id: event.id || generateId() };
      setEvents(prev => [...prev.slice(-199), eventWithId]);
      
      if (event.agent === 'red') {
        if (event.type === 'step') {
          const stepData = event.data as unknown as RedStep;
          setRedSteps(prev => [...prev, { ...stepData, id: generateId() }]);
        } else if (event.type === 'finding') {
          const findingData = event.data as unknown as Finding;
          setRedFindings(prev => [...prev, { ...findingData, id: generateId() }]);
        }
      } else if (event.agent === 'blue') {
        if (event.type === 'detection') {
          const detectionData = event.data as unknown as Detection;
          setBlueDetections(prev => [...prev, { ...detectionData, id: generateId() }]);
        } else if (event.type === 'action') {
          const actionData = event.data as unknown as BlueAction;
          setBlueActions(prev => [...prev, { ...actionData, id: generateId() }]);
        }
      }
    },
    onConnect: () => setIsConnected(true),
    onDisconnect: () => setIsConnected(false),
  });

  // Fetch initial data
  useEffect(() => {
    setIsLoadingSessions(true);
    setIsLoadingContainers(true);
    setSessionsError(null);
    setContainersError(null);
    
    api.getSessions()
      .then(setSessions)
      .catch((err) => {
        console.error('Failed to fetch sessions:', err);
        setSessionsError(err.message || 'Failed to load sessions');
        setSessions([]);
      })
      .finally(() => setIsLoadingSessions(false));
    
    api.getContainers()
      .then(setContainers)
      .catch((err) => {
        console.error('Failed to fetch containers:', err);
        setContainersError(err.message || 'Failed to load containers');
        setContainers([]);
      })
      .finally(() => setIsLoadingContainers(false));
    
    api.health()
      .then(() => setIsConnected(true))
      .catch(() => setIsConnected(false));
  }, []);

  // Fetch metrics globally (not just when session is active)
  const fetchMetrics = useCallback(async () => {
    setIsLoadingMetrics(true);
    setMetricsError(null);
    try {
      const data = await api.getMetrics(activeSessionId || undefined);
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
      setMetricsError(err instanceof Error ? err.message : 'Failed to load metrics');
    } finally {
      setIsLoadingMetrics(false);
    }
  }, [activeSessionId]);

  // Initial metrics fetch and periodic refresh
  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  // Refresh sessions periodically
  useEffect(() => {
    const interval = setInterval(() => {
      api.getSessions()
        .then(setSessions)
        .catch((err) => console.error('Failed to refresh sessions:', err));
    }, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  // Fetch findings when session is selected
  useEffect(() => {
    if (activeSessionId) {
      api.getSessionFindings(activeSessionId)
        .then((data) => {
          if (data.red_findings) {
            setRedFindings(data.red_findings.map(f => ({ ...f, id: generateId() })));
          }
          if (data.blue_detections) {
            setBlueDetections(data.blue_detections.map(d => ({ ...d, id: generateId() })));
          }
        })
        .catch((err) => console.error('Failed to fetch findings:', err));
    }
  }, [activeSessionId]);

  // Wrap callbacks in useCallback
  const createSession = useCallback(async () => {
    const target = prompt('Enter target IP or domain:');
    if (!target) return;
    
    try {
      const session = await api.createSession(target);
      setSessions(prev => [session, ...prev]);
      setActiveSessionId(session.id);
      setActiveTab('red');
      setIsMobileMenuOpen(false);
      
      // Auto-start the session after creation
      await api.startSession(session.id);
      setSessions(prev => 
        prev.map(s => s.id === session.id ? { ...s, status: 'running' } : s)
      );
    } catch (error) {
      console.error('Failed to create/start session:', error);
    }
  }, []);

  const handleStartAttack = useCallback(async () => {
    if (!activeSessionId) return;
    await api.startSession(activeSessionId);
    setSessions(prev => 
      prev.map(s => s.id === activeSessionId ? { ...s, status: 'running' } : s)
    );
  }, [activeSessionId]);

  const handlePauseAttack = useCallback(async () => {
    if (!activeSessionId) return;
    await api.pauseSession(activeSessionId);
    setSessions(prev => 
      prev.map(s => s.id === activeSessionId ? { ...s, status: 'paused' } : s)
    );
  }, [activeSessionId]);

  const handleStopAttack = useCallback(async () => {
    if (!activeSessionId) return;
    await api.stopSession(activeSessionId);
    setSessions(prev => 
      prev.map(s => s.id === activeSessionId ? { ...s, status: 'completed' } : s)
    );
  }, [activeSessionId]);

  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab);
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    setActiveTab('red');
  }, []);

  const handleMobileMenuToggle = useCallback(() => {
    setIsMobileMenuOpen(prev => !prev);
  }, []);

  const handleMobileMenuClose = useCallback(() => {
    setIsMobileMenuOpen(false);
  }, []);

  const handleSettingsClick = useCallback(() => {
    setActiveTab('settings');
  }, []);

  const activeSession = sessions.find(s => s.id === activeSessionId);

  // Compute system health from container data
  const systemHealth = useMemo(() => {
    const blueContainer = containers.find(c => c.type === 'blue');
    return {
      cpu: blueContainer?.cpu ?? 0,
      memory: blueContainer?.memory ?? 0,
      network: Math.round(((blueContainer?.network?.rx ?? 0) + (blueContainer?.network?.tx ?? 0)) / 1000), // Convert to percentage-like value
    };
  }, [containers]);

  // Handler for WebSocket status dismiss
  const handleWsStatusDismiss = useCallback(() => {
    setWsStatusDismissed(true);
  }, []);

  // Handler for manual reconnect
  const handleWsReconnect = useCallback(() => {
    setWsStatusDismissed(false);
    wsReconnect();
  }, [wsReconnect]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Animated background - works for both themes */}
      <div className="fixed inset-0 -z-10" aria-hidden="true">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-purple-500/5 to-background" />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiM4YjVjZjYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyek0zNiAyNHYySDI0di0yaDEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30 dark:opacity-50" />
      </div>

      {/* Offline indicator - shows when browser is offline */}
      <OfflineIndicator />

      {/* Live region for WebSocket status announcements */}
      <div 
        role="status" 
        aria-live="polite" 
        aria-atomic="true"
        className="sr-only"
      >
        {isConnected ? 'Connected to server' : 'Disconnected from server'}
        {events.length > 0 && `${events.length} events received`}
        {isReconnecting && `Reconnecting, attempt ${reconnectAttempts}`}
        {wsError && `Connection error: ${wsError}`}
      </div>

      <Header 
        isConnected={isConnected && isOnline} 
        onSettingsClick={handleSettingsClick}
        onMenuToggle={handleMobileMenuToggle}
        isMobileMenuOpen={isMobileMenuOpen}
      />
      
      <div className="flex h-[calc(100vh-3.5rem)]">
        <SidebarErrorBoundary>
          <Sidebar
            activeTab={activeTab}
            onTabChange={handleTabChange}
            redFindings={redFindings.length}
            blueFindings={blueDetections.length}
            isMobileOpen={isMobileMenuOpen}
            onMobileClose={handleMobileMenuClose}
          />
        </SidebarErrorBoundary>
        
        <main className="flex-1 min-w-0 overflow-hidden" role="main">
          {activeTab === 'dashboard' && (
            <DashboardErrorBoundary>
              <MainDashboard
                metrics={metrics}
                sessions={sessions}
                containers={containers}
                onCreateSession={createSession}
                onSelectSession={handleSelectSession}
                isLoadingSessions={isLoadingSessions}
                isLoadingContainers={isLoadingContainers}
                isLoadingMetrics={isLoadingMetrics}
                sessionsError={sessionsError}
                containersError={containersError}
                metricsError={metricsError}
              />
            </DashboardErrorBoundary>
          )}
          
          {activeTab === 'red' && (
            <AttackSimulationErrorBoundary>
              <AttackDashboard
                status={activeSession?.status || 'idle'}
                target={activeSession?.target || ''}
                steps={redSteps}
                findings={redFindings}
                onStart={handleStartAttack}
                onPause={handlePauseAttack}
                onStop={handleStopAttack}
              />
            </AttackSimulationErrorBoundary>
          )}
          
          {activeTab === 'blue' && (
            <AttackSimulationErrorBoundary>
              <DefenseDashboard
                status={activeSession?.status || 'idle'}
                detections={blueDetections}
                actions={blueActions}
                systemHealth={systemHealth}
              />
            </AttackSimulationErrorBoundary>
          )}

          {activeTab === 'docker' && (
            <DashboardErrorBoundary>
              <DockerDashboard containers={containers} />
            </DashboardErrorBoundary>
          )}

          {activeTab === 'learning' && (
            <DashboardErrorBoundary>
              <LearningDashboard 
                sessionId={activeSessionId}
                findings={[...redFindings, ...blueDetections]}
              />
            </DashboardErrorBoundary>
          )}

          {activeTab === 'network' && (
            <DashboardErrorBoundary>
              <NetworkTopology containers={containers} />
            </DashboardErrorBoundary>
          )}
          
          {activeTab === 'findings' && (
            <FindingsErrorBoundary>
              <FindingsView redFindings={redFindings} blueFindings={blueDetections} />
            </FindingsErrorBoundary>
          )}
          
          {activeTab === 'logs' && <LogsView events={events} />}
          
          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>

      {/* WebSocket Connection Status */}
      {!wsStatusDismissed && (
        <WebSocketStatus
          isConnected={isConnected && isOnline}
          isReconnecting={isReconnecting}
          reconnectAttempts={reconnectAttempts}
          maxReconnectAttempts={10}
          reconnectCountdown={reconnectCountdown}
          onReconnect={handleWsReconnect}
          onDismiss={handleWsStatusDismiss}
        />
      )}
    </div>
  );
}

// Main App with Error Boundary wrapper
export default function App() {
  return (
    <AppErrorBoundary>
      <AppContent />
    </AppErrorBoundary>
  );
}
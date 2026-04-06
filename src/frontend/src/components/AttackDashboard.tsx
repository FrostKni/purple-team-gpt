import { useState, useCallback } from 'react';
import { 
  Sword, 
  Play, 
  Pause, 
  Square, 
  Target, 
  Zap, 
  AlertTriangle,
  Terminal,
  Clock,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

// Proper interfaces instead of inline types
interface AttackStep {
  step_num: number;
  action: string;
  description: string;
  result?: string;
  success: boolean;
  timestamp: string;
  id?: string;
}

interface Finding {
  id?: string;
  title: string;
  severity: string;
  description: string;
}

interface AttackDashboardProps {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'pending' | 'error';
  target: string;
  steps: AttackStep[];
  findings: Finding[];
  onStart: () => void;
  onPause: () => void;
  onStop: () => void;
}

const severityColors: Record<string, string> = {
  Critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  Low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  Info: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

// Generate unique ID for items
const generateId = (): string => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export function AttackDashboard({
  status,
  target,
  steps,
  findings,
  onStart,
  onPause,
  onStop,
}: AttackDashboardProps) {
  const [targetInput, setTargetInput] = useState(target);

  // Wrap handlers in useCallback
  const handleTargetChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setTargetInput(e.target.value);
  }, []);

  const handleStart = useCallback(() => {
    onStart();
  }, [onStart]);

  const handlePause = useCallback(() => {
    onPause();
  }, [onPause]);

  const handleStop = useCallback(() => {
    onStop();
  }, [onStop]);

  // Ensure unique IDs for steps and findings
  const stepsWithIds = steps.map((step, index) => ({
    ...step,
    id: step.id || `step-${index}-${generateId()}`
  }));

  const findingsWithIds = findings.map((finding, index) => ({
    ...finding,
    id: finding.id || `finding-${index}-${generateId()}`
  }));

  return (
    <div className="h-full flex flex-col gap-3 md:gap-4 p-3 md:p-4" role="region" aria-label="Red Agent Attack Dashboard">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-red/20 border border-red/30" aria-hidden="true">
            <Sword className="h-5 w-5 text-red" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold">Red Agent - Offensive</h2>
            <p className="text-xs text-muted-foreground">Autonomous penetration testing</p>
          </div>
        </div>
        <Badge 
          variant={status === 'running' ? 'success' : status === 'paused' ? 'warning' : 'secondary'}
          className="flex items-center gap-1.5 self-start sm:self-auto"
          role="status"
          aria-live="polite"
        >
          <div
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              status === 'running' ? "bg-green-500 animate-pulse" : 
              status === 'paused' ? "bg-yellow-500" : "bg-gray-500"
            )}
            aria-hidden="true"
          />
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Badge>
      </header>

      {/* Target Input */}
      <Card className="glow-red">
        <CardContent className="p-3 md:p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex items-center gap-3 flex-1">
              <Target className="h-5 w-5 text-red flex-shrink-0" aria-hidden="true" />
              <label htmlFor="target-input" className="sr-only">
                Target IP or domain
              </label>
              <input
                id="target-input"
                name="target"
                type="text"
                value={targetInput}
                onChange={handleTargetChange}
                placeholder="Enter target IP or domain"
                className="flex-1 bg-transparent border-none outline-none text-sm min-w-0 focus:ring-2 focus:ring-purple-500/50 rounded px-2 py-1"
                disabled={status === 'running'}
                aria-describedby="target-help"
              />
            </div>
            <div id="target-help" className="sr-only">
              Enter the IP address or domain name of the target system to attack
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {status === 'idle' && (
                <Button 
                  variant="red" 
                  size="sm" 
                  onClick={handleStart} 
                  className="gap-1.5 min-h-[44px] min-w-[44px]"
                  aria-label="Start attack"
                >
                  <Play className="h-4 w-4" aria-hidden="true" />
                  <span className="hidden sm:inline">Start Attack</span>
                  <span className="sm:hidden">Start</span>
                </Button>
              )}
              {status === 'running' && (
                <>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handlePause} 
                    className="gap-1.5 min-h-[44px] min-w-[44px]"
                    aria-label="Pause attack"
                  >
                    <Pause className="h-4 w-4" aria-hidden="true" />
                    <span className="hidden sm:inline">Pause</span>
                  </Button>
                  <Button 
                    variant="destructive" 
                    size="sm" 
                    onClick={handleStop} 
                    className="gap-1.5 min-h-[44px] min-w-[44px]"
                    aria-label="Stop attack"
                  >
                    <Square className="h-4 w-4" aria-hidden="true" />
                    <span className="hidden sm:inline">Stop</span>
                  </Button>
                </>
              )}
              {status === 'paused' && (
                <>
                  <Button 
                    variant="red" 
                    size="sm" 
                    onClick={handleStart} 
                    className="gap-1.5 min-h-[44px] min-w-[44px]"
                    aria-label="Resume attack"
                  >
                    <Play className="h-4 w-4" aria-hidden="true" />
                    <span className="hidden sm:inline">Resume</span>
                  </Button>
                  <Button 
                    variant="destructive" 
                    size="sm" 
                    onClick={handleStop}
                    className="min-h-[44px] min-w-[44px]"
                    aria-label="Stop attack"
                  >
                    <Square className="h-4 w-4" aria-hidden="true" />
                    <span className="hidden sm:inline">Stop</span>
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3" role="region" aria-label="Attack statistics">
        <Card>
          <CardContent className="p-2 md:p-3 text-center">
            <p className="text-xl md:text-2xl font-bold text-red">{steps.length}</p>
            <p className="text-[10px] md:text-xs text-muted-foreground">Steps</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-2 md:p-3 text-center">
            <p className="text-xl md:text-2xl font-bold text-orange-500">
              {findings.filter(f => f.severity === 'Critical' || f.severity === 'High').length}
            </p>
            <p className="text-[10px] md:text-xs text-muted-foreground">Critical/High</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-2 md:p-3 text-center">
            <p className="text-xl md:text-2xl font-bold text-yellow-500">{findings.length}</p>
            <p className="text-[10px] md:text-xs text-muted-foreground">Total Findings</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-2 md:p-3 text-center">
            <p className="text-xl md:text-2xl font-bold text-green-500">
              {steps.filter(s => s.success).length}
            </p>
            <p className="text-[10px] md:text-xs text-muted-foreground">Successful</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4 min-h-0">
        {/* Steps Log */}
        <Card className="flex flex-col min-h-[200px] lg:min-h-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Terminal className="h-4 w-4 text-red" aria-hidden="true" />
              Attack Steps
              {steps.length > 0 && (
                <Badge variant="outline" className="ml-auto text-[10px]">{steps.length}</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full pr-2 md:pr-4">
              <div className="space-y-2" role="list" aria-label="Attack steps">
                {stepsWithIds.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm py-8" role="status">
                    <Zap className="h-8 w-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
                    <p>No attack steps yet</p>
                    <p className="text-xs">Start an attack to see live progress</p>
                  </div>
                ) : (
                  stepsWithIds.map((step) => (
                    <div
                      key={step.id}
                      role="listitem"
                      className={cn(
                        "flex items-start gap-2 p-2 rounded-lg text-xs",
                        step.success ? "bg-green-500/10" : "bg-red-500/10"
                      )}
                    >
                      {step.success ? (
                        <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-muted-foreground">#{step.step_num}</span>
                          <span className="font-medium">{step.action}</span>
                        </div>
                        <p className="text-muted-foreground truncate">{step.description}</p>
                      </div>
                      <Clock className="h-3 w-3 text-muted-foreground flex-shrink-0" aria-hidden="true" />
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Findings */}
        <Card className="flex flex-col min-h-[200px] lg:min-h-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" aria-hidden="true" />
              Vulnerabilities Found
              {findings.length > 0 && (
                <Badge variant="outline" className="ml-auto text-[10px]">{findings.length}</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full pr-2 md:pr-4">
              <div className="space-y-2" role="list" aria-label="Vulnerabilities found">
                {findingsWithIds.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm py-8" role="status">
                    <Target className="h-8 w-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
                    <p>No findings yet</p>
                  </div>
                ) : (
                  findingsWithIds.map((finding) => (
                    <div
                      key={finding.id}
                      role="listitem"
                      className="p-3 rounded-lg border bg-card hover:bg-secondary/50 transition-colors cursor-pointer min-h-[44px]"
                      tabIndex={0}
                    >
                      <div className="flex items-center justify-between mb-1 gap-2">
                        <span className="font-medium text-sm truncate">{finding.title}</span>
                        <Badge 
                          variant="outline" 
                          className={cn("text-[10px] flex-shrink-0", severityColors[finding.severity])}
                        >
                          {finding.severity}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {finding.description}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
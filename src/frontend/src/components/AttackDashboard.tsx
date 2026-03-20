import { useState } from 'react';
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

interface AttackDashboardProps {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'pending' | 'error';
  target: string;
  steps: Array<{
    step_num: number;
    action: string;
    description: string;
    result?: string;
    success: boolean;
    timestamp: string;
  }>;
  findings: Array<{
    title: string;
    severity: string;
    description: string;
  }>;
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

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-red/20 border border-red/30">
            <Sword className="h-5 w-5 text-red" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Red Agent - Offensive</h2>
            <p className="text-xs text-muted-foreground">Autonomous penetration testing</p>
          </div>
        </div>
        <Badge 
          variant={status === 'running' ? 'success' : status === 'paused' ? 'warning' : 'secondary'}
          className="flex items-center gap-1.5"
        >
          <div className={cn(
            "w-1.5 h-1.5 rounded-full",
            status === 'running' ? "bg-green-500 animate-pulse" : 
            status === 'paused' ? "bg-yellow-500" : "bg-gray-500"
          )} />
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Badge>
      </div>

      {/* Target Input */}
      <Card className="glow-red">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <Target className="h-5 w-5 text-red" />
            <input
              type="text"
              value={targetInput}
              onChange={(e) => setTargetInput(e.target.value)}
              placeholder="Enter target IP or domain"
              className="flex-1 bg-transparent border-none outline-none text-sm"
              disabled={status === 'running'}
            />
            <div className="flex items-center gap-2">
              {status === 'idle' && (
                <Button variant="red" size="sm" onClick={onStart} className="gap-1.5">
                  <Play className="h-4 w-4" />
                  Start Attack
                </Button>
              )}
              {status === 'running' && (
                <>
                  <Button variant="outline" size="sm" onClick={onPause} className="gap-1.5">
                    <Pause className="h-4 w-4" />
                    Pause
                  </Button>
                  <Button variant="destructive" size="sm" onClick={onStop} className="gap-1.5">
                    <Square className="h-4 w-4" />
                    Stop
                  </Button>
                </>
              )}
              {status === 'paused' && (
                <>
                  <Button variant="red" size="sm" onClick={onStart} className="gap-1.5">
                    <Play className="h-4 w-4" />
                    Resume
                  </Button>
                  <Button variant="destructive" size="sm" onClick={onStop}>
                    Stop
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-red">{steps.length}</p>
            <p className="text-xs text-muted-foreground">Steps</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-orange-500">
              {findings.filter(f => f.severity === 'Critical' || f.severity === 'High').length}
            </p>
            <p className="text-xs text-muted-foreground">Critical/High</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-yellow-500">{findings.length}</p>
            <p className="text-xs text-muted-foreground">Total Findings</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-green-500">
              {steps.filter(s => s.success).length}
            </p>
            <p className="text-xs text-muted-foreground">Successful</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        {/* Steps Log */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Terminal className="h-4 w-4 text-red" />
              Attack Steps
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-2">
                {steps.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm py-8">
                    <Zap className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No attack steps yet</p>
                    <p className="text-xs">Start an attack to see live progress</p>
                  </div>
                ) : (
                  steps.map((step, i) => (
                    <div
                      key={i}
                      className={cn(
                        "flex items-start gap-2 p-2 rounded-lg text-xs",
                        step.success ? "bg-green-500/10" : "bg-red-500/10"
                      )}
                    >
                      {step.success ? (
                        <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-muted-foreground">#{step.step_num}</span>
                          <span className="font-medium">{step.action}</span>
                        </div>
                        <p className="text-muted-foreground truncate">{step.description}</p>
                      </div>
                      <Clock className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Findings */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              Vulnerabilities Found
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-2">
                {findings.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm py-8">
                    <Target className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No findings yet</p>
                  </div>
                ) : (
                  findings.map((finding, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg border bg-card hover:bg-secondary/50 transition-colors cursor-pointer"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{finding.title}</span>
                        <Badge 
                          variant="outline" 
                          className={cn("text-[10px]", severityColors[finding.severity])}
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
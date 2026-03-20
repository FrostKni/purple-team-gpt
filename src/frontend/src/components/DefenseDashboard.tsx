import { 
  Shield, 
  AlertTriangle,
  Terminal,
  Lock,
  Eye,
  CheckCircle,
  Activity,
  Server,
  Wifi,
  Clock
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

interface DefenseDashboardProps {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'pending' | 'error';
  detections: Array<{
    title: string;
    severity: string;
    description: string;
    timestamp: string;
  }>;
  actions: Array<{
    action: string;
    description: string;
    success: boolean;
    timestamp: string;
  }>;
  systemHealth: {
    cpu: number;
    memory: number;
    network: number;
  };
}

export function DefenseDashboard({
  status,
  detections,
  actions,
  systemHealth,
}: DefenseDashboardProps) {
  return (
    <div className="h-full flex flex-col gap-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue/20 border border-blue/30">
            <Shield className="h-5 w-5 text-blue" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Blue Agent - Defensive</h2>
            <p className="text-xs text-muted-foreground">Real-time threat detection & response</p>
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
          {status === 'running' ? 'Monitoring' : status.charAt(0).toUpperCase() + status.slice(1)}
        </Badge>
      </div>

      {/* System Health */}
      <Card className="glow-blue">
        <CardContent className="p-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Server className="h-3.5 w-3.5" />
                  CPU
                </span>
                <span className={cn(
                  "font-mono",
                  systemHealth.cpu > 80 ? "text-red-500" : 
                  systemHealth.cpu > 50 ? "text-yellow-500" : "text-green-500"
                )}>
                  {systemHealth.cpu}%
                </span>
              </div>
              <Progress 
                value={systemHealth.cpu} 
                className="h-1.5"
                indicatorClassName={cn(
                  systemHealth.cpu > 80 ? "bg-red-500" : 
                  systemHealth.cpu > 50 ? "bg-yellow-500" : "bg-green-500"
                )}
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Activity className="h-3.5 w-3.5" />
                  Memory
                </span>
                <span className={cn(
                  "font-mono",
                  systemHealth.memory > 80 ? "text-red-500" : 
                  systemHealth.memory > 50 ? "text-yellow-500" : "text-green-500"
                )}>
                  {systemHealth.memory}%
                </span>
              </div>
              <Progress 
                value={systemHealth.memory} 
                className="h-1.5"
                indicatorClassName={cn(
                  systemHealth.memory > 80 ? "bg-red-500" : 
                  systemHealth.memory > 50 ? "bg-yellow-500" : "bg-green-500"
                )}
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Wifi className="h-3.5 w-3.5" />
                  Network
                </span>
                <span className={cn(
                  "font-mono",
                  systemHealth.network > 80 ? "text-red-500" : 
                  systemHealth.network > 50 ? "text-yellow-500" : "text-green-500"
                )}>
                  {systemHealth.network}%
                </span>
              </div>
              <Progress 
                value={systemHealth.network} 
                className="h-1.5"
                indicatorClassName={cn(
                  systemHealth.network > 80 ? "bg-red-500" : 
                  systemHealth.network > 50 ? "bg-yellow-500" : "bg-green-500"
                )}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-blue">{detections.length}</p>
            <p className="text-xs text-muted-foreground">Detections</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-green-500">
              {actions.filter(a => a.success).length}
            </p>
            <p className="text-xs text-muted-foreground">Blocked</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-purple-500">{actions.length}</p>
            <p className="text-xs text-muted-foreground">Actions</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <div className="flex items-center justify-center gap-1.5">
              <Lock className="h-5 w-5 text-green-500" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">Protected</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        {/* Detections */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Eye className="h-4 w-4 text-blue" />
              Threat Detections
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-2">
                {detections.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm py-8">
                    <Shield className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No threats detected</p>
                    <p className="text-xs">System is secure</p>
                  </div>
                ) : (
                  detections.map((detection, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg border bg-card hover:bg-secondary/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-orange-500" />
                          {detection.title}
                        </span>
                        <Badge variant="warning" className="text-[10px]">
                          {detection.severity}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {detection.description}
                      </p>
                      <div className="flex items-center gap-1.5 mt-2 text-[10px] text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {new Date(detection.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Defense Actions */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Terminal className="h-4 w-4 text-green-500" />
              Defense Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-2">
                {actions.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm py-8">
                    <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No defense actions yet</p>
                    <p className="text-xs">Monitoring for threats...</p>
                  </div>
                ) : (
                  actions.map((action, i) => (
                    <div
                      key={i}
                      className={cn(
                        "flex items-start gap-2 p-2 rounded-lg text-xs",
                        action.success ? "bg-green-500/10" : "bg-yellow-500/10"
                      )}
                    >
                      <CheckCircle className={cn(
                        "h-4 w-4 mt-0.5 flex-shrink-0",
                        action.success ? "text-green-500" : "text-yellow-500"
                      )} />
                      <div className="flex-1 min-w-0">
                        <span className="font-medium">{action.action}</span>
                        <p className="text-muted-foreground truncate">{action.description}</p>
                      </div>
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
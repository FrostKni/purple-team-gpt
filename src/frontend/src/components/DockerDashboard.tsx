import { useState, useEffect } from 'react';
import {
  Container as ContainerIcon,
  Play,
  Square,
  RotateCw,
  Terminal,
  Cpu,
  HardDrive,
  Network,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Copy,
  Settings,
  Trash2
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

interface Container {
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

interface DockerDashboardProps {
  containers: Container[];
}

const containerConfig = {
  orchestrator: {
    icon: Activity,
    color: 'purple',
    gradient: 'from-purple-600 to-pink-600',
    bgGradient: 'from-purple-500/10 to-transparent',
    borderColor: 'border-purple-500/30',
    description: 'Central coordination service',
    defaultPort: '8000',
  },
  red: {
    icon: ContainerIcon,
    color: 'red',
    gradient: 'from-red-600 to-orange-600',
    bgGradient: 'from-red-500/10 to-transparent',
    borderColor: 'border-red-500/30',
    description: 'Kali Linux • 50+ offensive tools',
    defaultPort: '8001',
  },
  blue: {
    icon: ContainerIcon,
    color: 'blue',
    gradient: 'from-blue-600 to-cyan-600',
    bgGradient: 'from-blue-500/10 to-transparent',
    borderColor: 'border-blue-500/30',
    description: 'Ubuntu Server • 50+ defensive tools',
    defaultPort: '8002',
  },
  chromadb: {
    icon: HardDrive,
    color: 'yellow',
    gradient: 'from-yellow-600 to-orange-600',
    bgGradient: 'from-yellow-500/10 to-transparent',
    borderColor: 'border-yellow-500/30',
    description: 'Vector database for learning',
    defaultPort: '8003',
  },
  redis: {
    icon: Network,
    color: 'orange',
    gradient: 'from-orange-600 to-red-600',
    bgGradient: 'from-orange-500/10 to-transparent',
    borderColor: 'border-orange-500/30',
    description: 'Message queue & caching',
    defaultPort: '6379',
  },
};

export function DockerDashboard({ containers: initialContainers }: DockerDashboardProps) {
  const [containers, setContainers] = useState<Container[]>(initialContainers);
  const [selectedContainer, setSelectedContainer] = useState<Container | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  // Simulated real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setContainers(prev => prev.map(c => ({
        ...c,
        cpu: c.status === 'running' ? Math.min(100, Math.max(0, c.cpu + (Math.random() - 0.5) * 10)) : 0,
        memory: c.status === 'running' ? Math.min(100, Math.max(0, c.memory + (Math.random() - 0.5) * 5)) : 0,
        network: {
          rx: c.status === 'running' ? c.network.rx + Math.floor(Math.random() * 1000) : 0,
          tx: c.status === 'running' ? c.network.tx + Math.floor(Math.random() * 500) : 0,
        },
      })));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const handleContainerAction = async (containerId: string, action: 'start' | 'stop' | 'restart') => {
    setIsLoading(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setContainers(prev => prev.map(c => {
      if (c.id === containerId) {
        return {
          ...c,
          status: action === 'start' ? 'running' : action === 'stop' ? 'stopped' : 'running',
          uptime: action === 'start' ? '0s' : c.uptime,
        };
      }
      return c;
    }));
    
    setIsLoading(false);
  };

  const totalCpu = containers.reduce((acc, c) => acc + (c.status === 'running' ? c.cpu : 0), 0);
  const totalMemory = containers.reduce((acc, c) => acc + (c.status === 'running' ? c.memory : 0), 0);
  const runningCount = containers.filter(c => c.status === 'running').length;

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
            Container Management
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage and monitor Docker containers
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" className="gap-2" onClick={() => setContainers(initialContainers)}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-medium text-green-400">
              {runningCount}/{containers.length} Running
            </span>
          </div>
        </div>
      </div>

      {/* Resource Overview */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Containers</p>
                <p className="text-2xl font-bold mt-1">{runningCount}/{containers.length}</p>
              </div>
              <ContainerIcon className="h-8 w-8 text-purple-500/30" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Total CPU</p>
                <p className="text-2xl font-bold mt-1">{totalCpu.toFixed(1)}%</p>
              </div>
              <Cpu className="h-8 w-8 text-blue-500/30" />
            </div>
            <Progress value={totalCpu} className="h-1.5 mt-2" />
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Total Memory</p>
                <p className="text-2xl font-bold mt-1">{totalMemory.toFixed(1)}%</p>
              </div>
              <HardDrive className="h-8 w-8 text-green-500/30" />
            </div>
            <Progress value={totalMemory} className="h-1.5 mt-2" />
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-orange-500/10 to-transparent border-orange-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Network I/O</p>
                <p className="text-2xl font-bold mt-1">
                  {containers.reduce((acc, c) => acc + c.network.rx, 0) / 1024 | 0} MB
                </p>
              </div>
              <Network className="h-8 w-8 text-orange-500/30" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-3 gap-4 min-h-0">
        {/* Container List */}
        <Card className="flex flex-col col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <ContainerIcon className="h-4 w-4 text-blue-400" />
              Containers
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <ScrollArea className="h-full">
              <div className="space-y-3">
                {containers.map((container) => {
                  const config = containerConfig[container.type as keyof typeof containerConfig] || containerConfig.orchestrator;
                  const Icon = config.icon;
                  
                  return (
                    <div
                      key={container.id}
                      className={cn(
                        "p-4 rounded-xl border transition-all cursor-pointer",
                        selectedContainer?.id === container.id 
                          ? `bg-gradient-to-br ${config.bgGradient} ${config.borderColor}` 
                          : "bg-card/50 hover:bg-card border-transparent hover:border-gray-500/20"
                      )}
                      onClick={() => setSelectedContainer(container)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={cn(
                            "p-2 rounded-lg bg-gradient-to-br",
                            config.gradient
                          )}>
                            <Icon className="h-5 w-5 text-white" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{container.name}</p>
                              <Badge 
                                variant={container.status === 'running' ? 'success' : container.status === 'error' ? 'destructive' : 'secondary'}
                                className="text-[10px]"
                              >
                                {container.status}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground">{config.description}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                          {/* Resource bars */}
                          <div className="flex items-center gap-4">
                            <div className="w-24">
                              <div className="flex items-center justify-between text-[10px] mb-1">
                                <span className="text-muted-foreground">CPU</span>
                                <span className={cn(
                                  container.cpu > 80 ? "text-red-400" : 
                                  container.cpu > 50 ? "text-yellow-400" : "text-green-400"
                                )}>
                                  {container.cpu.toFixed(0)}%
                                </span>
                              </div>
                              <Progress 
                                value={container.cpu} 
                                className="h-1"
                              />
                            </div>
                            <div className="w-24">
                              <div className="flex items-center justify-between text-[10px] mb-1">
                                <span className="text-muted-foreground">MEM</span>
                                <span className={cn(
                                  container.memory > 80 ? "text-red-400" : 
                                  container.memory > 50 ? "text-yellow-400" : "text-green-400"
                                )}>
                                  {container.memory.toFixed(0)}%
                                </span>
                              </div>
                              <Progress 
                                value={container.memory} 
                                className="h-1"
                              />
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-1">
                            {container.status === 'running' ? (
                              <>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleContainerAction(container.id, 'restart');
                                  }}
                                >
                                  <RotateCw className="h-4 w-4 text-yellow-500" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleContainerAction(container.id, 'stop');
                                  }}
                                >
                                  <Square className="h-4 w-4 text-red-500" />
                                </Button>
                              </>
                            ) : (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleContainerAction(container.id, 'start');
                                }}
                              >
                                <Play className="h-4 w-4 text-green-500" />
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Ports and Uptime */}
                      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-500/10">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Network className="h-3 w-3" />
                          {container.ports.map((port, i) => (
                            <Badge key={i} variant="outline" className="text-[10px] font-mono">
                              {port}
                            </Badge>
                          ))}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Activity className="h-3 w-3" />
                          Uptime: {container.uptime}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Container Details */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Settings className="h-4 w-4 text-gray-400" />
              Container Details
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            {selectedContainer ? (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-gradient-to-br from-gray-500/5 to-transparent border">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium">{selectedContainer.name}</span>
                    <Badge 
                      variant={selectedContainer.status === 'running' ? 'success' : 'secondary'}
                      className="text-xs"
                    >
                      {selectedContainer.status}
                    </Badge>
                  </div>
                  
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Image</span>
                      <span className="font-mono">{selectedContainer.image}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Container ID</span>
                      <span className="font-mono text-[10px]">{selectedContainer.id.slice(0, 12)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Uptime</span>
                      <span>{selectedContainer.uptime}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Quick Actions</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <Button variant="outline" size="sm" className="gap-2">
                      <Terminal className="h-4 w-4" />
                      Shell
                    </Button>
                    <Button variant="outline" size="sm" className="gap-2">
                      <ExternalLink className="h-4 w-4" />
                      Open
                    </Button>
                    <Button variant="outline" size="sm" className="gap-2">
                      <Copy className="h-4 w-4" />
                      Copy ID
                    </Button>
                    <Button variant="outline" size="sm" className="gap-2 text-red-400 hover:text-red-300">
                      <Trash2 className="h-4 w-4" />
                      Remove
                    </Button>
                  </div>
                </div>

                {selectedContainer.tools && (
                  <div className="space-y-2">
                    <span className="text-sm font-medium">Available Tools</span>
                    <ScrollArea className="h-32">
                      <div className="flex flex-wrap gap-1">
                        {selectedContainer.tools.map((tool, i) => (
                          <Badge key={i} variant="outline" className="text-[10px]">
                            {tool}
                          </Badge>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}

                <div className="space-y-2">
                  <span className="text-sm font-medium">Network Stats</span>
                  <div className="p-3 rounded-lg bg-black/20 font-mono text-xs space-y-1">
                    <div className="flex items-center justify-between text-green-400">
                      <span>RX</span>
                      <span>{(selectedContainer.network.rx / 1024).toFixed(2)} KB</span>
                    </div>
                    <div className="flex items-center justify-between text-blue-400">
                      <span>TX</span>
                      <span>{(selectedContainer.network.tx / 1024).toFixed(2)} KB</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <ContainerIcon className="h-12 w-12 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">Select a container</p>
                  <p className="text-xs">to view details</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
import { useState } from 'react';
import {
  Network as NetworkIcon,
  Server,
  Shield,
  Sword,
  Database,
  Wifi,
  ArrowRight,
  Circle,
  Activity,
  CheckCircle2,
  AlertCircle,
  Zap
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

interface Container {
  id: string;
  name: string;
  type: 'orchestrator' | 'red' | 'blue' | 'chromadb' | 'redis' | 'target';
  status: 'running' | 'stopped' | 'paused' | 'restarting' | 'error';
  ports?: string[];
}

interface NetworkTopologyProps {
  containers: Container[];
}

interface NetworkNode {
  id: string;
  name: string;
  type: string;
  status: string;
  ip: string;
  x: number;
  y: number;
}

interface NetworkConnection {
  from: string;
  to: string;
  type: 'management' | 'attack' | 'defense';
  animated?: boolean;
}

// Network layout positions
const nodePositions: Record<string, { x: number; y: number; ip: string }> = {
  orchestrator: { x: 400, y: 100, ip: '10.0.0.10' },
  red: { x: 200, y: 250, ip: '10.0.0.20' },
  blue: { x: 600, y: 250, ip: '10.0.0.30' },
  chromadb: { x: 200, y: 400, ip: '10.0.0.40' },
  redis: { x: 400, y: 400, ip: '10.0.0.50' },
  dvwa: { x: 100, y: 450, ip: '192.168.100.100' },
  metasploitable: { x: 100, y: 520, ip: '192.168.100.101' },
  production: { x: 700, y: 400, ip: '172.16.0.100' },
};

export function NetworkTopology({ containers }: NetworkTopologyProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredConnection, setHoveredConnection] = useState<string | null>(null);

  // Get container status
  const getContainerStatus = (type: string) => {
    const container = containers.find(c => c.type === type);
    return container?.status || 'stopped';
  };

  // Define connections
  const connections: NetworkConnection[] = [
    { from: 'orchestrator', to: 'red', type: 'management' },
    { from: 'orchestrator', to: 'blue', type: 'management' },
    { from: 'orchestrator', to: 'chromadb', type: 'management' },
    { from: 'orchestrator', to: 'redis', type: 'management' },
    { from: 'red', to: 'dvwa', type: 'attack', animated: true },
    { from: 'red', to: 'metasploitable', type: 'attack', animated: true },
    { from: 'blue', to: 'production', type: 'defense' },
  ];

  // Network zones
  const zones = [
    { name: 'Management', subnet: '10.0.0.0/24', color: 'purple', x: 150, y: 50, width: 500, height: 400 },
    { name: 'Attack', subnet: '192.168.100.0/24', color: 'red', x: 30, y: 380, width: 200, height: 200 },
    { name: 'Defense', subnet: '172.16.0.0/24', color: 'blue', x: 620, y: 320, width: 180, height: 180 },
  ];

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'orchestrator': return Activity;
      case 'red': return Sword;
      case 'blue': return Shield;
      case 'chromadb': return Database;
      case 'redis': return Database;
      case 'dvwa': return Server;
      case 'metasploitable': return Server;
      case 'production': return Server;
      default: return Server;
    }
  };

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'orchestrator': return 'purple';
      case 'red': return 'red';
      case 'blue': return 'blue';
      case 'chromadb': return 'yellow';
      case 'redis': return 'orange';
      case 'dvwa': return 'gray';
      case 'metasploitable': return 'gray';
      case 'production': return 'green';
      default: return 'gray';
    }
  };

  const getConnectionColor = (type: string) => {
    switch (type) {
      case 'management': return '#8b5cf6';
      case 'attack': return '#ef4444';
      case 'defense': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            Network Topology
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Visualize Docker network architecture and traffic flow
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-1 bg-purple-500/10 border-purple-500/30">
            <div className="w-2 h-2 rounded-full bg-purple-500" />
            Management
          </Badge>
          <Badge variant="outline" className="gap-1 bg-red-500/10 border-red-500/30">
            <div className="w-2 h-2 rounded-full bg-red-500" />
            Attack
          </Badge>
          <Badge variant="outline" className="gap-1 bg-blue-500/10 border-blue-500/30">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            Defense
          </Badge>
        </div>
      </div>

      {/* Topology View */}
      <div className="flex-1 grid grid-cols-4 gap-4 min-h-0">
        {/* SVG Network Diagram */}
        <Card className="col-span-3 overflow-hidden">
          <CardContent className="p-0 h-full">
            <svg
              viewBox="0 0 800 600"
              className="w-full h-full"
              style={{ minHeight: '400px' }}
            >
              {/* Background grid */}
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1"/>
                </pattern>
                
                {/* Glow filters */}
                <filter id="glow-purple" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
                <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
                <filter id="glow-blue" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>

                {/* Arrow marker */}
                <marker id="arrow-purple" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#8b5cf6"/>
                </marker>
                <marker id="arrow-red" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444"/>
                </marker>
                <marker id="arrow-blue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6"/>
                </marker>
              </defs>

              {/* Grid background */}
              <rect width="800" height="600" fill="url(#grid)" />

              {/* Network Zones */}
              {zones.map((zone) => (
                <g key={zone.name}>
                  <rect
                    x={zone.x}
                    y={zone.y}
                    width={zone.width}
                    height={zone.height}
                    fill={`url(#gradient-${zone.color})`}
                    opacity="0.1"
                    rx="10"
                    stroke={`var(--${zone.color}-500)`}
                    strokeWidth="1"
                    strokeDasharray="5,5"
                    strokeOpacity="0.3"
                  />
                  <text
                    x={zone.x + 10}
                    y={zone.y + 20}
                    fill={`var(--${zone.color}-400)`}
                    fontSize="10"
                    fontWeight="bold"
                  >
                    {zone.name} Network
                  </text>
                  <text
                    x={zone.x + 10}
                    y={zone.y + 35}
                    fill="rgba(255,255,255,0.5)"
                    fontSize="9"
                  >
                    {zone.subnet}
                  </text>
                </g>
              ))}

              {/* Connections */}
              {connections.map((conn, i) => {
                const from = nodePositions[conn.from];
                const to = nodePositions[conn.to];
                if (!from || !to) return null;

                return (
                  <g key={i}>
                    <line
                      x1={from.x}
                      y1={from.y}
                      x2={to.x}
                      y2={to.y}
                      stroke={getConnectionColor(conn.type)}
                      strokeWidth="2"
                      strokeDasharray={conn.animated ? "5,5" : "none"}
                      markerEnd={`url(#arrow-${conn.type})`}
                      opacity="0.6"
                      className={cn(
                        conn.animated && "animate-pulse"
                      )}
                    />
                    {conn.animated && (
                      <circle r="3" fill={getConnectionColor(conn.type)}>
                        <animateMotion
                          dur="2s"
                          repeatCount="indefinite"
                          path={`M${from.x},${from.y} L${to.x},${to.y}`}
                        />
                      </circle>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {Object.entries(nodePositions).map(([key, pos]) => {
                const status = getContainerStatus(key);
                const color = getNodeColor(key);
                const Icon = getNodeIcon(key);
                const isSelected = selectedNode === key;

                return (
                  <g
                    key={key}
                    onClick={() => setSelectedNode(key)}
                    className="cursor-pointer"
                  >
                    {/* Node glow */}
                    {status === 'running' && (
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r="35"
                        fill={`var(--${color}-500)`}
                        opacity="0.1"
                        className="animate-pulse"
                      />
                    )}

                    {/* Node circle */}
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r="28"
                      fill={`var(--${color}-900)`}
                      stroke={isSelected ? '#fff' : `var(--${color}-500)`}
                      strokeWidth={isSelected ? "3" : "2"}
                      filter={`url(#glow-${color})`}
                    />

                    {/* Status indicator */}
                    <circle
                      cx={pos.x + 20}
                      cy={pos.y - 20}
                      r="6"
                      fill={status === 'running' ? '#22c55e' : status === 'error' ? '#ef4444' : '#6b7280'}
                      stroke="#1e1e1e"
                      strokeWidth="2"
                    />

                    {/* Node label */}
                    <text
                      x={pos.x}
                      y={pos.y + 45}
                      textAnchor="middle"
                      fill="white"
                      fontSize="10"
                      fontWeight="bold"
                    >
                      {key.charAt(0).toUpperCase() + key.slice(1)}
                    </text>
                    <text
                      x={pos.x}
                      y={pos.y + 57}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.5)"
                      fontSize="8"
                    >
                      {pos.ip}
                    </text>
                  </g>
                );
              })}

              {/* Traffic animation legend */}
              <g transform="translate(650, 550)">
                <text fill="rgba(255,255,255,0.5)" fontSize="9">
                  ● Traffic flow
                </text>
              </g>
            </svg>
          </CardContent>
        </Card>

        {/* Node Details Panel */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-cyan-400" />
              Node Details
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1">
            {selectedNode ? (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-gradient-to-br from-gray-500/10 to-transparent border">
                  <div className="flex items-center gap-3 mb-3">
                    {(() => {
                      const Icon = getNodeIcon(selectedNode);
                      const color = getNodeColor(selectedNode);
                      return (
                        <div className={cn(
                          "p-2 rounded-lg",
                          `bg-${color}-500/20`
                        )}>
                          <Icon className={cn("h-5 w-5", `text-${color}-400`)} />
                        </div>
                      );
                    })()}
                    <div>
                      <p className="font-medium capitalize">{selectedNode}</p>
                      <p className="text-xs text-muted-foreground">
                        {nodePositions[selectedNode]?.ip}
                      </p>
                    </div>
                  </div>

                  <Badge 
                    variant={getContainerStatus(selectedNode) === 'running' ? 'success' : 'secondary'}
                    className="text-xs"
                  >
                    {getContainerStatus(selectedNode)}
                  </Badge>
                </div>

                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Connections</p>
                  {connections
                    .filter(c => c.from === selectedNode || c.to === selectedNode)
                    .map((conn, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <ArrowRight className={cn(
                          "h-3 w-3",
                          conn.type === 'attack' ? "text-red-400" :
                          conn.type === 'defense' ? "text-blue-400" : "text-purple-400"
                        )} />
                        <span>{conn.from === selectedNode ? conn.to : conn.from}</span>
                        <Badge variant="outline" className="text-[10px]">
                          {conn.type}
                        </Badge>
                      </div>
                    ))
                  }
                </div>

                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Network</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-black/20">
                      <p className="text-muted-foreground">RX</p>
                      <p className="font-mono text-green-400">12.4 MB</p>
                    </div>
                    <div className="p-2 rounded bg-black/20">
                      <p className="text-muted-foreground">TX</p>
                      <p className="font-mono text-blue-400">8.2 MB</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <NetworkIcon className="h-12 w-12 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">Select a node</p>
                  <p className="text-xs">to view details</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Traffic Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/20">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-purple-400" />
              <div>
                <p className="text-xs text-muted-foreground">Management Traffic</p>
                <p className="font-bold">2.4 GB</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-red-500/10 to-transparent border-red-500/20">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <Sword className="h-4 w-4 text-red-400" />
              <div>
                <p className="text-xs text-muted-foreground">Attack Traffic</p>
                <p className="font-bold">856 MB</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-blue-400" />
              <div>
                <p className="text-xs text-muted-foreground">Defense Logs</p>
                <p className="font-bold">12,450</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-400" />
              <div>
                <p className="text-xs text-muted-foreground">Active Connections</p>
                <p className="font-bold">47</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
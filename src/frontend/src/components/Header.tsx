import { Shield, Activity, Settings, Moon, Sun } from 'lucide-react';
import { Badge } from './ui/badge';
import { useState } from 'react';

interface HeaderProps {
  isConnected: boolean;
  version?: string;
}

export function Header({ isConnected, version = 'v0.1.0' }: HeaderProps) {
  const [isDark, setIsDark] = useState(true);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        {/* Logo */}
        <div className="flex items-center gap-3 mr-6">
          <div className="relative">
            <Shield className="h-7 w-7 text-purple-500" />
            <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Purple Team GPT
            </h1>
            <p className="text-[10px] text-muted-foreground -mt-0.5">Autonomous Cyber Simulation</p>
          </div>
        </div>

        {/* Center Stats */}
        <div className="flex-1 flex items-center justify-center gap-6">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/50">
            <Activity className="h-4 w-4 text-green-500" />
            <span className="text-xs text-muted-foreground">System</span>
            <Badge variant="success" className="text-[10px] px-1.5">Active</Badge>
          </div>
          
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/50">
            <span className="text-xs text-muted-foreground">Backend</span>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-xs">{isConnected ? 'Connected' : 'Offline'}</span>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px]">{version}</Badge>
          
          <button
            onClick={() => setIsDark(!isDark)}
            className="p-2 rounded-lg hover:bg-secondary transition-colors"
          >
            {isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </button>
          
          <button className="p-2 rounded-lg hover:bg-secondary transition-colors">
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
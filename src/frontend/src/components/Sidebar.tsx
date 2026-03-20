import { 
  Sword, 
  Shield, 
  Activity, 
  Target, 
  Settings, 
  LayoutDashboard,
  Bug,
  Radar
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Badge } from './ui/badge';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  redFindings: number;
  blueFindings: number;
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'red', label: 'Red Agent', icon: Sword, color: 'red' },
  { id: 'blue', label: 'Blue Agent', icon: Shield, color: 'blue' },
  { id: 'findings', label: 'Findings', icon: Bug },
  { id: 'logs', label: 'Live Logs', icon: Activity },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ activeTab, onTabChange, redFindings, blueFindings }: SidebarProps) {
  return (
    <aside className="w-16 lg:w-64 border-r bg-card flex flex-col">
      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                isActive
                  ? item.color === 'red'
                    ? "bg-red/20 text-red border border-red/30"
                    : item.color === 'blue'
                    ? "bg-blue/20 text-blue border border-blue/30"
                    : "bg-primary/20 text-primary border border-primary/30"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              <span className="hidden lg:block truncate">{item.label}</span>
              
              {/* Badges for findings */}
              {item.id === 'red' && redFindings > 0 && (
                <Badge variant="red" className="ml-auto hidden lg:flex">
                  {redFindings}
                </Badge>
              )}
              {item.id === 'blue' && blueFindings > 0 && (
                <Badge variant="blue" className="ml-auto hidden lg:flex">
                  {blueFindings}
                </Badge>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Status */}
      <div className="p-3 border-t hidden lg:block">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Radar className="h-4 w-4 text-purple-500 animate-pulse" />
          <span>Purple Team Active</span>
        </div>
      </div>
    </aside>
  );
}
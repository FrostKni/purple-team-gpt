import { useState, useCallback } from 'react';
import { 
  LayoutDashboard, 
  Sword, 
  Shield, 
  FileText, 
  Settings, 
  Terminal,
  Brain,
  Container,
  Network,
  Lightbulb,
  X
} from 'lucide-react';
import { cn } from '../lib/utils';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  redFindings: number;
  blueFindings: number;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigation: NavigationItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'red', label: 'Red Agent', icon: Sword },
  { id: 'blue', label: 'Blue Agent', icon: Shield },
  { id: 'docker', label: 'Containers', icon: Container },
  { id: 'network', label: 'Network', icon: Network },
  { id: 'learning', label: 'Learning', icon: Brain },
  { id: 'findings', label: 'Findings', icon: FileText },
  { id: 'logs', label: 'Live Logs', icon: Terminal },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ 
  activeTab, 
  onTabChange, 
  redFindings, 
  blueFindings,
  isMobileOpen = true,
  onMobileClose 
}: SidebarProps) {
  const getBadge = useCallback((id: string): React.ReactNode => {
    if (id === 'red' && redFindings > 0) {
      return (
        <span 
          className="sidebar-badge sidebar-badge-red"
          aria-label={`${redFindings} findings`}
        >
          {redFindings}
        </span>
      );
    }
    if (id === 'blue' && blueFindings > 0) {
      return (
        <span 
          className="sidebar-badge sidebar-badge-blue"
          aria-label={`${blueFindings} detections`}
        >
          {blueFindings}
        </span>
      );
    }
    return null;
  }, [redFindings, blueFindings]);

  const getItemClass = useCallback((id: string, isActive: boolean): string => {
    if (!isActive) return '';
    
    const colorMap: Record<string, string> = {
      'red': 'sidebar-item-red',
      'blue': 'sidebar-item-blue',
      'docker': 'sidebar-item-cyan',
      'network': 'sidebar-item-indigo',
      'learning': 'sidebar-item-green',
      'findings': 'sidebar-item-yellow',
      'default': 'sidebar-item-purple'
    };
    
    return `border ${colorMap[id] || colorMap['default']}`;
  }, []);

  const handleTabChange = useCallback((tabId: string) => {
    onTabChange(tabId);
    // Close mobile menu when a tab is selected
    if (onMobileClose) {
      onMobileClose();
    }
  }, [onTabChange, onMobileClose]);

  const renderNavigationItems = (items: NavigationItem[]) => {
    return items.map((item) => {
      const Icon = item.icon;
      const isActive = activeTab === item.id;
      
      return (
        <button
          key={item.id}
          onClick={() => handleTabChange(item.id)}
          className={cn(
            "sidebar-item min-h-[44px] focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:ring-offset-2 focus:ring-offset-background",
            isActive && getItemClass(item.id, true)
          )}
          role="menuitem"
          aria-current={isActive ? 'page' : undefined}
          aria-label={`${item.label}${item.id === 'red' && redFindings > 0 ? `, ${redFindings} findings` : ''}${item.id === 'blue' && blueFindings > 0 ? `, ${blueFindings} detections` : ''}`}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
          <span>{item.label}</span>
          {getBadge(item.id)}
        </button>
      );
    });
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}
      
      <aside 
        id="sidebar-navigation"
        className={cn(
          "sidebar fixed md:static inset-y-0 left-0 z-50 w-56 transform transition-transform duration-300 ease-in-out md:transform-none",
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="sidebar-header flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="sidebar-logo-icon" aria-hidden="true">
                <span className="text-white font-bold text-sm">PT</span>
              </div>
              <div>
                <p className="font-semibold text-sm text-foreground">Purple Team</p>
                <p className="text-[10px] text-muted-foreground">GPT Security</p>
              </div>
            </div>
            {/* Mobile close button */}
            <button
              onClick={onMobileClose}
              className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-secondary transition-colors md:hidden focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:ring-offset-2"
              aria-label="Close navigation menu"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav 
            className="flex-1 p-3 space-y-1 overflow-y-auto"
            role="menu"
            aria-label="Main menu"
          >
            <div className="mb-2 px-2">
              <p className="sidebar-section-label" id="nav-section-main">
                Main
              </p>
            </div>
            
            <div role="group" aria-labelledby="nav-section-main">
              {renderNavigationItems(navigation.slice(0, 3))}
            </div>

            <div className="sidebar-divider" role="separator" />

            <div className="mb-2 px-2">
              <p className="sidebar-section-label" id="nav-section-infra">
                Infrastructure
              </p>
            </div>
            
            <div role="group" aria-labelledby="nav-section-infra">
              {renderNavigationItems(navigation.slice(3, 6))}
            </div>

            <div className="sidebar-divider" role="separator" />

            <div className="mb-2 px-2">
              <p className="sidebar-section-label" id="nav-section-analysis">
                Analysis
              </p>
            </div>
            
            <div role="group" aria-labelledby="nav-section-analysis">
              {renderNavigationItems(navigation.slice(6))}
            </div>
          </nav>

          {/* Status Footer */}
          <div className="sidebar-footer-section">
            <div className="sidebar-status-box" role="status" aria-live="polite">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" aria-hidden="true" />
                <span className="sidebar-status-text">System Online</span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-[10px]">
                <div>
                  <p className="text-muted-foreground">Containers</p>
                  <p className="sidebar-status-value sidebar-status-green" aria-label="5 of 5 containers running">5/5</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Agents</p>
                  <p className="sidebar-status-value sidebar-status-blue" aria-label="2 of 2 agents active">2/2</p>
                </div>
              </div>
            </div>
          </div>

          {/* Tips */}
          <div className="sidebar-tips-section">
            <div className="sidebar-tip-box">
              <div className="flex items-start gap-2">
                <Lightbulb className="h-4 w-4 sidebar-tip-icon flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="sidebar-tip-text">
                  Tip: Use the Learning tab to provide feedback and improve agent performance
                </p>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
import { Shield, Activity, Settings, Moon, Sun, Menu } from 'lucide-react';
import { Badge } from './ui/badge';
import { useState, useEffect, useCallback } from 'react';

interface HeaderProps {
  isConnected: boolean;
  version?: string;
  onSettingsClick?: () => void;
  onMenuToggle?: () => void;
  isMobileMenuOpen?: boolean;
}

export function Header({ 
  isConnected, 
  version = 'v0.1.0', 
  onSettingsClick,
  onMenuToggle,
  isMobileMenuOpen 
}: HeaderProps) {
  const [isDark, setIsDark] = useState(() => {
    // Check localStorage or system preference on init
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme');
      if (stored) return stored === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return true;
  });

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      root.classList.remove('light');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      root.classList.add('light');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const toggleTheme = useCallback(() => {
    setIsDark(prev => !prev);
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center px-4 md:px-6">
        {/* Mobile Menu Button */}
        <button
          onClick={onMenuToggle}
          className="mr-2 flex h-11 w-11 items-center justify-center rounded-lg hover:bg-secondary transition-colors md:hidden focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:ring-offset-2"
          aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={isMobileMenuOpen}
          aria-controls="sidebar-navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Logo */}
        <div className="flex items-center gap-2 md:gap-3 mr-2 md:mr-6">
          <div className="relative" aria-hidden="true">
            <Shield className="h-6 w-6 md:h-7 md:w-7 text-purple-500" />
            <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-base md:text-lg font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Purple Team GPT
            </h1>
            <p className="text-[9px] md:text-[10px] text-muted-foreground -mt-0.5">Autonomous Cyber Simulation</p>
          </div>
        </div>

        {/* Center Stats */}
        <div className="flex-1 flex items-center justify-center gap-2 md:gap-6">
          <div className="flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1.5 rounded-lg bg-secondary/50">
            <Activity className="h-3.5 w-3.5 md:h-4 md:w-4 text-green-500" aria-hidden="true" />
            <span className="text-[10px] md:text-xs text-muted-foreground hidden sm:inline">System</span>
            <Badge variant="success" className="text-[9px] md:text-[10px] px-1 md:px-1.5">Active</Badge>
          </div>
          
          <div className="flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1.5 rounded-lg bg-secondary/50">
            <span className="text-[10px] md:text-xs text-muted-foreground hidden sm:inline">Backend</span>
            <div 
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}
              aria-hidden="true"
            />
            <span className="text-[10px] md:text-xs">{isConnected ? 'Connected' : 'Offline'}</span>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-1 md:gap-2">
          <Badge variant="outline" className="text-[9px] md:text-[10px] hidden sm:inline-flex">{version}</Badge>
          
          <button
            onClick={toggleTheme}
            className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:ring-offset-2"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="h-4 w-4 md:h-5 md:w-5" /> : <Moon className="h-4 w-4 md:h-5 md:w-5" />}
          </button>
          
          <button 
            onClick={onSettingsClick}
            className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:ring-offset-2"
            aria-label="Open settings"
            title="Open settings"
          >
            <Settings className="h-4 w-4 md:h-5 md:w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
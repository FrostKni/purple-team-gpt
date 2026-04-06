import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Send, Wifi, WifiOff, X, Home } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { cn } from '../lib/utils';

// Error info interface for error reporting
interface ErrorDetails {
  error: Error;
  errorInfo: ErrorInfo;
  timestamp: string;
  componentStack: string;
}

// Props for error boundary
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  onReset?: () => void;
  resetKeys?: unknown[];
  componentName?: string;
  level?: 'app' | 'component';
}

// State for error boundary
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
}

// Generate unique error ID for tracking
const generateErrorId = (): string => {
  return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Base Error Boundary Component
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error, errorId: generateErrorId() };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    
    // Log error to console in development
    if (import.meta.env.DEV) {
      console.error('Error caught by boundary:', error, errorInfo);
    }

    // Call optional error callback
    this.props.onError?.(error, errorInfo);

    // Store error for potential reporting
    const errorDetails: ErrorDetails = {
      error,
      errorInfo,
      timestamp: new Date().toISOString(),
      componentStack: errorInfo.componentStack || '',
    };
    
    // Store in sessionStorage for potential retrieval
    try {
      sessionStorage.setItem(`error_${this.state.errorId}`, JSON.stringify({
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: errorDetails.timestamp,
      }));
    } catch {
      // Storage might be full or unavailable
    }
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    const { resetKeys } = this.props;
    const { hasError } = this.state;

    if (hasError && prevProps.resetKeys !== resetKeys) {
      this.reset();
    }
  }

  reset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, errorId: null });
    this.props.onReset?.();
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  handleReportError = () => {
    const { error, errorId } = this.state;
    
    // Create a GitHub issue URL with error details
    const issueTitle = encodeURIComponent(`Error: ${error?.message || 'Unknown error'}`);
    const issueBody = encodeURIComponent(`
**Error ID:** ${errorId}
**Timestamp:** ${new Date().toISOString()}
**Message:** ${error?.message}
**Stack:** 
\`\`\`
${error?.stack}
\`\`\`

**Steps to Reproduce:**
1. [Please describe what you were doing when the error occurred]

**Environment:**
- Browser: ${navigator.userAgent}
- URL: ${window.location.href}
    `);
    
    // Open GitHub issues page (adjust URL as needed)
    window.open(`https://github.com/your-repo/purple-team-gpt/issues/new?title=${issueTitle}&body=${issueBody}`, '_blank');
  };

  render() {
    const { hasError, error, errorId } = this.state;
    const { children, fallback, componentName, level = 'component' } = this.props;

    if (hasError) {
      if (fallback) {
        return fallback;
      }

      if (level === 'app') {
        return (
          <AppErrorFallback
            error={error}
            errorId={errorId}
            onRetry={this.reset}
            onReload={this.handleReload}
            onGoHome={this.handleGoHome}
            onReport={this.handleReportError}
          />
        );
      }

      return (
        <ComponentErrorFallback
          error={error}
          errorId={errorId}
          componentName={componentName}
          onRetry={this.reset}
          onReport={this.handleReportError}
        />
      );
    }

    return children;
  }
}

// App-level error fallback UI
interface ErrorFallbackProps {
  error: Error | null;
  errorId: string | null;
  onRetry: () => void;
  onReload: () => void;
  onGoHome: () => void;
  onReport: () => void;
}

function AppErrorFallback({ error, errorId, onRetry, onReload, onGoHome, onReport }: ErrorFallbackProps) {
  return (
    <div 
      className="min-h-screen bg-background flex items-center justify-center p-4"
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <Card className="max-w-lg w-full border-destructive/50 bg-destructive/5">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
            <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
          </div>
          <CardTitle className="text-xl text-destructive">
            Something went wrong
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-muted-foreground">
            We encountered an unexpected error. The application needs to be refreshed.
          </p>
          
          {error && import.meta.env.DEV && (
            <div className="bg-muted p-3 rounded-lg overflow-auto max-h-32">
              <p className="text-xs font-mono text-destructive break-all">
                {error.message}
              </p>
            </div>
          )}
          
          {errorId && (
            <p className="text-xs text-center text-muted-foreground">
              Error ID: <code className="font-mono">{errorId}</code>
            </p>
          )}
          
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <Button
              onClick={onReload}
              className="gap-2 min-h-[44px]"
              aria-label="Reload application"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Reload App
            </Button>
            <Button
              variant="outline"
              onClick={onGoHome}
              className="gap-2 min-h-[44px]"
              aria-label="Go to home page"
            >
              <Home className="h-4 w-4" aria-hidden="true" />
              Go Home
            </Button>
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={onReport}
            className="w-full gap-2 text-muted-foreground"
            aria-label="Report this error"
          >
            <Send className="h-3 w-3" aria-hidden="true" />
            Report this issue
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// Component-level error fallback UI
interface ComponentFallbackProps {
  error: Error | null;
  errorId: string | null;
  componentName?: string;
  onRetry: () => void;
  onReport: () => void;
}

function ComponentErrorFallback({ error, errorId, componentName, onRetry, onReport }: ComponentFallbackProps) {
  return (
    <div 
      className="h-full flex items-center justify-center p-4"
      role="alert"
      aria-live="polite"
    >
      <Card className="max-w-md w-full border-yellow-500/50 bg-yellow-500/5">
        <CardContent className="pt-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-yellow-500/10 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="h-5 w-5 text-yellow-500" aria-hidden="true" />
            </div>
            <div>
              <p className="font-medium text-foreground">
                {componentName ? `${componentName} Error` : 'Component Error'}
              </p>
              <p className="text-sm text-muted-foreground">
                This section couldn't be displayed.
              </p>
            </div>
          </div>
          
          {error && import.meta.env.DEV && (
            <div className="bg-muted p-2 rounded-lg overflow-auto max-h-24">
              <p className="text-xs font-mono text-yellow-600 break-all">
                {error.message}
              </p>
            </div>
          )}
          
          {errorId && (
            <p className="text-xs text-muted-foreground">
              Error ID: <code className="font-mono text-[10px]">{errorId}</code>
            </p>
          )}
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              className="flex-1 gap-2 min-h-[44px]"
              aria-label="Retry loading this section"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Retry
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onReport}
              className="min-h-[44px]"
              aria-label="Report this error"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Specialized Error Boundaries for specific components

// Sidebar Error Boundary
export function SidebarErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary 
      componentName="Sidebar"
      level="component"
    >
      {children}
    </ErrorBoundary>
  );
}

// Dashboard Error Boundary
export function DashboardErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary 
      componentName="Dashboard"
      level="component"
    >
      {children}
    </ErrorBoundary>
  );
}

// Attack Simulation Error Boundary
export function AttackSimulationErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary 
      componentName="Attack Simulation"
      level="component"
    >
      {children}
    </ErrorBoundary>
  );
}

// Findings Display Error Boundary
export function FindingsErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary 
      componentName="Findings Display"
      level="component"
    >
      {children}
    </ErrorBoundary>
  );
}

// App-level Error Boundary (wraps entire app)
export function AppErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary 
      level="app"
    >
      {children}
    </ErrorBoundary>
  );
}

// WebSocket Error/Connection Component
interface WebSocketErrorProps {
  isConnected: boolean;
  isReconnecting: boolean;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  reconnectCountdown: number;
  onReconnect: () => void;
  onDismiss?: () => void;
}

export function WebSocketStatus({
  isConnected,
  isReconnecting,
  reconnectAttempts,
  maxReconnectAttempts,
  reconnectCountdown,
  onReconnect,
  onDismiss,
}: WebSocketErrorProps) {
  // Don't show anything if connected
  if (isConnected && !isReconnecting) {
    return null;
  }

  // Connection lost, attempting to reconnect
  if (isReconnecting) {
    return (
      <div 
        className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50"
        role="status"
        aria-live="polite"
      >
        <Card className="border-yellow-500/50 bg-yellow-500/10 backdrop-blur-sm shadow-lg">
          <CardContent className="p-3 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center">
              <RefreshCw className="h-4 w-4 text-yellow-500 animate-spin" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-yellow-500">
                Reconnecting...
              </p>
              <p className="text-xs text-muted-foreground">
                Attempt {reconnectAttempts} of {maxReconnectAttempts}
                {reconnectCountdown > 0 && ` in ${reconnectCountdown}s`}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Connection failed completely
  return (
    <div 
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 max-w-md w-[calc(100%-2rem)]"
      role="alert"
      aria-live="assertive"
    >
      <Card className="border-destructive/50 bg-destructive/10 backdrop-blur-sm shadow-lg">
        <CardContent className="p-3">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-destructive/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <WifiOff className="h-4 w-4 text-destructive" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-destructive">
                Connection Lost
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Unable to connect to the server. Real-time updates are unavailable.
              </p>
              <div className="flex gap-2 mt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onReconnect}
                  className="gap-2 min-h-[36px]"
                  aria-label="Try to reconnect"
                >
                  <RefreshCw className="h-3 w-3" aria-hidden="true" />
                  Reconnect
                </Button>
                {onDismiss && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onDismiss}
                    className="min-h-[36px]"
                    aria-label="Dismiss this message"
                  >
                    Dismiss
                  </Button>
                )}
              </div>
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-secondary/50 transition-colors"
                aria-label="Close notification"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Offline Indicator Component
export function OfflineIndicator() {
  const isOnline = navigator.onLine;
  
  if (isOnline) {
    return null;
  }

  return (
    <div 
      className="fixed top-0 left-0 right-0 z-[100] bg-destructive text-destructive-foreground text-center py-2 text-sm font-medium"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-center justify-center gap-2">
        <WifiOff className="h-4 w-4" aria-hidden="true" />
        <span>You are currently offline. Some features may not be available.</span>
      </div>
    </div>
  );
}

// Connection Status Badge for Header
interface ConnectionBadgeProps {
  isConnected: boolean;
  className?: string;
}

export function ConnectionBadge({ isConnected, className }: ConnectionBadgeProps) {
  return (
    <div 
      className={cn(
        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors",
        isConnected 
          ? "bg-green-500/10 text-green-400 border border-green-500/20" 
          : "bg-red-500/10 text-red-400 border border-red-500/20",
        className
      )}
      role="status"
      aria-live="polite"
      aria-label={isConnected ? "Connected to server" : "Disconnected from server"}
    >
      {isConnected ? (
        <>
          <Wifi className="h-3 w-3" aria-hidden="true" />
          <span className="hidden sm:inline">Connected</span>
        </>
      ) : (
        <>
          <WifiOff className="h-3 w-3" aria-hidden="true" />
          <span className="hidden sm:inline">Offline</span>
        </>
      )}
    </div>
  );
}

// Error reporting utility
export function reportError(error: Error, context?: Record<string, unknown>) {
  const errorReport = {
    message: error.message,
    stack: error.stack,
    timestamp: new Date().toISOString(),
    url: window.location.href,
    userAgent: navigator.userAgent,
    context,
  };

  // Log to console in development
  if (import.meta.env.DEV) {
    console.error('Error Report:', errorReport);
  }

  // In production, you could send this to an error tracking service
  // Example: Sentry, LogRocket, etc.
  
  return errorReport;
}
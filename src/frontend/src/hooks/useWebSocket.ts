import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketEvent } from '../lib/api';

interface UseWebSocketOptions {
  sessionId: string;
  onEvent?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface WebSocketState {
  isConnected: boolean;
  isReconnecting: boolean;
  reconnectAttempts: number;
  reconnectCountdown: number;
  lastError: string | null;
  events: WebSocketEvent[];
}

export function useWebSocket({
  sessionId,
  onEvent,
  onConnect,
  onDisconnect,
  onError,
  reconnect: shouldReconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
}: UseWebSocketOptions) {
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isReconnecting: false,
    reconnectAttempts: 0,
    reconnectCountdown: 0,
    lastError: null,
    events: [],
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isManualDisconnect = useRef(false);

  // Clear all timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
  }, []);

  // Start countdown for reconnection
  const startCountdown = useCallback((seconds: number) => {
    setState(prev => ({ ...prev, reconnectCountdown: seconds }));
    
    countdownIntervalRef.current = setInterval(() => {
      setState(prev => {
        const newCountdown = Math.max(0, prev.reconnectCountdown - 1);
        if (newCountdown === 0) {
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current);
            countdownIntervalRef.current = null;
          }
        }
        return { ...prev, reconnectCountdown: newCountdown };
      });
    }, 1000);
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Clear any existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    clearTimers();

    try {
      const wsUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace('http', 'ws');
      // Connect to general WebSocket endpoint if no session, otherwise use session-specific endpoint
      const endpoint = sessionId ? `/ws/session/${sessionId}` : '/ws';
      const ws = new WebSocket(`${wsUrl}${endpoint}`);
      wsRef.current = ws;
      isManualDisconnect.current = false;

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setState(prev => ({
          ...prev,
          isConnected: true,
          isReconnecting: false,
          reconnectAttempts: 0,
          reconnectCountdown: 0,
          lastError: null,
        }));
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          setState(prev => ({
            ...prev,
            events: [...prev.events.slice(-99), data],
          }));
          onEvent?.(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
          setState(prev => ({
            ...prev,
            lastError: 'Failed to parse server message',
          }));
        }
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        
        setState(prev => ({
          ...prev,
          isConnected: false,
        }));

        onDisconnect?.();

        // Don't reconnect if manual disconnect or max attempts reached
        if (isManualDisconnect.current) {
          setState(prev => ({ ...prev, isReconnecting: false }));
          return;
        }

        // Attempt reconnection if enabled
        if (shouldReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1), 30000);
          
          setState(prev => ({
            ...prev,
            isReconnecting: true,
            reconnectAttempts: reconnectAttemptsRef.current,
            lastError: event.reason || 'Connection closed',
          }));

          startCountdown(Math.ceil(delay / 1000));

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setState(prev => ({
            ...prev,
            isReconnecting: false,
            lastError: 'Maximum reconnection attempts reached',
          }));
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        
        setState(prev => ({
          ...prev,
          lastError: 'WebSocket connection error',
        }));

        onError?.(error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setState(prev => ({
        ...prev,
        lastError: 'Failed to create WebSocket connection',
        isConnected: false,
      }));
    }
  }, [sessionId, onEvent, onConnect, onDisconnect, onError, shouldReconnect, reconnectInterval, maxReconnectAttempts, clearTimers, startCountdown]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    isManualDisconnect.current = true;
    clearTimers();
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setState(prev => ({
      ...prev,
      isConnected: false,
      isReconnecting: false,
      reconnectCountdown: 0,
    }));
  }, [clearTimers]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    setState(prev => ({
      ...prev,
      reconnectAttempts: 0,
      lastError: null,
    }));
    connect();
  }, [connect]);

  // Send message
  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  // Clear events
  const clearEvents = useCallback(() => {
    setState(prev => ({ ...prev, events: [] }));
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, lastError: null }));
  }, []);

  // Connect on mount and when sessionId changes
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [sessionId, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  return {
    ...state,
    send,
    disconnect,
    reconnect,
    clearEvents,
    clearError,
  };
}

// Hook for managing offline/online status
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}
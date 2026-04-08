import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketEvent, getToken } from '../lib/api';

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
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isManualDisconnect = useRef(false);
  
  // Use refs for callbacks to avoid reconnection loops
  const onEventRef = useRef(onEvent);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);
  
  // Update refs when callbacks change
  useEffect(() => {
    onEventRef.current = onEvent;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onErrorRef.current = onError;
  });

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
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
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
  const connect = useCallback(async () => {
    // Clear any existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    clearTimers();

    // Get authentication token
    const token = await getToken();
    if (!token) {
      console.error('WebSocket: No auth token available');
      setState(prev => ({
        ...prev,
        lastError: 'Authentication required',
        isConnected: false,
      }));
      return;
    }

    try {
      // Use current host for WebSocket connection (goes through Vite proxy)
      const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = typeof window !== 'undefined' ? window.location.host : 'localhost:5000';
      const wsUrl = `${protocol}//${host}`;
      // Connect to general WebSocket endpoint if no session, otherwise use session-specific endpoint
      // Include token for authentication
      const endpoint = sessionId ? `/ws/session/${sessionId}?token=${token}` : `/ws?token=${token}`;
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
        onConnectRef.current?.();
        
        // Start heartbeat to keep connection alive
        heartbeatIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000); // Send ping every 30 seconds
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          setState(prev => ({
            ...prev,
            events: [...prev.events.slice(-99), data],
          }));
          onEventRef.current?.(data);
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
        
        // Clear heartbeat interval
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }
        
        setState(prev => ({
          ...prev,
          isConnected: false,
        }));

        onDisconnectRef.current?.();

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

        onErrorRef.current?.(error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setState(prev => ({
        ...prev,
        lastError: 'Failed to create WebSocket connection',
        isConnected: false,
      }));
    }
  }, [sessionId, shouldReconnect, reconnectInterval, maxReconnectAttempts, clearTimers, startCountdown]);

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
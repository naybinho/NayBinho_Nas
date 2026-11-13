import { useEffect, useRef, useState, useCallback } from 'react';

export interface UseWebSocketOptions {
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onOpen?: (event: WebSocketEventMap['open']) => void;
  onClose?: (event: WebSocketEventMap['close']) => void;
  onError?: (event: WebSocketEventMap['error']) => void;
}

export type ConnectionStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';

export function useWebSocket<T = any>(
  url: string | null,
  options: UseWebSocketOptions = {}
) {
  const {
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    onOpen,
    onClose,
    onError,
  } = options;

  const [lastData, setLastData] = useState<T | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('CLOSED');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!url) return;

    try {
      setStatus('CONNECTING');
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = (event) => {
        setStatus('OPEN');
        reconnectAttemptsRef.current = 0;
        if (onOpen) onOpen(event);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setLastData(parsed);
        } catch {
          setLastData(event.data as unknown as T);
        }
      };

      ws.onerror = (event) => {
        if (onError) onError(event);
      };

      ws.onclose = (event) => {
        setStatus('CLOSED');
        if (onClose) onClose(event);

        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch (err) {
      setStatus('CLOSED');
    }
  }, [url, autoReconnect, reconnectInterval, maxReconnectAttempts, onOpen, onClose, onError]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = typeof message === 'string' ? message : JSON.stringify(message);
      wsRef.current.send(payload);
      return true;
    }
    return false;
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectAttemptsRef.current = maxReconnectAttempts; // prevent reconnect
    if (wsRef.current) {
      wsRef.current.close();
    }
  }, [maxReconnectAttempts]);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    lastData,
    status,
    sendMessage,
    disconnect,
    reconnect: connect,
    isConnected: status === 'OPEN',
  };
}

export default useWebSocket;

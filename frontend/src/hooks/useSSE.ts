import { useEffect, useRef, useState, useCallback } from 'react';

export interface UseSSEOptions {
  withCredentials?: boolean;
  onOpen?: (event: Event) => void;
  onError?: (event: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export type SSEConnectionStatus = 'CONNECTING' | 'OPEN' | 'CLOSED';

export function useSSE<T = any>(
  url: string | null,
  options: UseSSEOptions = {}
) {
  const {
    withCredentials = false,
    onOpen,
    onError,
    autoReconnect = true,
    reconnectInterval = 5000,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<SSEConnectionStatus>('CLOSED');
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!url) return;

    try {
      setStatus('CONNECTING');
      const es = new EventSource(url, { withCredentials });
      eventSourceRef.current = es;

      es.onopen = (event) => {
        setStatus('OPEN');
        if (onOpen) onOpen(event);
      };

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch {
          setData(event.data as unknown as T);
        }
      };

      es.onerror = (event) => {
        setStatus('CLOSED');
        es.close();
        if (onError) onError(event);

        if (autoReconnect) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch {
      setStatus('CLOSED');
    }
  }, [url, withCredentials, onOpen, onError, autoReconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setStatus('CLOSED');
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    data,
    status,
    disconnect,
    reconnect: connect,
    isConnected: status === 'OPEN',
  };
}

export default useSSE;

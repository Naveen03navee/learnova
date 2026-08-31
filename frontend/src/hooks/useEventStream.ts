import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';

export interface RuntimeEvent {
  message: string;
  type: string;
  timestamp: number;
}

export interface EventStreamOptions {
  sseEndpoint: string;
  initialStatusEndpoint?: string;
  onComplete?: (status: string, message?: string) => void;
  onInitialTerminalState?: () => void;
}

export function useEventStream({ sseEndpoint, initialStatusEndpoint, onComplete, onInitialTerminalState }: EventStreamOptions) {
  const [status, setStatus] = useState("PENDING");
  const [message, setMessage] = useState("Initializing...");
  const [progress, setProgress] = useState(0);
  const [events, setEvents] = useState<RuntimeEvent[]>([]);
  const [provider, setProvider] = useState<string | null>(null);
  const [rateLimitCountdown, setRateLimitCountdown] = useState<number | null>(null);
  const [stuckSeconds, setStuckSeconds] = useState<number>(0);
  const [batchInfo, setBatchInfo] = useState<{batch?: number, total_batches?: number}>({});

  const retryCount = useRef(0);
  const lastEventTime = useRef<number>(Date.now());
  const MAX_RETRIES = 5;

  // Rate Limit Countdown Timer
  useEffect(() => {
    if (rateLimitCountdown === null || rateLimitCountdown <= 0) return;
    const timer = setInterval(() => {
      setRateLimitCountdown(prev => prev !== null && prev > 0 ? prev - 1 : 0);
    }, 1000);
    return () => clearInterval(timer);
  }, [rateLimitCountdown]);

  // Stuck / No Event Protection Timer
  useEffect(() => {
    const timer = setInterval(() => {
      if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "READY"].includes(status)) {
        setStuckSeconds(0);
        return;
      }
      
      const secondsSinceLastEvent = Math.floor((Date.now() - lastEventTime.current) / 1000);
      if (secondsSinceLastEvent > 10) {
        setStuckSeconds(secondsSinceLastEvent);
      } else {
        setStuckSeconds(0);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [status]);

  useEffect(() => {
    let active = true;
    let eventSource: EventSource | null = null;

    const connectSSE = async () => {
      try {
        const { createClient } = await import('@/lib/supabase');
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token || '';
        
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const url = `${apiUrl}${sseEndpoint}${sseEndpoint.includes('?') ? '&' : '?'}token=${token}`;
        eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
          if (!active) return;
          retryCount.current = 0;
          lastEventTime.current = Date.now();
          
          try {
            const data = JSON.parse(event.data);
            
            if (data.status) setStatus(data.status);
            if (data.progress !== undefined) setProgress(data.progress * 100);
            if (data.provider) setProvider(data.provider);
            
            if (data.retry_after_seconds) {
                setRateLimitCountdown(data.retry_after_seconds);
            } else if (data.event_type !== 'RATE_LIMIT' && data.event_type !== 'PROVIDER_RETRY') {
                setRateLimitCountdown(null);
            }

            if (data.message) {
                setEvents(prev => {
                    const newEvents = [...prev, { message: data.message, type: data.event_type || 'INFO', timestamp: Date.now() }];
                    return newEvents.slice(-7); // keep last 7
                });
                setMessage(data.message);
            }

            if (data.batch || data.total_batches) {
              setBatchInfo({ batch: data.batch, total_batches: data.total_batches });
            }

            if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "READY"].includes(data.status)) {
              eventSource?.close();
              if (onComplete) onComplete(data.status, data.message);
            }
          } catch (e) {
            console.error("Failed to parse event", e);
          }
        };

        eventSource.onerror = async (error) => {
          if (!active) return;
          eventSource?.close();

          if (retryCount.current < MAX_RETRIES) {
            retryCount.current += 1;
            
            if (initialStatusEndpoint) {
              try {
                const res = await api.get(initialStatusEndpoint);
                if (!active) return;
                const data = res.data;
                if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "READY"].includes(data.status)) {
                  setStatus(data.status);
                  if (onComplete) onComplete(data.status, data.message);
                  return;
                }
              } catch (err) {
                // fallthrough to timeout
              }
            }
            setTimeout(connectSSE, 2000 * retryCount.current);
          } else {
            setStatus("FAILED");
            setMessage("Connection lost. Please refresh.");
            if (onComplete) onComplete("FAILED", "Connection lost. Please refresh.");
          }
        };
      } catch (err) {
        console.error("Error setting up EventSource", err);
      }
    };

    const checkInitialStatus = async () => {
      if (!initialStatusEndpoint) {
        connectSSE();
        return;
      }
      try {
        const res = await api.get(initialStatusEndpoint);
        if (!active) return;
        const data = res.data;
        
        setStatus(data.status);
        if (data.progress !== undefined) setProgress(data.progress * 100);
        
        if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "READY"].includes(data.status)) {
          if (["COMPLETED", "READY"].includes(data.status)) setProgress(100);
          setMessage(`Process ${data.status.toLowerCase()}`);
          if (onInitialTerminalState) {
            onInitialTerminalState();
          } else if (onComplete) {
            onComplete(data.status, data.message || `Process ${data.status.toLowerCase()}`);
          }
        } else {
          connectSSE();
        }
      } catch (err) {
        if (active) connectSSE();
      }
    };

    checkInitialStatus();

    return () => {
      active = false;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [sseEndpoint, initialStatusEndpoint, onComplete, onInitialTerminalState]);

  return {
    status,
    message,
    progress,
    events,
    provider,
    rateLimitCountdown,
    stuckSeconds,
    batchInfo
  };
}

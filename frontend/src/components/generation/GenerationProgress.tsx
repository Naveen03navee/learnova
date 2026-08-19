"use client";

import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, AlertCircle, Loader2, Cpu, Clock, RefreshCcw, ShieldAlert, XCircle } from "lucide-react";
import { notify } from "@/store/notificationStore";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface GenerationProgressProps {
  sessionId: string;
  onComplete: () => void;
  onInitialTerminalState?: () => void;
}

interface RuntimeEvent {
  message: string;
  type: string;
  timestamp: number;
}

export function GenerationProgress({ sessionId, onComplete, onInitialTerminalState }: GenerationProgressProps) {
  const [status, setStatus] = useState("PENDING");
  const [message, setMessage] = useState("Initializing generation session...");
  const [progress, setProgress] = useState(0);
  const [batchInfo, setBatchInfo] = useState<{batch?: number, total_batches?: number}>({});
  
  const [events, setEvents] = useState<RuntimeEvent[]>([]);
  const [provider, setProvider] = useState<string | null>(null);
  const [rateLimitCountdown, setRateLimitCountdown] = useState<number | null>(null);
  const [stuckSeconds, setStuckSeconds] = useState<number>(0);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isCancellingDialog, setIsCancellingDialog] = useState(false);
  
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
      if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED"].includes(status)) {
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
      const { createClient } = await import('@/lib/supabase');
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token || '';
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      eventSource = new EventSource(`${apiUrl}/api/v1/generation/${sessionId}/stream?token=${token}`);

      eventSource.onmessage = (event) => {
        if (!active) return;
        retryCount.current = 0;
        lastEventTime.current = Date.now();
        
        const data = JSON.parse(event.data);
        
        setStatus(data.status);
        setProgress(data.progress * 100);
        
        if (data.provider) setProvider(data.provider);
        
        if (data.retry_after_seconds) {
            setRateLimitCountdown(data.retry_after_seconds);
        } else if (data.event_type !== 'RATE_LIMIT' && data.event_type !== 'PROVIDER_RETRY') {
            setRateLimitCountdown(null);
        }

        if (data.message) {
            setEvents(prev => {
                const newEvents = [...prev, { message: data.message, type: data.event_type || 'INFO', timestamp: Date.now() }];
                return newEvents.slice(-7); // keep last 7 for better visibility
            });
            setMessage(data.message);
        }

        if (data.batch || data.total_batches) {
          setBatchInfo({ batch: data.batch, total_batches: data.total_batches });
        }

        if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED"].includes(data.status)) {
          eventSource?.close();
          if (data.status === "COMPLETED") {
            notify.success('Generation complete', data.message || 'All questions were generated successfully.');
          } else if (data.status === "PARTIAL") {
            notify.info('Generation partially complete', data.message || 'Some questions were generated. Review them in the question bank.');
          } else if (data.status === "FAILED") {
            notify.error('Generation failed', data.message || 'The generation session encountered an error.');
          } else if (data.status === "CANCELLED") {
            notify.info('Generation cancelled', data.message || 'Generation was cancelled by you.');
          }
          onComplete();
        }
      };

      eventSource.onerror = async (error) => {
        if (!active) return;
        eventSource?.close();

        if (retryCount.current < MAX_RETRIES) {
          retryCount.current += 1;
          console.warn(`SSE stream disconnected. Retry ${retryCount.current}/${MAX_RETRIES}...`);
          
          try {
            const res = await api.get(`/api/v1/generation/${sessionId}`);
            if (!active) return;
            const data = res.data;
            
            if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED"].includes(data.status)) {
              setStatus(data.status);
              if (data.status === "COMPLETED") {
                notify.success('Generation complete', 'All questions were generated successfully.');
              } else if (data.status === "PARTIAL") {
                notify.info('Generation partially complete', 'Some questions were generated.');
              } else if (data.status === "FAILED") {
                notify.error('Generation failed', 'The generation session encountered an error.');
              } else if (data.status === "CANCELLED") {
                notify.info('Generation cancelled', 'Generation was cancelled by you.');
              }
              onComplete();
            } else {
              setTimeout(connectSSE, 2000 * retryCount.current);
            }
          } catch (err) {
            setTimeout(connectSSE, 2000 * retryCount.current);
          }
        } else {
          setStatus("FAILED");
          setMessage("Connection lost. Please refresh the page to check status.");
          notify.error('Generation failed', 'Max retries reached. Connection to server lost.');
          onComplete();
        }
      };
    };

    const checkInitialStatus = async () => {
      try {
        const res = await api.get(`/api/v1/generation/${sessionId}`);
        if (!active) return;
        const data = res.data;
        
        setStatus(data.status);
        setProgress(data.progress ? data.progress * 100 : 0);
        
        if (["COMPLETED", "PARTIAL", "FAILED", "CANCELLED"].includes(data.status)) {
          if (data.status === "COMPLETED") setProgress(100);
          setMessage(data.status === "COMPLETED" ? "Generation completed." : data.status === "FAILED" ? "Generation failed." : data.status === "CANCELLED" ? "Generation cancelled." : "Generation partially completed.");
          if (onInitialTerminalState) {
            onInitialTerminalState();
          } else {
            onComplete();
          }
        } else {
          connectSSE();
        }
      } catch (err) {
        console.error("Failed to fetch initial status, fallback to SSE", err);
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
  }, [sessionId, onComplete]);

  const handleCancel = async () => {
    setIsCancelling(true);
    try {
      await api.post(`/api/v1/generation/${sessionId}/cancel`);
      notify.info("Cancellation requested", "Stopping gracefully...");
    } catch (error) {
      console.error("Failed to cancel", error);
      notify.error("Cancellation failed", "Could not cancel the generation.");
      setIsCancelling(false);
    }
  };

  const isTerminal = ["COMPLETED", "PARTIAL", "FAILED", "CANCELLED"].includes(status);

  return (
    <Card className="border-blue-100 shadow-md transition-all duration-300">
      <CardHeader className="bg-slate-50 border-b pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            {["COMPLETED", "PARTIAL"].includes(status) && <CheckCircle2 className="text-green-500 w-5 h-5" />}
            {status === "FAILED" && <AlertCircle className="text-red-500 w-5 h-5" />}
            {status === "CANCELLED" && <XCircle className="text-slate-500 w-5 h-5" />}
            {status === "rate_limited" && <Clock className="text-orange-500 w-5 h-5" />}
            {!isTerminal && status !== "rate_limited" && <Loader2 className="animate-spin text-blue-500 w-5 h-5" />}
            Generation Runtime Status
          </CardTitle>
          
          {provider && !isTerminal && (
            <Badge variant="outline" className="flex items-center gap-1 bg-white border-blue-200 text-blue-700 capitalize">
              <Cpu className="w-3 h-3" />
              {provider} Active
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6 pt-6">
        
        {rateLimitCountdown !== null && rateLimitCountdown > 0 && !isTerminal && (
          <div className="flex items-start gap-3 bg-orange-50 border border-orange-200 text-orange-800 p-4 rounded-md">
            <ShieldAlert className="w-5 h-5 flex-shrink-0 mt-0.5 text-orange-600" />
            <div className="flex-1">
              <h4 className="font-semibold text-sm">Provider Rate Limit Reached</h4>
              <p className="text-sm mt-1">
                We've paused to respect provider limits to avoid permanent blocks. 
                Retrying automatically in <strong>{rateLimitCountdown} seconds</strong>...
              </p>
            </div>
            <RefreshCcw className="w-4 h-4 text-orange-500 animate-spin" />
          </div>
        )}

        {stuckSeconds > 10 && rateLimitCountdown === null && !isTerminal && (
          <div className="flex items-start gap-3 bg-blue-50 border border-blue-200 text-blue-800 p-4 rounded-md">
            <Loader2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-600 animate-spin" />
            <div className="flex-1">
              <h4 className="font-semibold text-sm">Waiting for backend activity...</h4>
              <p className="text-sm mt-1">
                Generation is still processing in the background. Some steps like AI model reasoning can take longer.
                Last activity: {stuckSeconds} seconds ago.
              </p>
            </div>
          </div>
        )}

        {status === "CANCELLED" && (
          <div className="flex items-start gap-3 bg-slate-50 border border-slate-200 text-slate-800 p-4 rounded-md">
            <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-slate-500" />
            <div className="flex-1">
              <h4 className="font-semibold text-sm">Generation Cancelled</h4>
              <p className="text-sm mt-1">
                {message || "The generation process was safely stopped."}
              </p>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <div className="flex justify-between text-sm font-medium mb-1">
            <span className="text-slate-600">Overall Progress</span>
            <span className="text-slate-800">{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="w-full h-2.5" />
          
          {batchInfo.total_batches && !isTerminal && (
            <div className="mt-2 text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full inline-flex items-center w-fit border border-blue-100">
              Batch {batchInfo.batch} of {batchInfo.total_batches}
            </div>
          )}
        </div>

        <div className="bg-slate-900 rounded-lg overflow-hidden border border-slate-800">
          <div className="bg-slate-800 px-3 py-1.5 border-b border-slate-700 flex justify-between items-center text-xs text-slate-300">
            <span>Live Activity Feed</span>
            {!isTerminal && <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> Streaming</span>}
            {isTerminal && <span className="text-slate-500">Stopped</span>}
          </div>
          <div className="p-3 h-40 overflow-y-auto space-y-2 text-sm font-mono flex flex-col justify-end">
            {events.length === 0 ? (
              <div className="text-slate-500 text-xs">Waiting for events...</div>
            ) : (
              events.map((evt, idx) => {
                const isError = ['ERROR', 'PROVIDER_ERROR', 'QUOTA_EXCEEDED', 'GENERATION_FAILED'].includes(evt.type);
                const isWarning = ['WARNING', 'RATE_LIMIT', 'PROVIDER_RETRY'].includes(evt.type);
                const isSuccess = ['SUCCESS', 'PROVIDER_SUCCESS', 'FALLBACK_SUCCESS', 'EMBEDDING_MODEL_READY', 'KNOWLEDGE_RETRIEVED', 'BATCH_COMPLETED', 'GENERATION_COMPLETED'].includes(evt.type);
                const isFallback = ['PROVIDER_FALLBACK'].includes(evt.type);
                const isLoading = ['LOADING_EMBEDDING_MODEL', 'GENERATING_BATCH', 'REPAIRING', 'INITIALIZING', 'RETRIEVING_KNOWLEDGE', 'BUILDING_CONTEXT', 'VALIDATING', 'DEDUPLICATING'].includes(evt.type);
                const isCancel = ['CANCELLED'].includes(evt.type);
                
                let icon = "●";
                if (isSuccess) icon = "✓";
                if (isError) icon = "✕";
                if (isWarning) icon = "⚠";
                if (isLoading) icon = "◐";
                if (isFallback) icon = "↪";

                return (
                  <div key={idx} className="flex gap-2 items-start transition-all animate-in fade-in slide-in-from-bottom-2">
                    <span className="text-slate-500 text-xs mt-0.5 flex-shrink-0">
                      {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false, second: '2-digit' })}
                    </span>
                    <span className={`flex-1 break-words whitespace-pre-wrap ${
                      isError ? 'text-red-400' :
                      isWarning ? 'text-orange-400' :
                      isSuccess ? 'text-green-400' :
                      isFallback ? 'text-purple-400' :
                      isLoading ? 'text-blue-300' :
                      isCancel ? 'text-slate-400 italic' :
                      'text-slate-300'
                    }`}>
                      <span className="mr-1.5">{icon}</span> {evt.message}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
        
        {!isTerminal && (
          <div className="flex justify-end pt-2">
            <Button 
              variant="outline" 
              size="sm"
              disabled={isCancelling}
              className="text-slate-600 border-slate-300 hover:bg-slate-100 hover:text-slate-900"
              onClick={() => setIsCancellingDialog(true)}
            >
              {isCancelling ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <XCircle className="w-4 h-4 mr-2" />}
              {isCancelling ? "Cancelling..." : "Cancel Generation"}
            </Button>
            <AlertDialog open={isCancellingDialog} onOpenChange={setIsCancellingDialog}>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Cancel generation?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Generation will stop after the current operation reaches a safe cancellation point. Questions already generated will be preserved.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep generating</AlertDialogCancel>
                  <AlertDialogAction onClick={() => {
                    setIsCancellingDialog(false);
                    handleCancel();
                  }}>Cancel generation</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

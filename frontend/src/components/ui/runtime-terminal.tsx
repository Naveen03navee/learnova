import { RuntimeEvent } from "@/hooks/useEventStream";
import { Progress } from "@/components/ui/progress";
import { Loader2, CheckCircle2, AlertCircle, XCircle, Clock, Cpu, ShieldAlert, RefreshCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
} from "@/components/ui/alert-dialog";
import { useState } from "react";

export interface RuntimeTerminalProps {
  title?: string;
  status: string;
  message: string;
  progress: number;
  events: RuntimeEvent[];
  provider?: string | null;
  rateLimitCountdown?: number | null;
  stuckSeconds?: number;
  batchInfo?: { batch?: number; total_batches?: number };
  onCancel?: () => Promise<void>;
  isCancelling?: boolean;
}

export function RuntimeTerminal({
  title = "Runtime Status",
  status,
  message,
  progress,
  events,
  provider,
  rateLimitCountdown,
  stuckSeconds = 0,
  batchInfo = {},
  onCancel,
  isCancelling = false
}: RuntimeTerminalProps) {
  const [isCancellingDialog, setIsCancellingDialog] = useState(false);
  const isTerminal = ["COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "READY"].includes(status);

  return (
    <Card className="border-blue-100 shadow-md transition-all duration-300 w-full">
      <CardHeader className="bg-slate-50 border-b pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            {["COMPLETED", "PARTIAL", "READY"].includes(status) && <CheckCircle2 className="text-green-500 w-5 h-5" />}
            {status === "FAILED" && <AlertCircle className="text-red-500 w-5 h-5" />}
            {status === "CANCELLED" && <XCircle className="text-slate-500 w-5 h-5" />}
            {status === "rate_limited" && <Clock className="text-orange-500 w-5 h-5" />}
            {!isTerminal && status !== "rate_limited" && <Loader2 className="animate-spin text-blue-500 w-5 h-5" />}
            {title}
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
        
        {rateLimitCountdown !== null && rateLimitCountdown !== undefined && rateLimitCountdown > 0 && !isTerminal && (
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

        {stuckSeconds > 10 && (rateLimitCountdown === null || rateLimitCountdown === undefined) && !isTerminal && (
          <div className="flex items-start gap-3 bg-blue-50 border border-blue-200 text-blue-800 p-4 rounded-md">
            <Loader2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-600 animate-spin" />
            <div className="flex-1">
              <h4 className="font-semibold text-sm">Waiting for backend activity...</h4>
              <p className="text-sm mt-1">
                Processing is continuing in the background. Some steps can take longer.
                Last activity: {stuckSeconds} seconds ago.
              </p>
            </div>
          </div>
        )}

        {status === "CANCELLED" && (
          <div className="flex items-start gap-3 bg-slate-50 border border-slate-200 text-slate-800 p-4 rounded-md">
            <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-slate-500" />
            <div className="flex-1">
              <h4 className="font-semibold text-sm">Process Cancelled</h4>
              <p className="text-sm mt-1">
                {message || "The process was safely stopped."}
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
                const isError = ['ERROR', 'PROVIDER_ERROR', 'QUOTA_EXCEEDED', 'GENERATION_FAILED', 'PROCESSING_FAILED', 'EXTRACTION_FAILED'].includes(evt.type);
                const isWarning = ['WARNING', 'RATE_LIMIT', 'PROVIDER_RETRY'].includes(evt.type);
                const isSuccess = ['SUCCESS', 'PROVIDER_SUCCESS', 'FALLBACK_SUCCESS', 'EMBEDDING_MODEL_READY', 'KNOWLEDGE_RETRIEVED', 'BATCH_COMPLETED', 'GENERATION_COMPLETED', 'EXTRACTION_COMPLETED', 'PROCESSING_COMPLETED', 'ANALYSIS_COMPLETED'].includes(evt.type);
                const isFallback = ['PROVIDER_FALLBACK'].includes(evt.type);
                const isLoading = ['LOADING_EMBEDDING_MODEL', 'GENERATING_BATCH', 'REPAIRING', 'INITIALIZING', 'RETRIEVING_KNOWLEDGE', 'BUILDING_CONTEXT', 'VALIDATING', 'DEDUPLICATING', 'EXTRACTING', 'ANALYZING', 'CLEANING', 'CHUNKING', 'EMBEDDING', 'INDEXING'].includes(evt.type);
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
        
        {!isTerminal && onCancel && (
          <div className="flex justify-end pt-2">
            <Button 
              variant="outline" 
              size="sm"
              disabled={isCancelling}
              className="text-slate-600 border-slate-300 hover:bg-slate-100 hover:text-slate-900"
              onClick={() => setIsCancellingDialog(true)}
            >
              {isCancelling ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <XCircle className="w-4 h-4 mr-2" />}
              {isCancelling ? "Cancelling..." : "Cancel"}
            </Button>
            <AlertDialog open={isCancellingDialog} onOpenChange={setIsCancellingDialog}>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Cancel process?</AlertDialogTitle>
                  <AlertDialogDescription>
                    The process will stop after the current operation reaches a safe cancellation point.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep running</AlertDialogCancel>
                  <AlertDialogAction onClick={() => {
                    setIsCancellingDialog(false);
                    onCancel();
                  }}>Cancel</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

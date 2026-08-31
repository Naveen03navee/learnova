import { useEventStream } from "@/hooks/useEventStream";
import { RuntimeTerminal } from "@/components/ui/runtime-terminal";
import { useQueryClient } from "@tanstack/react-query";
import { useNotificationStore } from "@/store/notificationStore";

interface PatternProgressTerminalProps {
  patternId: string;
  examId: string;
  subjectId: string;
  onComplete: () => void;
}

export function PatternProgressTerminal({ patternId, examId, subjectId, onComplete }: PatternProgressTerminalProps) {
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);

  const streamState = useEventStream({
    sseEndpoint: `/api/v1/patterns/${patternId}/events`,
    onComplete: (finalStatus, finalMessage) => {
      queryClient.invalidateQueries({ queryKey: ['patterns', examId, subjectId] });
      
      if (finalStatus === "READY") {
        notify.success('Analysis complete', 'Pattern structure has been learned.');
      } else if (finalStatus === "FAILED") {
        notify.error('Analysis failed', finalMessage || 'An error occurred during analysis.');
      }
      onComplete();
    }
  });

  return (
    <RuntimeTerminal
      title="Pattern Analysis Status"
      {...streamState}
    />
  );
}

import { useEventStream } from "@/hooks/useEventStream";
import { RuntimeTerminal } from "@/components/ui/runtime-terminal";
import { useQueryClient } from "@tanstack/react-query";
import { useNotificationStore } from "@/store/notificationStore";

interface ResourceProgressTerminalProps {
  resourceId: string;
  examId: string;
  subjectId: string;
  folderId: string | null;
  onComplete: () => void;
}

export function ResourceProgressTerminal({ resourceId, examId, subjectId, folderId, onComplete }: ResourceProgressTerminalProps) {
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);

  const streamState = useEventStream({
    sseEndpoint: `/api/v1/resources/${resourceId}/events`,
    onComplete: (finalStatus, finalMessage) => {
      queryClient.invalidateQueries({ queryKey: ['resources', examId, subjectId, folderId] });
      
      if (finalStatus === "READY") {
        notify.success('Processing complete', 'Document is ready for generation.');
      } else if (finalStatus === "FAILED") {
        notify.error('Processing failed', finalMessage || 'An error occurred during processing.');
      }
      onComplete();
    }
  });

  return (
    <RuntimeTerminal
      title="Knowledge Processing Status"
      {...streamState}
    />
  );
}

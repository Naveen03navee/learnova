"use client";

import { useWorkspaceStore } from "@/store/workspaceStore";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Clock, Database, CheckSquare, Loader2 } from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { parseUtc } from "@/lib/date";

export default function HistoryPage() {
  const { examId, subjectId } = useWorkspaceStore();

  const { data: activities = [], isLoading } = useQuery({
    queryKey: ["activity", examId, subjectId, "history"],
    queryFn: () => {
      const params = new URLSearchParams();
      if (examId) params.append("exam_id", examId);
      if (subjectId) params.append("subject_id", subjectId);
      params.append("limit", "50");
      return api.get(`/api/v1/metrics/activity?${params.toString()}`).then(res => res.data);
    },
    enabled: !!examId && !!subjectId,
  });

  if (!examId || !subjectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)] text-muted-foreground space-y-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground/50" />
        <h2 className="text-xl font-medium">No Context Selected</h2>
        <p>Please select an Exam and Subject from the sidebar to view history.</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System History</h1>
        <p className="text-muted-foreground mt-2">Activity timeline for this workspace context.</p>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          ) : activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground text-center">
              <Clock className="w-10 h-10 mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-1">No Activity Found</h3>
              <p className="text-sm">Events will appear here as you generate questions and build papers.</p>
            </div>
          ) : (
            <div className="divide-y">
              {activities.map((activity: any) => (
                <div key={activity.id} className="p-6 flex items-start space-x-4 hover:bg-muted/50 transition-colors">
                  <div className="rounded-full bg-primary/10 p-3 mt-1">
                    {activity.type === 'generation' ? (
                      <Database className="h-5 w-5 text-primary" />
                    ) : (
                      <CheckSquare className="h-5 w-5 text-emerald-600" />
                    )}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-base font-medium">{activity.title}</p>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDistanceToNow(parseUtc(activity.created_at), { addSuffix: true })}
                      </span>
                    </div>
                    <div className="flex items-center text-sm text-muted-foreground space-x-4 pt-1">
                      <span className="uppercase text-[11px] tracking-wider font-semibold border rounded-full px-2 py-0.5">
                        {activity.status}
                      </span>
                      <span>{format(new Date(activity.created_at), "MMM d, yyyy 'at' h:mm a")}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

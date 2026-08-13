"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Check, X, Edit, AlertCircle } from "lucide-react";
import { useNotificationStore } from "@/store/notificationStore";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function GeneratedReview() {
  const { examId, subjectId } = useWorkspaceStore();
  
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);

  const { data: questions = [], isLoading } = useQuery({
    queryKey: ["review_questions", examId, subjectId],
    queryFn: async () => {
      let url = "/api/v1/generation/questions?";
      if (examId) url += `exam_id=${examId}&`;
      if (subjectId) url += `subject_id=${subjectId}&`;
      return api.get(url).then(res => res.data);
    },
    enabled: !!examId && !!subjectId
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/generation/questions/${id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review_questions"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      notify.success("Approved", "Question approved and moved to Question Bank.");
    },
    onError: (error: any) => {
      notify.error("Action failed", error.response?.data?.detail || "Failed to approve question");
    }
  });
  
  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/generation/questions/${id}/reject`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review_questions"] });
      notify.success("Rejected", "Question rejected and discarded.");
    },
    onError: (error: any) => {
      notify.error("Action failed", error.response?.data?.detail || "Failed to reject question");
    }
  });

  if (!examId || !subjectId) {
    return (
      <Alert variant="default" className="bg-amber-50 text-amber-800 border-amber-200 m-8 max-w-2xl">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Context Required</AlertTitle>
        <AlertDescription>
          Please select an Exam and Subject from the sidebar to review generated questions.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="flex flex-col h-full gap-4">

      
      <div className="flex-1 overflow-auto space-y-4 pb-10">
        <div className="flex justify-between items-center bg-muted/50 p-3 rounded-md">
          <span className="font-semibold">{questions.length} Pending Questions</span>
        </div>
        
        {isLoading && <div className="flex items-center justify-center p-8"><Loader2 className="animate-spin text-blue-500 w-8 h-8" /></div>}
        
        {!isLoading && questions.length === 0 && (
          <div className="text-center p-8 text-muted-foreground border rounded-md">
            No pending questions to review.
          </div>
        )}

        {questions.map((q: any) => (
          <Card key={q.id} className="border-blue-100 dark:border-blue-900">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground font-medium flex justify-between">
                <span>{q.content?.question_type || "MCQ"} • {q.content?.difficulty || "Medium"} • {q.content?.marks || 1} Marks</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="font-semibold text-lg">{q.question_text}</p>
              
              {q.content?.options && (
                <div className="space-y-2 pl-4 border-l-2">
                  {q.content.options.map((opt: any) => (
                    <div key={opt.id} className="flex gap-2">
                      <span className="font-medium text-muted-foreground">{opt.id}.</span>
                      <span className={opt.id === q.content.correct_answer || opt.text === q.content.correct_answer ? "font-bold text-green-600" : ""}>
                        {opt.text}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              
              {!q.content?.options && (
                <div className="bg-green-50/50 dark:bg-green-950/20 p-3 rounded-md text-sm border border-green-100 dark:border-green-900">
                  <span className="font-semibold text-green-800 dark:text-green-300">Answer: </span>
                  {q.content?.correct_answer}
                </div>
              )}

              <div className="text-sm bg-muted p-3 rounded-md">
                <span className="font-semibold block mb-1">Explanation:</span>
                {q.content?.explanation}
              </div>
              
              <div className="text-xs text-muted-foreground italic mt-2">
                AI Source: {Array.isArray(q.content?.source_citations) ? q.content.source_citations.join(", ") : q.content?.source_citation}
              </div>
            </CardContent>
            <CardFooter className="flex justify-end gap-2 border-t pt-4 bg-muted/20">
              <Button variant="outline" size="sm" disabled>
                <Edit className="w-4 h-4 mr-2" /> Edit
              </Button>
              <Button 
                variant="destructive" 
                size="sm"
                disabled={rejectMutation.isPending || approveMutation.isPending}
                onClick={() => rejectMutation.mutate(q.id)}
              >
                <X className="w-4 h-4 mr-2" /> Reject
              </Button>
              <Button 
                variant="default" 
                size="sm"
                disabled={rejectMutation.isPending || approveMutation.isPending}
                onClick={() => approveMutation.mutate(q.id)}
              >
                <Check className="w-4 h-4 mr-2" /> Approve
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Trash2, Edit, Plus, Search, AlertCircle } from "lucide-react";
import { useNotificationStore } from "@/store/notificationStore";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { QuestionDialog } from "./QuestionDialog";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AccessBadge } from "@/components/sharing/AccessBadge";
import { ShareDialog } from "@/components/sharing/ShareDialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Share2 as ShareDialogIcon, MoreVerticalIcon } from 'lucide-react';

export function QuestionBank() {
  const { examId, subjectId } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState("");
  
  // Dialog state
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<any>(null);
  const [shareOpenId, setShareOpenId] = useState<string | null>(null);
  
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);

  const { data: questions = [], isLoading } = useQuery({
    queryKey: ["questions", examId, subjectId, searchQuery],
    queryFn: async () => {
      let url = "/api/v1/questions?";
      if (examId) url += `exam_id=${examId}&`;
      if (subjectId) url += `subject_id=${subjectId}&`;
      if (searchQuery) url += `q=${encodeURIComponent(searchQuery)}&`;
      return api.get(url).then(res => res.data);
    },
    enabled: !!examId && !!subjectId
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/questions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      notify.success("Deleted", "Question was deleted from the bank.");
    },
    onError: (error: any) => {
      notify.error("Action failed", error.response?.data?.detail || "Failed to delete question");
    }
  });

  const openCreateDialog = () => {
    setEditingQuestion(null);
    setIsDialogOpen(true);
  };

  const openEditDialog = (q: any) => {
    setEditingQuestion(q);
    setIsDialogOpen(true);
  };

  if (!examId || !subjectId) {
    return (
      <Alert variant="default" className="bg-amber-50 text-amber-800 border-amber-200 m-8 max-w-2xl">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Context Required</AlertTitle>
        <AlertDescription>
          Please select an Exam and Subject from the sidebar to view the Question Bank.
        </AlertDescription>
      </Alert>
    );
  }

  const [shareOpenId, setShareOpenId] = useState<string | null>(null);

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Search and Action Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-4 border rounded-md bg-card">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search questions by text or concept..." 
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Button onClick={openCreateDialog} className="shrink-0 bg-blue-600 hover:bg-blue-700">
          <Plus className="h-4 w-4 mr-2" />
          Create Question
        </Button>
      </div>
      
      <div className="flex-1 overflow-auto space-y-4 pb-10">
        {isLoading && <div className="flex items-center justify-center p-8"><Loader2 className="animate-spin text-blue-500 w-8 h-8" /></div>}
        
        {!isLoading && questions.length === 0 && (
          <div className="text-center p-8 text-muted-foreground border rounded-md bg-card">
            {searchQuery ? "No questions match your search." : "No approved questions found. Create one or generate using AI!"}
          </div>
        )}

        {questions.map((q: any) => (
          <Card key={q.id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground font-medium flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-3">
                  <span>{q.question_type} • {q.difficulty} • {q.marks} Marks</span>
                  <AccessBadge access={q.access} />
                </div>
                <div className="flex gap-2">

                  <DropdownMenu>
                    <DropdownMenuTrigger className="h-8 w-8 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground outline-none">
                      <MoreVerticalIcon className="h-4 w-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {q.access?.level && ['OWNER', 'EDIT'].includes(q.access.level) && (
                        <DropdownMenuItem onClick={() => openEditDialog(q)}>
                          <Edit className="w-4 h-4 mr-2" /> Edit
                        </DropdownMenuItem>
                      )}
                      
                      {q.access?.level === 'OWNER' && !q.access?.is_global && (
                        <DropdownMenuItem onSelect={() => setShareOpenId(q.id)}>
                          <ShareDialogIcon className="w-4 h-4 mr-2" /> Share
                        </DropdownMenuItem>
                      )}
                      
                      {q.access?.level === 'OWNER' && (
                        <DropdownMenuItem className="text-red-600" onClick={() => { if(confirm("Delete this question?")) deleteMutation.mutate(q.id) }}>
                          <Trash2 className="w-4 h-4 mr-2" /> Delete
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>

                  {q.access?.level === 'OWNER' && !q.access?.is_global && (
                    <ShareDialog 
                      entityType="question" 
                      entityId={q.id} 
                      open={shareOpenId === q.id}
                      onOpenChange={(isOpen) => {
                        if (!isOpen) setShareOpenId(null);
                      }}
                    />
                  )}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="font-semibold text-lg">{q.question_text}</p>
              
              {q.question_type === "MCQ" && q.content.options && (
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
              
              {q.question_type !== "MCQ" && q.content.correct_answer && (
                <div className="bg-green-50/50 dark:bg-green-950/20 p-3 rounded-md text-sm border border-green-100 dark:border-green-900">
                  <span className="font-semibold text-green-800 dark:text-green-300">Answer: </span>
                  {q.content.correct_answer}
                </div>
              )}

              {q.content.explanation && (
                <div className="text-sm bg-muted p-3 rounded-md">
                  <span className="font-semibold block mb-1">Explanation:</span>
                  {q.content.explanation}
                </div>
              )}

              {q.source_citation && (
                <div className="text-xs text-muted-foreground italic mt-2">
                  Sources: {Array.isArray(q.source_citation) ? q.source_citation.join(", ") : q.source_citation}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

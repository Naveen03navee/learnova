'use client';

import { useWorkspaceStore } from '@/store/workspaceStore';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AlertCircle, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { AccessBadge } from '@/components/sharing/AccessBadge';
import { ShareDialog } from '@/components/sharing/ShareDialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Settings, Trash2 } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNotificationStore } from '@/store/notificationStore';

interface Exam {
  id: string;
  name: string;
  access?: any;
}

interface Subject {
  id: string;
  name: string;
  access?: any;
}

export function GlobalContextSelector() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { examId, subjectId, setExamId, setSubjectId } = useWorkspaceStore();
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);
  
  const { data: exams, isLoading: isLoadingExams, error: examsError } = useQuery({
    queryKey: ['exams'],
    queryFn: async () => (await api.get('/api/v1/exams')).data as Exam[]
  });

  const { data: subjects, isLoading: isLoadingSubjects } = useQuery({
    queryKey: ['subjects', examId],
    queryFn: async () => examId ? (await api.get(`/api/v1/subjects?exam_id=${examId}`)).data as Subject[] : [],
    enabled: !!examId
  });

  const clearResourcesMutation = useMutation({
    mutationFn: async () => {
      if (!subjectId) return;
      return api.delete(`/api/v1/subjects/${subjectId}/resources`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      notify.success("Resources Cleared", `Successfully deleted resources for this subject.`);
    },
    onError: (err: any) => {
      notify.error("Action Failed", err.response?.data?.detail || "Could not clear resources");
    }
  });

  const handleExamChange = (newExamId: string | null) => {
    if (!newExamId) return;
    setExamId(newExamId);
    
    // Clean URL if we are deep linked
    if (searchParams.has('folder_id') || searchParams.has('pattern_id')) {
      router.push(pathname);
    }
  };

  const handleSubjectChange = (newSubjectId: string | null) => {
    if (!newSubjectId) return;
    setSubjectId(newSubjectId);

    // Clean URL if we are deep linked
    if (searchParams.has('folder_id') || searchParams.has('pattern_id')) {
      router.push(pathname);
    }
  };

  if (isLoadingExams) {
    return (
      <div className="flex items-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Loading workspace...
      </div>
    );
  }

  if (examsError) {
    return (
      <div className="flex items-center text-sm text-destructive">
        <AlertCircle className="mr-2 h-4 w-4" />
        Error loading context
      </div>
    );
  }

  if (!exams || exams.length === 0) {
    return (
      <div className="flex items-center text-sm text-amber-600">
        <AlertCircle className="mr-2 h-4 w-4" />
        No exams available
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-2">
      <div className="flex items-center">
        <span className="text-xs font-medium text-muted-foreground mr-2 hidden sm:inline-block">Exam:</span>
        <Select value={examId || ''} onValueChange={handleExamChange}>
          <SelectTrigger className="w-auto min-w-[120px] max-w-[180px] sm:w-[180px] h-8 text-sm">
            <SelectValue placeholder="Select Exam">
              {examId ? (exams?.find(e => e.id === examId)?.name ?? 'Select Exam') : 'Select Exam'}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {exams.map((exam) => (
              <SelectItem key={exam.id} value={exam.id}>
                {exam.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {examId && exams?.find(e => e.id === examId) && (
        <div className="flex items-center gap-2 ml-2 border-l pl-4">
          <AccessBadge access={exams.find(e => e.id === examId)?.access} />
          {exams.find(e => e.id === examId)?.access?.level === "OWNER" && !exams.find(e => e.id === examId)?.access?.is_global && (
            <ShareDialog entityType="exam" entityId={examId} />
          )}
        </div>
      )}

      {examId && (
        <div className="flex items-center ml-2">
          <span className="text-xs font-medium text-muted-foreground mr-2 hidden sm:inline-block">Subject:</span>
          <Select value={subjectId || ''} onValueChange={handleSubjectChange}>
            <SelectTrigger className="w-auto min-w-[120px] max-w-[180px] sm:w-[180px] h-8 text-sm">
              <SelectValue placeholder={isLoadingSubjects ? "Loading..." : "Select Subject"}>
                {subjectId ? (subjects?.find(s => s.id === subjectId)?.name ?? 'Select Subject') : 'Select Subject'}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {subjects && subjects.length > 0 ? (
                subjects.map((subject) => (
                  <SelectItem key={subject.id} value={subject.id}>
                    {subject.name}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="none" disabled>
                  No subjects found
                </SelectItem>
              )}
            </SelectContent>
          </Select>
          
          {subjectId && subjects?.find(s => s.id === subjectId)?.access?.has_edit && (
            <div className="ml-2">
              <DropdownMenu>
                <DropdownMenuTrigger className="h-8 w-8 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground outline-none">
                  <Settings className="h-4 w-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem 
                    className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
                    onClick={() => {
                      if (confirm("Delete all resources in this subject? This action cannot be undone.")) {
                        clearResourcesMutation.mutate();
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Clear All Resources
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

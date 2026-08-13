'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { createClient } from '@/lib/supabase';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CreateExamDialog } from '@/components/workspace/CreateExamDialog';
import { CreateSubjectDialog } from '@/components/workspace/CreateSubjectDialog';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { BookOpen, FolderOpen, ChevronRight } from 'lucide-react';

type Exam = { id: string; name: string; is_college: boolean; exam_type: string; description?: string; created_at: string };
type Subject = { id: string; exam_id: string; name: string; code?: string; description?: string; created_at: string };

export default function WorkspaceSetupPage() {
  const router = useRouter();
  const [examDialogOpen, setExamDialogOpen] = useState(false);
  const [subjectDialogOpen, setSubjectDialogOpen] = useState(false);

  const { examId, setExamId, subjectId, setSubjectId } = useWorkspaceStore();

  useEffect(() => {
    const checkSession = async () => {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
      }
    };
    checkSession();
  }, [router]);

  const { data: exams, isLoading: isLoadingExams, error: examsError } = useQuery<Exam[]>({
    queryKey: ['exams'],
    queryFn: async () => {
      const res = await api.get('/api/v1/exams');
      return res.data;
    },
    retry: false
  });

  const { data: subjects, isLoading: isLoadingSubjects } = useQuery<Subject[]>({
    queryKey: ['subjects', examId],
    queryFn: async () => {
      if (!examId) return [];
      const res = await api.get(`/api/v1/subjects?exam_id=${examId}`);
      return res.data;
    },
    enabled: !!examId,
  });

  // Protect against stale UUID display if exam is removed
  useEffect(() => {
    if (exams && examId) {
      if (!exams.find(e => e.id === examId)) {
        setExamId(null);
      }
    }
  }, [exams, examId, setExamId]);

  const selectedExam = exams?.find(e => e.id === examId);

  return (
    <main className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Exam & Subject Manager</h1>
        <p className="text-muted-foreground mt-2">Create and organize the examinations and subjects used by Learnova.</p>
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold tracking-tight">Your Exams</h2>
          <Button onClick={() => setExamDialogOpen(true)}>+ Add Exam</Button>
        </div>

        {isLoadingExams ? (
          <div className="flex justify-center items-center h-32 bg-muted/20 rounded-lg">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : examsError ? (
          <div className="bg-destructive/10 text-destructive p-4 rounded-md flex items-center justify-between">
            <span>Unable to load exams. Ensure backend is running.</span>
          </div>
        ) : !exams || exams.length === 0 ? (
          <div className="text-center py-12 bg-muted/20 rounded-lg border border-dashed">
            <h3 className="text-lg font-semibold mb-2">No exams yet.</h3>
            <p className="text-muted-foreground mb-4">Create your first examination workspace to get started.</p>
            <Button onClick={() => setExamDialogOpen(true)}>+ Create Exam</Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {exams.map((exam) => (
              <Card 
                key={exam.id} 
                className={`cursor-pointer transition-all hover:border-primary/50 ${examId === exam.id ? 'border-primary' : ''}`}
                onClick={() => setExamId(exam.id)}
              >
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-lg">{exam.name}</CardTitle>
                    {exam.exam_type && (
                      <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full font-medium">
                        {exam.exam_type}
                      </span>
                    )}
                  </div>
                  {exam.description && (
                    <CardDescription className="line-clamp-2 mt-1">
                      {exam.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="flex items-center text-sm text-muted-foreground">
                    <BookOpen className="h-4 w-4 mr-2" />
                    <span>Select to view subjects</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {selectedExam && (
        <div className="space-y-4 pt-6 border-t animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold tracking-tight">Subjects for {selectedExam.name}</h2>
            </div>
            <Button onClick={() => setSubjectDialogOpen(true)} variant="secondary">+ Add Subject</Button>
          </div>

          {isLoadingSubjects ? (
            <div className="flex justify-center items-center h-32 bg-muted/20 rounded-lg">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : !subjects || subjects.length === 0 ? (
            <div className="text-center py-12 bg-muted/20 rounded-lg border border-dashed">
              <h3 className="text-lg font-semibold mb-2">No subjects configured for {selectedExam.name}.</h3>
              <p className="text-muted-foreground mb-4">Add subjects to start building the knowledge base.</p>
              <Button onClick={() => setSubjectDialogOpen(true)}>+ Add Subject</Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {subjects.map((subject) => (
                <Card 
                  key={subject.id} 
                  className="cursor-pointer transition-all hover:bg-muted/50"
                  onClick={() => {
                    setSubjectId(subject.id);
                    router.push('/workspace/knowledge');
                  }}
                >
                  <CardHeader className="py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-md flex items-center">
                          {subject.name}
                        </CardTitle>
                        {subject.code && (
                          <CardDescription className="text-xs mt-1">Code: {subject.code}</CardDescription>
                        )}
                      </div>
                      <ChevronRight className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      <CreateExamDialog open={examDialogOpen} onOpenChange={setExamDialogOpen} />
      {selectedExam && (
        <CreateSubjectDialog 
          open={subjectDialogOpen} 
          onOpenChange={setSubjectDialogOpen} 
          examId={selectedExam.id} 
          examName={selectedExam.name} 
        />
      )}
    </main>
  );
}

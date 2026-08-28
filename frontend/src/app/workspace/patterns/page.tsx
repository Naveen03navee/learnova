'use client';

import { useWorkspaceStore } from '@/store/workspaceStore';
import { GlobalContextSelector } from '@/components/workspace/GlobalContextSelector';
import { Button } from '@/components/ui/button';
import { BookOpen, FileText, UploadIcon, FileIcon, ChevronDown, CheckCircle2, Trash2, Loader2, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import { parseUtc } from '@/lib/date';
import { useState, useRef } from 'react';
import { notify } from '@/store/notificationStore';
import { Share2 as ShareDialogIcon, MoreVerticalIcon } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AccessBadge } from "@/components/sharing/AccessBadge";
import { ShareDialog } from "@/components/sharing/ShareDialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ExamPattern {
  id: string;
  file_name: string;
  status: string;
  analysis_data?: {
    question_count: number;
    total_marks: number;
  };
  extracted_example_count?: number;
  created_at: string;
  access?: any;
}

function PatternPreviewDialog({ patternId }: { patternId: string }) {
  const { data: chunks, isLoading } = useQuery({
    queryKey: ['pattern_chunks', patternId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/patterns/${patternId}/chunks`);
      return res.data;
    },
  });

  return (
    <Dialog>
      <DialogTrigger render={<Button variant="outline" size="sm" className="w-full mt-4" />}>
        <BookOpen className="w-4 h-4 mr-2" /> Preview Extracted Questions
      </DialogTrigger>
      <DialogContent className="w-[calc(100%-2rem)] sm:max-w-3xl h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Extracted Representative Questions</DialogTitle>
        </DialogHeader>
        <ScrollArea className="flex-1 pr-4">
          {isLoading ? (
            <div className="p-4 text-center text-muted-foreground">Loading...</div>
          ) : chunks?.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">No questions extracted.</div>
          ) : (
            <div className="space-y-4 py-4">
              {chunks?.map((chunk: any, i: number) => (
                <div key={chunk.id} className="p-4 border rounded-lg bg-muted/20">
                  <div className="flex gap-2 mb-2">
                    <Badge variant="outline">Q{i + 1}</Badge>
                    {chunk.question_type && <Badge variant="secondary">{chunk.question_type}</Badge>}
                    {chunk.difficulty && <Badge variant="secondary">{chunk.difficulty}</Badge>}
                    {chunk.marks && <Badge variant="secondary">{chunk.marks} Marks</Badge>}
                  </div>
                  <pre className="text-sm whitespace-pre-wrap font-sans mt-2">{chunk.content}</pre>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

export default function PatternsPage() {
  const { examId, subjectId } = useWorkspaceStore();
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [shareOpenId, setShareOpenId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [year, setYear] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!selectedFile || !examId || !subjectId) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', selectedFile);
      form.append('exam_id', examId);
      form.append('subject_id', subjectId);
      if (year) form.append('year', year);
      await api.post('/api/v1/patterns/upload', form);
      notify.success('Pattern uploaded', 'The sample paper is being analyzed in the background.');
      setUploadOpen(false);
      setSelectedFile(null);
      setYear('');
      queryClient.invalidateQueries({ queryKey: ['patterns', examId, subjectId] });
    } catch (err: any) {
      notify.error('Upload failed', err?.response?.data?.detail || err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirmId) return;
    const targetId = deleteConfirmId;
    setDeleteConfirmId(null); // Hide dialog instantly
    
    // Optimistic UI update
    queryClient.setQueryData(['patterns', examId, subjectId], (oldData: any) => {
      if (!oldData) return [];
      return oldData.filter((p: any) => p.id !== targetId);
    });

    try {
      await api.delete(`/api/v1/patterns/${targetId}`);
      notify.success('Pattern deleted');
      // Invalidate to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['patterns', examId, subjectId] });
    } catch (err: any) {
      // Revert on failure (we just invalidate to fetch fresh data)
      queryClient.invalidateQueries({ queryKey: ['patterns', examId, subjectId] });
      notify.error('Delete failed', err?.response?.data?.detail || err.message);
    }
  };

  const { data: patterns = [], isLoading } = useQuery<ExamPattern[]>({
    queryKey: ['patterns', examId, subjectId],
    queryFn: async () => {
      if (!examId || !subjectId) return [];
      const res = await api.get(`/api/v1/patterns?exam_id=${examId}&subject_id=${subjectId}`);
      return res.data;
    },
    enabled: !!examId && !!subjectId,
    refetchInterval: (query) => {
      // Poll every 3 seconds if any pattern is analyzing
      const data = query.state.data;
      if (Array.isArray(data) && data.some(p => p.status === 'ANALYZING' || p.status === 'UPLOADED')) {
        return 3000;
      }
      return false;
    }
  });

  if (!examId || !subjectId) {
    return (
      <main className="p-8 max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Exam Patterns</h1>
            <p className="text-muted-foreground mt-2">Teach Learnova the structure and style of the examination.</p>
          </div>
        </div>
        <Alert variant="default" className="bg-primary/5 border-primary/20">
          <AlertTitle className="text-lg font-semibold flex items-center">
            <BookOpen className="w-5 h-5 mr-2 text-primary" />
            Workspace Context Required
          </AlertTitle>
          <AlertDescription className="mt-2 text-sm text-muted-foreground">
            Please use the context selector in the sidebar to select an Exam and Subject before uploading sample papers.
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  return (
    <main className="p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Exam Patterns</h1>
          <p className="text-muted-foreground mt-2">
            Upload sample question papers from previous years. The AI analyzes these to learn the exact difficulty, tone, formatting, and structural constraints required for this exam.
          </p>
        </div>
        
        <Button className="shrink-0" onClick={() => setUploadOpen(true)}>
          <UploadIcon className="w-4 h-4 mr-2" /> Upload Sample Paper
        </Button>
      </div>

      <div className="mt-8 space-y-4">
        {isLoading ? (
          <div className="text-center p-12 text-muted-foreground border rounded-xl bg-card">Loading patterns...</div>
        ) : patterns.length === 0 ? (
          <div className="border rounded-xl p-12 text-center bg-card flex flex-col items-center justify-center min-h-[250px] shadow-sm">
            <FileText className="w-12 h-12 mb-4 text-muted-foreground/30" strokeWidth={1} />
            <h3 className="text-lg font-semibold mb-2">No patterns uploaded yet</h3>
            <p className="text-muted-foreground mb-6 max-w-md">
              Upload a sample question paper or blueprint to teach Learnova exactly how to format the generated questions.
            </p>
            <Button onClick={() => setUploadOpen(true)} variant="outline" className="border-primary text-primary hover:bg-primary/5">
              <UploadIcon className="w-4 h-4 mr-2" /> Upload Sample Paper
            </Button>
          </div>
        ) : (
          <div className="grid gap-4">
            {patterns.map((pattern) => (
              <Collapsible key={pattern.id} className="border rounded-xl bg-card shadow-sm overflow-hidden">
                <div className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors">
                  <CollapsibleTrigger className="flex items-center gap-3 text-left cursor-pointer flex-1 outline-none text-foreground bg-transparent border-none p-0 text-inherit">
                      <div className="p-2 bg-primary/10 text-primary rounded-lg">
                        <FileIcon className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold">{pattern.file_name}</h4>
                          <AccessBadge access={pattern.access} />
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 text-left">
                          {formatDistanceToNow(parseUtc(pattern.created_at), { addSuffix: true })}
                        </p>
                      </div>
                  </CollapsibleTrigger>
                  <div className="flex items-center gap-4">
                      {pattern.status === 'ACTIVE' ? (
                        <Badge variant="default" className="bg-green-500/10 text-green-600 hover:bg-green-500/20 border-green-500/20">
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Active
                        </Badge>
                      ) : pattern.status === 'ANALYZING' ? (
                        <div className="flex items-center text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 shadow-sm">
                           <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                           Analyzing...
                        </div>
                      ) : pattern.status === 'FAILED' ? (
                        <Badge variant="default" className="bg-red-500/10 text-red-600 hover:bg-red-500/20 border-red-500/20">
                          <AlertCircle className="w-3 h-3 mr-1" /> Failed
                        </Badge>
                      ) : (
                        <Badge variant="outline">{pattern.status}</Badge>
                      )}
                      
                      <div className="flex items-center gap-1 ml-2">
                        <CollapsibleTrigger className="h-8 w-8 shrink-0 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground outline-none bg-transparent border-none p-0">
                            <ChevronDown className="w-4 h-4" />
                        </CollapsibleTrigger>
                        
                        <DropdownMenu>
                          <DropdownMenuTrigger className="h-8 w-8 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground outline-none">
                            <MoreVerticalIcon className="h-4 w-4" />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {pattern.access?.level === 'OWNER' && !pattern.access?.is_global && (
                              <DropdownMenuItem onSelect={() => setShareOpenId(pattern.id)}>
                                <ShareDialogIcon className="w-4 h-4 mr-2" /> Share
                              </DropdownMenuItem>
                            )}
                            
                            {pattern.access?.has_edit && (
                              <DropdownMenuItem className="text-red-600" onClick={() => setDeleteConfirmId(pattern.id)}>
                                <Trash2 className="w-4 h-4 mr-2" /> Delete
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>

                        {pattern.access?.level === 'OWNER' && !pattern.access?.is_global && (
                          <ShareDialog 
                            entityType="pattern" 
                            entityId={pattern.id} 
                            open={shareOpenId === pattern.id}
                            onOpenChange={(isOpen) => {
                              if (!isOpen) setShareOpenId(null);
                            }}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                <CollapsibleContent>
                  <div className="p-4 pt-0 border-t bg-muted/20">
                    {pattern.status === 'FAILED' && (
                      <div className="p-3 mt-4 bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-400 rounded-lg text-sm flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        <span>No exam question paper structure found. Please ensure you upload a <strong>Sample Question Paper / PYQ</strong> rather than a textbook or syllabus. Textbooks should be uploaded under <strong>Knowledge Base</strong>.</span>
                      </div>
                    )}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                      <div className="p-3 bg-background rounded-lg border">
                        <p className="text-xs text-muted-foreground">Status</p>
                        <p className="font-medium mt-1">{pattern.status}</p>
                      </div>
                      {pattern.analysis_data && (
                        <>
                          <div className="p-3 bg-background rounded-lg border">
                            <p className="text-xs text-muted-foreground">Total Questions</p>
                            <p className="font-medium mt-1">{pattern.analysis_data.question_count}</p>
                          </div>
                          <div className="p-3 bg-background rounded-lg border">
                            <p className="text-xs text-muted-foreground">Total Marks</p>
                            <p className="font-medium mt-1">{pattern.analysis_data.total_marks}</p>
                          </div>
                        </>
                      )}
                      <div className="p-3 bg-background rounded-lg border border-primary/20 bg-primary/5">
                        <p className="text-xs text-muted-foreground text-primary">Extracted Examples</p>
                        <p className="font-medium mt-1 text-primary">{pattern.extracted_example_count || 0} chunks</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {pattern.extracted_example_count ? (
                        <PatternPreviewDialog patternId={pattern.id} />
                      ) : null}
                    </div>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        )}
      </div>

      {/* Upload Sample Paper Dialog */}
      {uploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-card rounded-xl shadow-2xl border w-full max-w-md mx-4 p-6 space-y-5">
            <div>
              <h2 className="text-xl font-bold tracking-tight">Upload Sample Paper</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Upload a previous year question paper (PDF, DOCX, or image). The AI will analyze its structure, difficulty, and formatting.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Year (optional)</label>
                <input
                  type="text"
                  placeholder="e.g. 2023"
                  value={year}
                  onChange={e => setYear(e.target.value)}
                  className="w-full border rounded-md px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-1.5 block">File</label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
                  className="hidden"
                  onChange={e => setSelectedFile(e.target.files?.[0] ?? null)}
                />
                {selectedFile ? (
                  <div className="flex items-center justify-between border rounded-md px-3 py-2 bg-muted/30">
                    <span className="text-sm truncate">{selectedFile.name}</span>
                    <button onClick={() => setSelectedFile(null)} className="ml-2 text-muted-foreground hover:text-destructive text-xs">✕</button>
                  </div>
                ) : (
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full border-2 border-dashed border-muted-foreground/30 rounded-md px-4 py-6 text-sm text-muted-foreground hover:border-primary/50 hover:text-primary transition-colors text-center"
                  >
                    <UploadIcon className="w-5 h-5 mx-auto mb-2 opacity-50" />
                    Click to select a file
                  </button>
                )}
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => { setUploadOpen(false); setSelectedFile(null); setYear(''); }}
                disabled={uploading}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
              >
                {uploading ? 'Uploading...' : 'Upload'}
              </Button>
            </div>
          </div>
        </div>
      )}
      <Dialog open={!!deleteConfirmId} onOpenChange={(open) => !open && setDeleteConfirmId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Pattern</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              Are you sure you want to delete this pattern? This will remove the uploaded file and all its extracted structural data. This action cannot be undone.
            </p>
          </div>
          <div className="flex justify-end gap-3 mt-2">
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete Pattern
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}

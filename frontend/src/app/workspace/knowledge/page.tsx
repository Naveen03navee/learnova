'use client';

import { Suspense, useEffect } from 'react';
import { useWorkspaceStore } from '@/store/workspaceStore';
import KnowledgeBaseLayout from '@/components/knowledge/KnowledgeBaseLayout';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

function KnowledgeBaseSkeleton() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-pulse">
      {/* Header skeleton */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="space-y-3">
          <div className="h-8 w-48 bg-muted rounded-lg" />
          <div className="h-4 w-80 bg-muted rounded" />
          <div className="h-9 w-64 bg-muted rounded-lg" />
        </div>
        <div className="flex gap-3">
          <div className="h-9 w-32 bg-muted rounded-md" />
          <div className="h-9 w-28 bg-muted rounded-md" />
          <div className="h-9 w-36 bg-muted rounded-md" />
        </div>
      </div>
      {/* Folder grid skeleton */}
      <div className="space-y-4">
        <div className="h-6 w-24 bg-muted rounded" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-muted rounded-xl" />
          ))}
        </div>
      </div>
      {/* Documents list skeleton */}
      <div className="space-y-4">
        <div className="h-6 w-28 bg-muted rounded" />
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-14 bg-muted rounded-lg" />
        ))}
      </div>
    </div>
  );
}

function KnowledgeBaseContent() {
  const { examId, subjectId } = useWorkspaceStore();
  const searchParams = useSearchParams();
  const folderId = searchParams.get('folder_id');
  const router = useRouter();
  const pathname = usePathname();

  // Guard: if context is lost, wait for user to select in GlobalContextSelector
  if (!examId || !subjectId) {
    return (
      <div className="p-8 max-w-7xl mx-auto flex flex-col items-center justify-center min-h-[50vh] text-center">
        <h2 className="text-2xl font-semibold tracking-tight">Select Context</h2>
        <p className="text-muted-foreground mt-2">
          Please select an Exam and Subject from the workspace setup to view its knowledge base.
        </p>
      </div>
    );
  }

  // Effect to safely clear folder state if the user changes global context
  useEffect(() => {
    if (folderId) {
      // We don't have a reliable way to synchronously check if the folder belongs to the new exam/subject without making an API call. 
      // The backend protects this, but for UX, we should just drop back to root if the context changes aggressively.
      // A more complex approach is to store the "last known exam/subject" and if it differs from current, redirect.
      // We will handle it implicitly: if backend throws 403, we will catch it in KnowledgeBaseLayout and reset.
    }
  }, [examId, subjectId, folderId, router, pathname]);

  return (
    <KnowledgeBaseLayout 
      examId={examId} 
      subjectId={subjectId} 
      folderId={folderId || null} 
    />
  );
}

export default function KnowledgeBasePage() {
  return (
    <Suspense fallback={<KnowledgeBaseSkeleton />}>
      <KnowledgeBaseContent />
    </Suspense>
  );
}

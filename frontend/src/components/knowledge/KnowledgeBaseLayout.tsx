/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars */
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { ChevronRightIcon, UploadIcon, PlusIcon, FolderOpen, DatabaseIcon } from 'lucide-react';
import { useRouter } from 'next/navigation';
import CreateFolderDialog from './CreateFolderDialog';
import UploadResourceDialog from './UploadResourceDialog';
import FolderList from './FolderList';
import ResourceList from './ResourceList';
import RetrievalDialog from './RetrievalDialog';
import { SearchIcon } from 'lucide-react';

type KnowledgeBaseLayoutProps = {
  examId: string;
  subjectId: string;
  folderId: string | null;
};

export default function KnowledgeBaseLayout({ examId, subjectId, folderId }: KnowledgeBaseLayoutProps) {
  const router = useRouter();
  const [isCreateFolderOpen, setIsCreateFolderOpen] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isRetrievalOpen, setIsRetrievalOpen] = useState(false);

  // Fetch Exams to get the name
  const { data: exams } = useQuery({
    queryKey: ['exams'],
    queryFn: async () => {
      const res = await api.get('/api/v1/exams');
      return res.data;
    }
  });

  // Fetch Subjects to get the name
  const { data: subjects } = useQuery({
    queryKey: ['subjects', examId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/subjects?exam_id=${examId}`);
      return res.data;
    },
    enabled: !!examId
  });

  const currentExam = exams?.find((e: any) => e.id === examId);
  const currentSubject = subjects?.find((s: any) => s.id === subjectId);

  // Fetch the current folder tree to build breadcrumbs
  const { data: breadcrumbs, isError: isBreadcrumbError } = useQuery({
    queryKey: ['folder_path', examId, subjectId, folderId],
    queryFn: async () => {
      if (!folderId) return [];
      try {
        const res = await api.get(`/api/v1/folders/${folderId}/path`);
        return res.data;
      } catch (error: any) {
        if (error.response?.status === 403 || error.response?.status === 404) {
          // Context isolation failure or folder deleted, force reset
          handleNavigateFolder(null);
        }
        throw error;
      }
    },
    enabled: !!folderId,
    retry: false
  });

  const handleNavigateFolder = (newFolderId: string | null) => {
    if (newFolderId) {
      router.push(`/workspace/knowledge?folder_id=${newFolderId}`);
    } else {
      router.push(`/workspace/knowledge`);
    }
  };

  return (
    <main className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      
      {/* Header Area */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-primary/80 mb-2">
            <DatabaseIcon className="w-5 h-5" />
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Knowledge Base</h1>
          </div>
          
          <p className="text-muted-foreground text-sm max-w-2xl mb-4">
            Upload notes, textbooks, and reference material used to ground AI-generated questions for {currentExam?.name || 'this exam'} {currentSubject?.name}.
          </p>

          <div className="flex items-center flex-wrap text-sm font-medium bg-muted/50 p-2 rounded-lg border">
            <span 
              className="hover:text-primary cursor-pointer flex items-center px-2 py-1 rounded-md transition-colors hover:bg-background" 
              onClick={() => handleNavigateFolder(null)}
            >
              <FolderOpen className="w-4 h-4 mr-2 text-primary" />
              {currentSubject?.name || 'Root'}
            </span>
            
            {breadcrumbs?.map((crumb: any) => (
              <div key={crumb.id} className="flex items-center">
                <ChevronRightIcon className="w-4 h-4 mx-1 text-muted-foreground" />
                <span 
                  className={`hover:text-primary cursor-pointer px-2 py-1 rounded-md transition-colors hover:bg-background ${crumb.id === folderId ? 'text-primary font-semibold' : 'text-muted-foreground'}`}
                  onClick={() => handleNavigateFolder(crumb.id)}
                >
                  {crumb.name}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex space-x-3 shrink-0">
          <Button variant="outline" onClick={() => setIsRetrievalOpen(true)} className="border-blue-200 text-blue-700 hover:bg-blue-50">
            <SearchIcon className="w-4 h-4 mr-2" /> Test Retrieval
          </Button>
          <Button variant="outline" onClick={() => setIsCreateFolderOpen(true)}>
            <PlusIcon className="w-4 h-4 mr-2" /> New Folder
          </Button>
          <Button onClick={() => setIsUploadOpen(true)} className="bg-primary hover:bg-primary/90">
            <UploadIcon className="w-4 h-4 mr-2" /> Upload Knowledge
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8">
        {/* Folders Section */}
        <section>
          <h2 className="text-xl font-semibold mb-4 tracking-tight flex items-center">
            Folders
          </h2>
          <FolderList 
            examId={examId} 
            subjectId={subjectId} 
            folderId={folderId} 
            onNavigate={handleNavigateFolder}
          />
        </section>

        {/* Documents Section */}
        <section>
          <h2 className="text-xl font-semibold mb-4 tracking-tight">Documents</h2>
          <ResourceList 
            examId={examId} 
            subjectId={subjectId} 
            folderId={folderId} 
          />
        </section>
      </div>

      <CreateFolderDialog 
        open={isCreateFolderOpen} 
        onOpenChange={setIsCreateFolderOpen} 
        examId={examId}
        subjectId={subjectId}
        parentId={folderId}
        locationPath={[
          currentExam?.name || 'Unknown Exam',
          currentSubject?.name || 'Unknown Subject',
          ...(breadcrumbs || []).map((c: any) => c.name)
        ].join(' / ')}
      />

      <UploadResourceDialog 
        open={isUploadOpen} 
        onOpenChange={setIsUploadOpen}
        examId={examId}
        subjectId={subjectId}
        folderId={folderId}
      />

      <RetrievalDialog 
        open={isRetrievalOpen} 
        onOpenChange={setIsRetrievalOpen}
        examId={examId}
        subjectId={subjectId}
        folderId={folderId}
      />
    </main>
  );
}

/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useNotificationStore } from '@/store/notificationStore';
import { FileIcon, MoreVerticalIcon, TrashIcon, DownloadIcon, RefreshCcwIcon, Loader2Icon, CheckCircle2Icon, AlertCircleIcon, Share2 as ShareDialogIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { AccessBadge } from '@/components/sharing/AccessBadge';
import { ShareDialog } from '@/components/sharing/ShareDialog';

type ResourceListProps = {
  examId: string;
  subjectId: string;
  folderId: string | null;
};

export default function ResourceList({ examId, subjectId, folderId }: ResourceListProps) {
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);

  const { data, isLoading } = useQuery({
    queryKey: ['resources', examId, subjectId, folderId],
    queryFn: async () => {
      let url = `/api/v1/resources?exam_id=${examId}&subject_id=${subjectId}`;
      if (folderId) {
        url += `&folder_id=${folderId}`;
      }
      const res = await api.get(url);
      return res.data; // returns { items: [...], total, page, page_size }
    },
    // Poll every 3 seconds if any item is not READY or FAILED
    refetchInterval: (query) => {
      const items = query.state?.data?.items || [];
      const isProcessing = items.some((item: any) => 
        !['READY', 'FAILED'].includes(item.status)
      );
      return isProcessing ? 3000 : false;
    }
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/resources/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resources', examId, subjectId, folderId] });
      notify.success('File deleted', 'The resource was deleted successfully.');
    },
    onError: (err: any) => {
      notify.error('Delete failed', err.response?.data?.detail || "Failed to delete file");
    }
  });
  
  const handleDownload = async (resource: any) => {
    try {
      const res = await api.get(`/api/v1/resources/${resource.id}/download`);
      if (res.data?.download_url) {
        window.open(res.data.download_url, '_blank');
      }
    } catch (err: any) {
      notify.error('Download failed', err.response?.data?.detail || "Failed to download file");
    }
  };

  const retryMut = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/resources/${id}/process`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resources', examId, subjectId, folderId] });
      notify.success('Processing restarted', 'The resource has been added back to the processing queue.');
    },
    onError: (err: any) => {
      notify.error('Retry failed', err.response?.data?.detail || "Failed to retry processing");
    }
  });

  if (isLoading) {
    return (
      <div className="flex flex-col space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between p-4 border rounded-xl bg-muted/10 animate-pulse">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-muted rounded shrink-0"></div>
              <div className="space-y-2">
                <div className="h-4 bg-muted rounded w-48"></div>
                <div className="h-3 bg-muted rounded w-24"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  const resources = data?.items || [];

  const getStatusDisplay = (status: string) => {
    switch(status) {
      case 'READY': return <div className="flex items-center text-green-600 bg-green-50 px-2 py-1 rounded-md text-xs font-medium"><CheckCircle2Icon className="w-3.5 h-3.5 mr-1.5" />Ready for generation</div>;
      case 'FAILED': return <div className="flex items-center text-red-600 bg-red-50 px-2 py-1 rounded-md text-xs font-medium"><AlertCircleIcon className="w-3.5 h-3.5 mr-1.5" />Processing failed</div>;
      case 'UPLOADED': return <div className="flex items-center text-blue-600 bg-blue-50 px-2 py-1 rounded-md text-xs font-medium"><Loader2Icon className="w-3.5 h-3.5 mr-1.5 animate-spin" />Uploading</div>;
      case 'PROCESSING':
      case 'EXTRACTING':
      case 'OCR': return <div className="flex items-center text-blue-600 bg-blue-50 px-2 py-1 rounded-md text-xs font-medium"><Loader2Icon className="w-3.5 h-3.5 mr-1.5 animate-spin" />Extracting text</div>;
      case 'CLEANING': return <div className="flex items-center text-blue-600 bg-blue-50 px-2 py-1 rounded-md text-xs font-medium"><Loader2Icon className="w-3.5 h-3.5 mr-1.5 animate-spin" />Cleaning content</div>;
      case 'CHUNKING': return <div className="flex items-center text-purple-600 bg-purple-50 px-2 py-1 rounded-md text-xs font-medium"><Loader2Icon className="w-3.5 h-3.5 mr-1.5 animate-spin" />Chunking knowledge</div>;
      case 'EMBEDDING': return <div className="flex items-center text-purple-600 bg-purple-50 px-2 py-1 rounded-md text-xs font-medium"><Loader2Icon className="w-3.5 h-3.5 mr-1.5 animate-spin" />Generating embeddings</div>;
      case 'INDEXING': return <div className="flex items-center text-purple-600 bg-purple-50 px-2 py-1 rounded-md text-xs font-medium"><Loader2Icon className="w-3.5 h-3.5 mr-1.5 animate-spin" />Indexing</div>;
      default: return <span>{status}</span>;
    }
  };

  if (resources.length === 0) {
    return (
      <div className="border rounded-xl p-8 text-center bg-card flex flex-col items-center justify-center min-h-[160px]">
        <FileIcon className="w-10 h-10 mb-4 text-muted-foreground/30" strokeWidth={1} />
        {folderId ? (
          <>
            <p className="text-foreground font-medium">This folder is empty.</p>
            <p className="text-sm text-muted-foreground mt-1">Upload knowledge documents to ground your AI generation.</p>
          </>
        ) : (
          <>
            <p className="text-foreground font-medium">Build your knowledge base</p>
            <p className="text-sm text-muted-foreground mt-1">Upload notes, textbooks, and reference material.</p>
          </>
        )}
      </div>
    );
  }

  const [shareOpenId, setShareOpenId] = useState<string | null>(null);

  return (
    <div className="flex flex-col space-y-2">
      {resources.map((resource: any) => (
        <div 
          key={resource.id} 
          className="group flex items-center justify-between p-4 border rounded-lg hover:border-primary/50 hover:bg-muted/30 transition-colors"
        >
          <div className="flex items-center space-x-4 overflow-hidden">
            <FileIcon className="w-6 h-6 text-gray-500 shrink-0" />
            <div className="flex flex-col overflow-hidden min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-medium truncate">{resource.name}</span>
                <AccessBadge access={resource.access} />
              </div>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground mt-1">
                <span>{resource.file_type.split('/').pop()?.toUpperCase()}</span>
                <span>•</span>
                <span>{(resource.file_size / 1024 / 1024).toFixed(2)} MB</span>
                <span>•</span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium">
                  {getStatusDisplay(resource.status)}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <ShareDialog 
              entityType="resource" 
              entityId={resource.id} 
              open={shareOpenId === resource.id}
              onOpenChange={(o) => setShareOpenId(o ? resource.id : null)}
              trigger={null}
            />
            <DropdownMenu>
              <DropdownMenuTrigger className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-muted outline-none">
                <MoreVerticalIcon className="h-4 w-4 text-muted-foreground" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {resource.status === 'FAILED' && (
                  <DropdownMenuItem onClick={() => retryMut.mutate(resource.id)}>
                    <RefreshCcwIcon className="w-4 h-4 mr-2 text-blue-600" /> Retry Processing
                  </DropdownMenuItem>
                )}
                
                {resource.access?.has_view && (
                  <DropdownMenuItem onClick={() => handleDownload(resource)}>
                    <DownloadIcon className="w-4 h-4 mr-2" /> Download File
                  </DropdownMenuItem>
                )}
                
                {resource.access?.level === 'OWNER' && !resource.access?.is_global && (
                  <DropdownMenuItem onSelect={() => setShareOpenId(resource.id)}>
                    <ShareDialogIcon className="w-4 h-4 mr-2" /> Share
                  </DropdownMenuItem>
                )}

                
                {resource.access?.has_edit && (
                  <DropdownMenuItem className="text-red-600" onClick={() => {
                    if (confirm(`Delete file "${resource.name}"? This will permanently delete it and its associated processed knowledge data.`)) {
                      deleteMut.mutate(resource.id);
                    }
                  }}>
                    <TrashIcon className="w-4 h-4 mr-2" /> Delete
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      ))}
    </div>
  );
}

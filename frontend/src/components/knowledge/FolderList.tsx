/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { FolderIcon, MoreVerticalIcon, TrashIcon, EditIcon } from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

type FolderListProps = {
  examId: string;
  subjectId: string;
  folderId: string | null;
  onNavigate: (folderId: string) => void;
};

export default function FolderList({ examId, subjectId, folderId, onNavigate }: FolderListProps) {
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);

  const { data: folders, isLoading } = useQuery({
    queryKey: ['folders', examId, subjectId, folderId],
    queryFn: async () => {
      let url = `/api/v1/folders?exam_id=${examId}&subject_id=${subjectId}`;
      if (folderId) {
        url += `&parent_id=${folderId}`;
      }
      const res = await api.get(url);
      return res.data;
    }
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/folders/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders', examId, subjectId, folderId] });
      notify.success('Folder deleted', 'The folder was deleted successfully.');
    },
    onError: (err: any) => {
      notify.error('Delete failed', err.response?.data?.detail || "Failed to delete folder");
    }
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex items-center space-x-3 p-4 border rounded-lg bg-muted/10 animate-pulse">
            <div className="w-5 h-5 bg-muted rounded shrink-0"></div>
            <div className="h-4 bg-muted rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!folders || folders.length === 0) {
    return (
      <div className="border rounded-xl p-8 text-center bg-card flex flex-col items-center justify-center min-h-[160px]">
        <FolderIcon className="w-10 h-10 mb-4 text-muted-foreground/30" strokeWidth={1} />
        {folderId ? (
          <>
            <p className="text-foreground font-medium">This folder is empty.</p>
            <p className="text-sm text-muted-foreground mt-1">Create a subfolder or upload knowledge documents here.</p>
          </>
        ) : (
          <>
            <p className="text-foreground font-medium">Build your knowledge base</p>
            <p className="text-sm text-muted-foreground mt-1">Create a folder or upload notes/textbooks to begin grounding Learnova.</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {folders.map((folder: any) => (
        <div 
          key={folder.id} 
          className="group flex items-center justify-between p-4 border rounded-xl hover:border-primary/50 hover:bg-muted/30 transition-all duration-200 cursor-pointer shadow-sm hover:shadow"
          onClick={() => onNavigate(folder.id)}
        >
          <div className="flex items-center space-x-3 overflow-hidden">
            <FolderIcon className="w-5 h-5 text-blue-500 shrink-0 fill-blue-500/20" />
            <span className="font-medium truncate text-sm">{folder.name}</span>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-muted outline-none" onClick={e => e.stopPropagation()}>
                <MoreVerticalIcon className="h-4 w-4 text-muted-foreground" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => {
                e.stopPropagation();
                const newName = prompt("Enter new folder name:", folder.name);
                if (newName && newName.trim() !== folder.name) {
                  // Actually should be a mutation, keeping it simple for now
                  api.put(`/api/v1/folders/${folder.id}`, { name: newName })
                    .then(() => queryClient.invalidateQueries({ queryKey: ['folders', examId, subjectId, folderId] }))
                    .catch(err => alert(err.response?.data?.detail || "Failed to rename folder"));
                }
              }}>
                <EditIcon className="w-4 h-4 mr-2" /> Rename
              </DropdownMenuItem>
              <DropdownMenuItem className="text-red-600" onClick={(e) => {
                e.stopPropagation();
                if (confirm(`Delete folder "${folder.name}"?`)) {
                  deleteMut.mutate(folder.id);
                }
              }}>
                <TrashIcon className="w-4 h-4 mr-2" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ))}
    </div>
  );
}

/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useNotificationStore } from '@/store/notificationStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';

type CreateFolderDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  examId: string;
  subjectId: string;
  parentId: string | null;
  locationPath: string;
};

export default function CreateFolderDialog({ open, onOpenChange, examId, subjectId, parentId, locationPath }: CreateFolderDialogProps) {
  const [folderName, setFolderName] = useState('');
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);

  const createMut = useMutation({
    mutationFn: async (name: string) => {
      await api.post('/api/v1/folders', {
        name,
        exam_id: examId,
        subject_id: subjectId,
        parent_id: parentId
      });
    },
    onSuccess: (_, name) => {
      queryClient.invalidateQueries({ queryKey: ['folders', examId, subjectId, parentId] });
      notify.success('Folder created', `Created folder "${name}"`);
      setFolderName('');
      onOpenChange(false);
    },
    onError: (err: any) => {
      notify.error('Creation failed', err.response?.data?.detail || "Failed to create folder");
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Folder</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <div className="text-sm font-medium">Location</div>
            <div className="p-2 bg-muted rounded-md text-sm text-muted-foreground flex items-center">
              {locationPath}
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="text-sm font-medium">Folder Name</div>
            <Input 
              autoFocus
              value={folderName} 
              onChange={e => setFolderName(e.target.value)} 
              placeholder="e.g. Chapter 1 Notes" 
              onKeyDown={e => {
                if (e.key === 'Enter' && folderName.trim()) {
                  createMut.mutate(folderName);
                }
              }}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button 
            onClick={() => createMut.mutate(folderName)} 
            disabled={!folderName.trim() || createMut.isPending}
          >
            {createMut.isPending ? "Creating..." : "Create Folder"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

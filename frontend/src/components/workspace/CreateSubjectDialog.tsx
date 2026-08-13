'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useNotificationStore } from '@/store/notificationStore';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface CreateSubjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  examId: string;
  examName: string;
}

export function CreateSubjectDialog({ open, onOpenChange, examId, examName }: CreateSubjectDialogProps) {
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/api/v1/subjects', {
        exam_id: examId,
        name,
        code: code || undefined,
        description: description || undefined,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subjects', examId] });
      notify.success('Subject created', `Successfully created ${name}`);
      onOpenChange(false);
      setName('');
      setCode('');
      setDescription('');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to create subject';
      notify.error('Creation failed', message);
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Subject</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Exam</Label>
            <div className="p-2 bg-muted rounded-md text-sm">{examName}</div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="subject-name">Subject Name</Label>
            <Input 
              id="subject-name" 
              placeholder="e.g. Physics, Biology" 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="subject-code">Subject Code (optional)</Label>
            <Input 
              id="subject-code" 
              placeholder="e.g. PHY-101" 
              value={code} 
              onChange={(e) => setCode(e.target.value)} 
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="subject-desc">Description (optional)</Label>
            <Input 
              id="subject-desc" 
              placeholder="Short description..." 
              value={description} 
              onChange={(e) => setDescription(e.target.value)} 
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button 
            disabled={!name.trim() || mutation.isPending} 
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? 'Creating...' : 'Create Subject'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface CreateExamDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateExamDialog({ open, onOpenChange }: CreateExamDialogProps) {
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);
  const [name, setName] = useState('');
  const [examType, setExamType] = useState('Competitive');
  const [description, setDescription] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/api/v1/exams', {
        name,
        exam_type: examType,
        description,
        is_college: examType === 'College / University',
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] });
      notify.success('Exam created', `Successfully created ${name}`);
      onOpenChange(false);
      setName('');
      setDescription('');
      setExamType('Competitive');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to create exam';
      notify.error('Creation failed', message);
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Exam</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="exam-name">Exam Name</Label>
            <Input 
              id="exam-name" 
              placeholder="e.g. KCET, NEET" 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="exam-type">Exam Type</Label>
            <Select value={examType} onValueChange={(val) => setExamType(val || 'Competitive')}>
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Competitive">Competitive Exam</SelectItem>
                <SelectItem value="College / University">College / University</SelectItem>
                <SelectItem value="Custom">Custom</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="exam-desc">Description (optional)</Label>
            <Input 
              id="exam-desc" 
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
            {mutation.isPending ? 'Creating...' : 'Create Exam'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

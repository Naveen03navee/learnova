/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useState, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { notify } from '@/store/notificationStore';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { FileIcon, UploadCloudIcon, FolderOpen, Loader2Icon, XIcon } from 'lucide-react';

type UploadResourceDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  examId: string;
  subjectId: string;
  folderId: string | null;
};

export default function UploadResourceDialog({ open, onOpenChange, examId, subjectId, folderId }: UploadResourceDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  // Access the cached exams/subjects/breadcrumbs to show destination
  const { data: examsData } = useQuery({ 
    queryKey: ['exams'],
    queryFn: async () => (await api.get('/api/v1/exams')).data
  });
  const { data: subjectsData } = useQuery({ 
    queryKey: ['subjects', examId],
    queryFn: async () => examId ? (await api.get(`/api/v1/subjects?exam_id=${examId}`)).data : [],
    enabled: !!examId
  });
  const { data: breadcrumbsData } = useQuery({ 
    queryKey: ['folder_path', examId, subjectId, folderId],
    queryFn: async () => {
      if (!examId || !subjectId || !folderId) return [];
      return (await api.get(`/api/v1/folders/${folderId}/path`)).data;
    },
    enabled: !!folderId
  });

  const exams = (examsData as any[]) || [];
  const subjects = (subjectsData as any[]) || [];
  const breadcrumbs = (breadcrumbsData as any[]) || [];

  const currentExam = exams.find((e: any) => e.id === examId);
  const currentSubject = subjects.find((s: any) => s.id === subjectId);

  const handleUpload = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setProgress(0);
    setIsProcessing(false);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('exam_id', examId);
    formData.append('subject_id', subjectId);
    if (folderId) {
      formData.append('folder_id', folderId);
    }

    try {
      const res = await api.post('/api/v1/resources', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(percentCompleted);
          }
        }
      });
      
      const resource = res.data;
      setIsUploading(false);
      setIsProcessing(true);
      setProcessingStatus('Starting document extraction...');
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const eventSource = new EventSource(`${apiUrl}/api/v1/resources/${resource.id}/events`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setProcessingStatus(data.message || data.status);
        setProcessingProgress(data.progress * 100);
        
        if (["READY", "FAILED"].includes(data.status)) {
            eventSource.close();
            if (data.status === "READY") {
                notify.success('Processing complete', 'Document is ready for generation.');
            } else {
                notify.error('Processing failed', data.message);
            }
            queryClient.invalidateQueries({ queryKey: ['resources', examId, subjectId, folderId] });
            setFile(null);
            setIsProcessing(false);
            onOpenChange(false);
        }
      };
      
      eventSource.onerror = () => {
          // If connection fails, assume background task is still going and let them close.
          eventSource.close();
          queryClient.invalidateQueries({ queryKey: ['resources', examId, subjectId, folderId] });
          notify.info('Upload complete', 'Document processing in background.');
          setFile(null);
          setIsProcessing(false);
          onOpenChange(false);
      };
      
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to upload file';
      notify.error('Upload failed', msg);
      setIsUploading(false);
      setProgress(0);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };
  
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };
  
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      if (!isUploading && !isProcessing) onOpenChange(isOpen);
    }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center text-xl">
            <UploadCloudIcon className="w-5 h-5 mr-2 text-primary" />
            Upload Knowledge Document
          </DialogTitle>
        </DialogHeader>

        {/* Destination Context Box */}
        <div className="bg-muted/30 p-3 rounded-lg border text-sm flex flex-col space-y-1 mb-2">
          <span className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Destination Context</span>
          <div className="flex items-center flex-wrap gap-x-1 font-medium">
            <span className="text-primary">{currentExam?.name || 'Exam'}</span>
            <span className="text-muted-foreground">/</span>
            <span>{currentSubject?.name || 'Subject'}</span>
            <span className="text-muted-foreground">/</span>
            <FolderOpen className="w-3.5 h-3.5 text-blue-500 inline mx-0.5" />
            {breadcrumbs && breadcrumbs.length > 0 ? (
              <span>{breadcrumbs.map((b: any) => b.name).join(' / ')}</span>
            ) : (
              <span>Root Folder</span>
            )}
          </div>
        </div>
        
        <div 
          className={`relative py-10 flex flex-col items-center justify-center border-2 border-dashed rounded-xl transition-colors duration-200 ${isDragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/20 hover:border-primary/50 bg-card'}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          {!file ? (
            <>
              <div className="p-4 rounded-full bg-primary/10 mb-4">
                <UploadCloudIcon className="w-8 h-8 text-primary" />
              </div>
              <h3 className="font-medium text-lg mb-1">Drag and drop your file here</h3>
              <p className="text-sm text-muted-foreground mb-6">Supports PDF, DOCX, TXT. Max 50MB.</p>
              
              <Button 
                variant="outline" 
                disabled={isUploading || isProcessing}
                onClick={() => fileInputRef.current?.click()}
                className="bg-background shadow-sm hover:bg-muted"
              >
                Browse Files
              </Button>
            </>
          ) : (
            <div className="w-full px-6">
              <div className="flex items-center p-4 bg-background border rounded-xl shadow-sm">
                <div className="p-2 bg-blue-100 rounded-lg mr-4">
                  <FileIcon className="w-6 h-6 text-blue-600 shrink-0" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate text-foreground">{file.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                {!isUploading && !isProcessing && (
                  <Button variant="ghost" size="icon" className="shrink-0 ml-2 rounded-full h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => setFile(null)}>
                    <XIcon className="w-4 h-4" />
                  </Button>
                )}
              </div>
              
              {isUploading && (
                <div className="mt-5 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center font-medium text-primary">
                      <Loader2Icon className="w-3.5 h-3.5 mr-2 animate-spin" /> Uploading securely...
                    </span>
                    <span className="text-muted-foreground font-medium">{progress}%</span>
                  </div>
                  <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary transition-all duration-300 ease-out" 
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}
              
              {isProcessing && (
                <div className="mt-5 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center font-medium text-blue-600">
                      <Loader2Icon className="w-3.5 h-3.5 mr-2 animate-spin" /> {processingStatus}
                    </span>
                    <span className="text-muted-foreground font-medium">{Math.round(processingProgress)}%</span>
                  </div>
                  <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 transition-all duration-300 ease-out" 
                      style={{ width: `${processingProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          <input 
            type="file" 
            className="hidden" 
            ref={fileInputRef}
            accept=".pdf,.docx,.doc,.txt"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                setFile(e.target.files[0]);
              }
            }}
            disabled={isUploading || isProcessing}
          />
        </div>
        
        <DialogFooter className="sm:justify-between mt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isUploading || isProcessing}>Cancel</Button>
          <Button 
            onClick={handleUpload} 
            disabled={!file || isUploading || isProcessing}
            className="px-8 shadow-sm"
          >
            {isUploading ? "Uploading..." : isProcessing ? "Processing..." : "Upload Document"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

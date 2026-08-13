'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2Icon, SearchIcon, FileTextIcon, FolderIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

type RetrievalDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  examId: string;
  subjectId: string;
  folderId: string | null;
};

type RetrievalResult = {
  chunk_id: string;
  resource_id: string;
  resource_name: string;
  folder_id: string | null;
  page_number: number | null;
  chunk_index: number;
  content: string;
  similarity: number;
};

export default function RetrievalDialog({
  open,
  onOpenChange,
  examId,
  subjectId,
  folderId,
}: RetrievalDialogProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<RetrievalResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError('');
    setHasSearched(false);

    try {
      const res = await api.post('/api/v1/retrieval/search', {
        exam_id: examId,
        subject_id: subjectId,
        folder_id: folderId || undefined, // undefined prevents sending null if API strictly expects absent/uuid
        query: query.trim(),
        top_k: 8,
      });
      setResults(res.data.results);
      setHasSearched(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to search the knowledge base.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Test Knowledge Retrieval</DialogTitle>
          <DialogDescription>
            Search through {folderId ? 'this folder and its descendants' : 'all study materials in this subject'}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSearch} className="flex items-end gap-3 pt-4 pb-2">
          <div className="space-y-2 flex-1">
            <Label htmlFor="query">Search Query</Label>
            <Input
              id="query"
              placeholder="e.g. Newton's second law"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <Button type="submit" disabled={isSearching || !query.trim()}>
            {isSearching ? <Loader2Icon className="w-4 h-4 mr-2 animate-spin" /> : <SearchIcon className="w-4 h-4 mr-2" />}
            Search
          </Button>
        </form>

        <div className="flex-1 overflow-y-auto space-y-4 py-4 min-h-[300px]">
          {isSearching && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Loader2Icon className="w-8 h-8 animate-spin mb-4" />
              <p>Searching knowledge...</p>
            </div>
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-4 rounded-md border border-red-200">
              {error}
            </div>
          )}

          {!isSearching && hasSearched && results.length === 0 && !error && (
            <div className="text-center text-muted-foreground mt-8">
              No highly relevant information found for this query in the selected scope.
            </div>
          )}

          {!isSearching && results.length > 0 && (
            <div className="space-y-3">
              <div className="text-sm font-medium text-muted-foreground px-1">
                {results.length} relevant chunks found
              </div>
              {results.map((result) => (
                <Card key={result.chunk_id} className="overflow-hidden">
                  <CardContent className="p-4 space-y-2">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2 text-sm font-semibold text-primary">
                        <FileTextIcon className="w-4 h-4" />
                        <span>{result.resource_name}</span>
                      </div>
                      <div className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 font-medium whitespace-nowrap">
                        Similarity: {(result.similarity * 100).toFixed(1)}%
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                      <span>Chunk {result.chunk_index}</span>
                      {result.page_number !== null && (
                        <>
                          <span>•</span>
                          <span>Page {result.page_number}</span>
                        </>
                      )}
                    </div>
                    
                    <div className="text-sm bg-muted/50 p-3 rounded-md mt-2 text-slate-800 dark:text-slate-200 leading-relaxed max-h-48 overflow-y-auto">
                      {result.content.length > 1000 
                        ? result.content.substring(0, 1000) + '...'
                        : result.content}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

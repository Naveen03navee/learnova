"use client";

import { useQuery } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, FileText, Loader2, BookOpen } from "lucide-react";
import { format } from "date-fns";
import { useNotificationStore } from "@/store/notificationStore";

export default function AnswersPage() {
  const { examId, subjectId } = useWorkspaceStore();
  const notify = useNotificationStore(s => s.notify);

  const { data: papers = [], isLoading } = useQuery({
    queryKey: ["papers", examId, "APPROVED"],
    queryFn: () => {
      const url = examId 
        ? `/api/v1/papers?exam_id=${examId}&status=APPROVED`
        : `/api/v1/papers?status=APPROVED`;
      return api.get(url).then(res => res.data);
    },
  });

  const handleDownload = async (paperId: string, type: 'answer_key' | 'question_paper') => {
    const endpoint = type === 'answer_key' ? 'answer_key/pdf' : 'docx';
    try {
      const response = await api.get(`/api/v1/papers/${paperId}/export/${endpoint}`, {
        responseType: 'blob'
      });
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = type === 'answer_key' ? 'Answer_Key.pdf' : 'Question_Paper.docx';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^";]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed", err);
      notify.error("Download Failed", "There was an error downloading the document.");
    }
  };

  if (!examId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)] text-muted-foreground space-y-4">
        <BookOpen className="w-12 h-12 text-muted-foreground/50" />
        <h2 className="text-xl font-medium">No Exam Selected</h2>
        <p>Please select an Exam from the top bar to view Answer Keys.</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Answer Keys & Explanations</h1>
        <p className="text-muted-foreground mt-2">Manage and export detailed answer keys and explanations for approved papers.</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : papers.length === 0 ? (
        <Card className="bg-muted/30 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground text-center">
            <FileText className="w-10 h-10 mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-1">No Approved Papers Found</h3>
            <p className="text-sm">Build and approve a Question Paper in this subject to generate an Answer Key.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {papers.map((paper: any) => (
            <Card key={paper.id} className="group hover:shadow-md transition-all duration-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg line-clamp-2 leading-tight">{paper.title}</CardTitle>
                <CardDescription>
                  {format(new Date(paper.created_at), "MMM d, yyyy")} • {paper.items?.length || 0} Questions
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button 
                  className="w-full" 
                  variant="outline"
                  onClick={() => handleDownload(paper.id, 'question_paper')}
                >
                  <Download className="w-4 h-4 mr-2" /> Download Question Paper
                </Button>
                <Button 
                  className="w-full" 
                  variant="default"
                  onClick={() => handleDownload(paper.id, 'answer_key')}
                >
                  <Download className="w-4 h-4 mr-2" /> Download Answer Key
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

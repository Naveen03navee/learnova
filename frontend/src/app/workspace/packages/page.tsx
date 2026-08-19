"use client";

import { useQuery } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, Package, Loader2, BookOpen } from "lucide-react";
import { format } from "date-fns";

export default function PackagesPage() {
  const { examId, subjectId } = useWorkspaceStore();

  const { data: papers = [], isLoading } = useQuery({
    queryKey: ["papers", examId, subjectId, "APPROVED"],
    queryFn: () => 
      api.get(`/api/v1/papers?exam_id=${examId}&subject_id=${subjectId}&status=APPROVED`).then(res => res.data),
    enabled: !!examId && !!subjectId,
  });

  const handleDownload = (paperId: string) => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/papers/${paperId}/export/package/zip`, '_blank');
  };

  if (!examId || !subjectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)] text-muted-foreground space-y-4">
        <BookOpen className="w-12 h-12 text-muted-foreground/50" />
        <h2 className="text-xl font-medium">No Context Selected</h2>
        <p>Please select an Exam and Subject from the sidebar to view Packages.</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Final Packages</h1>
        <p className="text-muted-foreground mt-2">Download completely formatted examination packages (ZIP format) including Question Papers and Answer Keys.</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : papers.length === 0 ? (
        <Card className="bg-muted/30 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground text-center">
            <Package className="w-10 h-10 mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-1">No Approved Papers Found</h3>
            <p className="text-sm">Build and approve a Question Paper in this subject to generate a package.</p>
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
              <CardContent>
                <Button 
                  className="w-full" 
                  variant="default"
                  onClick={() => handleDownload(paper.id)}
                >
                  <Download className="w-4 h-4 mr-2" /> Download Package (ZIP)
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, FileText } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { AccessBadge } from "@/components/sharing/AccessBadge";
import { ShareDialog } from "@/components/sharing/ShareDialog";

export function PapersList() {
  const { data: papers = [], isLoading } = useQuery({
    queryKey: ["papers"],
    queryFn: () => api.get("/api/v1/papers").then(res => res.data),
  });

  if (isLoading) {
    return <div className="flex items-center justify-center p-8"><Loader2 className="animate-spin text-blue-500 w-8 h-8" /></div>;
  }

  if (papers.length === 0) {
    return (
      <div className="text-center p-8 text-muted-foreground border rounded-md h-full flex items-center justify-center">
        No papers built yet. Use the "Build New" tab to create your first question paper.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-10">
      {papers.map((p: any) => (
        <Card key={p.id} className="hover:border-blue-300 transition-colors cursor-pointer">
          <Link href={`/workspace/papers/${p.id}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center justify-between">
                <span className="truncate pr-2">{p.title}</span>
                <Badge variant={p.status === "APPROVED" ? "default" : "secondary"}>{p.status}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  <span>{new Date(p.created_at).toLocaleDateString()}</span>
                </div>
                <div>{p.items?.length || 0} Questions</div>
                <div className="pt-2">
                  <AccessBadge access={p.access} />
                </div>
              </div>
            </CardContent>
          </Link>
          {p.access?.level === 'OWNER' && !p.access?.is_global && (
            <div className="px-6 pb-4 flex justify-end">
              <ShareDialog entityType="paper" entityId={p.id} />
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}

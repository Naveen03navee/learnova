"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Loader2, ArrowLeft, CheckCircle, RefreshCcw, ShieldAlert, ShieldCheck, Shield, Download, Info } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { useState, useEffect } from "react";
import { useNotificationStore } from "@/store/notificationStore";
import { AccessBadge } from "@/components/sharing/AccessBadge";
import { ShareDialog } from "@/components/sharing/ShareDialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function PaperReviewPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);
  const [showOverride, setShowOverride] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [checkEvents, setCheckEvents] = useState<any[]>([]);

  const { data: paper, isLoading } = useQuery({
    queryKey: ["paper", id],
    queryFn: () => api.get(`/api/v1/papers/${id}`).then(res => res.data),
  });

  const approveMutation = useMutation({
    mutationFn: (override: boolean = false) => api.post(`/api/v1/papers/${id}/approve`, { override_ai_check: override }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["paper", id] });
      notify.success("Approved", "Paper approved successfully!");
      setShowOverride(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail;
      if (typeof msg === 'string' && msg.includes("Explicit override required")) {
        setShowOverride(true);
      } else {
        notify.error("Action failed", typeof msg === 'string' ? msg : "Failed to approve paper");
      }
    }
  });

  const qualityCheckMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/papers/${id}/quality-check`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["paper", id] });
      notify.success("Quality Check", "AI Quality Check complete.");
      setIsChecking(false);
    },
    onError: (err: any) => {
      notify.error("Check failed", err.response?.data?.detail || "Failed to run quality check");
      setIsChecking(false);
    }
  });

  const handleRunCheck = () => {
    setIsChecking(true);
    setCheckEvents([]);
    
    // Connect to SSE stream
    const token = localStorage.getItem("auth_token") || "";
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/papers/${id}/quality-check/stream?token=${token}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setCheckEvents(prev => [...prev, data]);
        if (data.status === "SUCCESS" || data.status === "ERROR") {
          eventSource.close();
        }
      } catch (e) {}
    };
    
    eventSource.onerror = () => {
      eventSource.close();
    };

    qualityCheckMutation.mutate();
  };

  const handleDownload = async (type: 'answer_key' | 'question_paper_pdf' | 'question_paper_docx') => {
    let endpoint = 'docx';
    let filename = 'Question_Paper.docx';
    
    if (type === 'answer_key') {
        endpoint = 'answer_key/pdf';
        filename = 'Answer_Key.pdf';
    } else if (type === 'question_paper_pdf') {
        endpoint = 'question_paper/pdf';
        filename = 'Question_Paper.pdf';
    }

    try {
      const response = await api.get(`/api/v1/papers/${id}/export/${endpoint}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      notify.error("Download Failed", "There was an error downloading the document.");
    }
  };

  if (isLoading) {
    return <div className="flex h-[calc(100vh-100px)] items-center justify-center"><Loader2 className="animate-spin text-blue-500 w-12 h-12" /></div>;
  }

  if (!paper) {
    return <div className="p-8 text-center">Paper not found.</div>;
  }

  const isDraft = paper.status === "DRAFT";
  const report = paper.quality_report;
  const sections: Record<string, any[]> = {};
  paper.items.forEach((item: any) => {
    if (!sections[item.section_name]) sections[item.section_name] = [];
    sections[item.section_name].push(item);
  });

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto pb-20">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-card p-4 rounded-md border shadow-sm sticky top-0 z-10">
        <div className="flex items-start sm:items-center gap-4">
          <Link href="/workspace/papers">
            <Button variant="ghost" size="icon"><ArrowLeft className="w-5 h-5" /></Button>
          </Link>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              {paper.title} 
              <Badge variant={isDraft ? "secondary" : "default"}>{paper.status}</Badge>
            </h1>
            <p className="text-sm text-muted-foreground">
              Generated on {new Date(paper.created_at).toLocaleString()} • {paper.items.length} Questions
            </p>
            <div className="mt-1">
              <AccessBadge access={paper.access} />
            </div>
          </div>
        </div>
        
        {isDraft ? (
          <div className="flex flex-wrap gap-2 justify-start sm:justify-end items-center">
            {paper.access?.level === 'OWNER' && !paper.access?.is_global && (
              <ShareDialog entityType="paper" entityId={paper.id} />
            )}
            {showOverride && (
              <Button variant="destructive" onClick={() => approveMutation.mutate(true)} disabled={approveMutation.isPending || isChecking}>
                Override AI & Approve
              </Button>
            )}
            {!showOverride && (
              <>
                <Button 
                  variant="outline"
                  onClick={handleRunCheck}
                  disabled={qualityCheckMutation.isPending || isChecking}
                >
                  {(qualityCheckMutation.isPending || isChecking) ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Shield className="w-4 h-4 mr-2" />}
                  Run AI Check
                </Button>
                <Button 
                  variant="default" 
                  onClick={() => approveMutation.mutate(false)}
                  disabled={approveMutation.isPending || isChecking}
                >
                  <CheckCircle className="w-4 h-4 mr-2" /> Approve Paper
                </Button>
              </>
            )}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2 justify-start sm:justify-end items-center">
            {paper.access?.level === 'OWNER' && !paper.access?.is_global && (
              <ShareDialog entityType="paper" entityId={paper.id} />
            )}
            <Link href={`/workspace/papers/${id}/print`} target="_blank">
              <Button variant="outline">Print View</Button>
            </Link>
            <Button variant="outline" onClick={() => handleDownload('question_paper_pdf')}>
              <Download className="w-4 h-4 mr-2" /> Download Question Paper (PDF)
            </Button>
            <Button variant="outline" onClick={() => handleDownload('question_paper_docx')}>
              <Download className="w-4 h-4 mr-2" /> Download Question Paper (DOCX)
            </Button>
            <Button variant="outline" onClick={() => handleDownload('answer_key')}>
              <Download className="w-4 h-4 mr-2" /> Download Answer Key (PDF)
            </Button>
          </div>
        )}
      </div>

      {isChecking && (
        <Card className="border-l-4 border-l-blue-500 animate-pulse">
          <CardHeader className="py-3">
            <div className="flex items-center gap-2 font-semibold">
              <Loader2 className="animate-spin text-blue-500 w-5 h-5" />
              AI Quality Check in Progress...
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
             <div className="bg-muted/30 p-3 rounded h-32 overflow-y-auto font-mono text-xs flex flex-col gap-1">
                {checkEvents.length === 0 ? "Initializing..." : checkEvents.map((evt, i) => (
                  <div key={i} className="flex gap-2">
                    {evt.status === "SUCCESS" ? <span className="text-green-500">✓</span> : 
                     evt.status === "ERROR" ? <span className="text-red-500">✗</span> : 
                     evt.event_type === "WARNING" ? <span className="text-yellow-500">⚠</span> :
                     <span className="text-blue-500">◐</span>}
                    <span>{evt.message}</span>
                  </div>
                ))}
             </div>
          </CardContent>
        </Card>
      )}

      {isDraft && !isChecking && report && !paper.quality_report_stale && (
        <Card className={`border-l-4 ${paper.quality_status === 'PASS' ? 'border-l-green-500' : paper.quality_status === 'WARNING' ? 'border-l-yellow-500' : 'border-l-red-500'}`}>
          <CardHeader className="py-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2 font-semibold">
              {paper.quality_status === 'PASS' ? <ShieldCheck className="text-green-500 w-6 h-6" /> : <ShieldAlert className={paper.quality_status === 'WARNING' ? 'text-yellow-500 w-6 h-6' : 'text-red-500 w-6 h-6'} />}
              <div>
                AI Quality Check
                <div className="text-sm font-normal text-muted-foreground">{report.summary}</div>
              </div>
            </div>
            <div className="text-right">
                <div className="text-2xl font-bold">{report.final_score || report.overall_score}<span className="text-sm text-muted-foreground font-normal">/100</span></div>
                <div className="text-xs uppercase font-semibold tracking-wider text-muted-foreground">{paper.quality_status}</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {report.repair_summary?.repaired && (
                <div className="bg-blue-50 border border-blue-200 text-blue-800 p-3 rounded flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Info className="w-5 h-5 text-blue-500" />
                        <span>AI automatically replaced <strong>{report.repair_summary.replacement_count} questions</strong> to improve paper quality. (Score improved from {report.initial_score} to {report.final_score})</span>
                    </div>
                    
                    <Dialog>
                        <DialogTrigger>
                            <Button variant="outline" size="sm" className="bg-white">View Changes</Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                            <DialogHeader>
                                <DialogTitle>Automatic Question Replacements</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-6 mt-4">
                                {report.repair_summary.replacements.map((rep: any, i: number) => (
                                    <div key={i} className="border rounded-md p-4 space-y-3 relative">
                                        <div className="font-semibold text-lg border-b pb-2">Question {rep.question_number}</div>
                                        <div className="bg-red-50 p-3 rounded text-red-900 border border-red-100">
                                            <div className="text-xs font-bold uppercase mb-1">Issue: {rep.reason}</div>
                                            <div className="text-sm line-through opacity-75">{rep.old_text}</div>
                                        </div>
                                        <div className="bg-green-50 p-3 rounded text-green-900 border border-green-100">
                                            <div className="text-xs font-bold uppercase mb-1">Replacement</div>
                                            <div className="text-sm font-medium">{rep.new_text}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </DialogContent>
                    </Dialog>
                </div>
            )}
            
            {report.repair_summary?.not_repaired?.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 p-3 rounded">
                    <strong>{report.repair_summary.not_repaired.length} issues could not be repaired</strong> because no suitable replacement was found in the question bank.
                    <ul className="list-disc ml-5 mt-1 opacity-80">
                        {report.repair_summary.not_repaired.map((nr: any, i: number) => (
                            <li key={i}>Question {nr.question_number}: {nr.reason}</li>
                        ))}
                    </ul>
                </div>
            )}

            {report.metrics && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t">
                    <div className="bg-muted/20 p-2 rounded text-center">
                        <div className="text-xs text-muted-foreground">Duplication</div>
                        <div className="font-semibold">{report.metrics.duplication_score}/100</div>
                    </div>
                    <div className="bg-muted/20 p-2 rounded text-center">
                        <div className="text-xs text-muted-foreground">Difficulty</div>
                        <div className="font-semibold">{report.metrics.difficulty_balance_score}/100</div>
                    </div>
                    <div className="bg-muted/20 p-2 rounded text-center">
                        <div className="text-xs text-muted-foreground">Topic Coverage</div>
                        <div className="font-semibold">{report.metrics.topic_coverage_score}/100</div>
                    </div>
                    <div className="bg-muted/20 p-2 rounded text-center">
                        <div className="text-xs text-muted-foreground">Clarity</div>
                        <div className="font-semibold">{report.metrics.clarity_score}/100</div>
                    </div>
                </div>
            )}
          </CardContent>
        </Card>
      )}
      
      {isDraft && paper.quality_report_stale && (
        <div className="text-sm text-yellow-600 bg-yellow-50 p-3 rounded border border-yellow-200">
          The paper has been modified. Please re-run the AI Quality Check before approval.
        </div>
      )}

      <div className="space-y-8">
        {Object.entries(sections).map(([sectionName, items]) => (
          <div key={sectionName} className="space-y-4">
            <h2 className="text-2xl font-bold border-b pb-2">{sectionName}</h2>
            
            {items.map((item: any, idx: number) => (
              <Card key={item.id} className={`relative group ${report?.problematic_question_numbers?.includes(idx + 1) ? 'ring-2 ring-yellow-400' : ''}`}>
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-l-md" />
                <CardHeader className="py-3 px-6 flex flex-row items-start justify-between bg-muted/20">
                  <span className="font-semibold text-lg">Q{idx + 1}.</span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium text-muted-foreground border px-2 py-1 rounded bg-background">
                      {item.marks_override || item.marks_snapshot} Marks
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="py-4 px-6 space-y-4">
                  <p className="font-medium text-lg whitespace-pre-wrap">{item.question_text_snapshot}</p>
                  
                  {item.content_snapshot.options && (
                    <div className="space-y-2 pl-4">
                      {item.content_snapshot.options.map((opt: any) => (
                        <div key={opt.id} className="flex gap-2">
                          <span className="font-medium text-muted-foreground w-6">{opt.id}.</span>
                          <span>{opt.text}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="mt-4 pt-4 border-t border-dashed text-sm text-muted-foreground bg-muted/10 p-3 rounded">
                    <span className="font-semibold text-foreground block mb-1">Answer Key Reference:</span>
                    {item.content_snapshot.options ? (
                      <span>Correct Option: <strong className="text-green-600">{item.content_snapshot.correct_answer}</strong></span>
                    ) : (
                      <span>{item.content_snapshot.correct_answer}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

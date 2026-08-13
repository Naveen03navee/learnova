"use client";

import { useWorkspaceStore } from "@/store/workspaceStore";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { AlertCircle, Loader2, Activity, Zap, ShieldCheck } from "lucide-react";

export default function InsightsPage() {
  const { examId, subjectId } = useWorkspaceStore();

  const { data: metrics, isLoading } = useQuery({
    queryKey: ["metrics", examId, subjectId],
    queryFn: () => {
      const params = new URLSearchParams();
      if (examId) params.append("exam_id", examId);
      if (subjectId) params.append("subject_id", subjectId);
      return api.get(`/api/v1/metrics?${params.toString()}`).then(res => res.data);
    },
    enabled: !!examId && !!subjectId,
  });

  if (!examId || !subjectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)] text-muted-foreground space-y-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground/50" />
        <h2 className="text-xl font-medium">No Context Selected</h2>
        <p>Please select an Exam and Subject from the sidebar to view insights.</p>
      </div>
    );
  }

  const genTotal = metrics?.generation?.requests_total || 0;
  const genSuccess = metrics?.generation?.success_total || 0;
  const genFailed = metrics?.generation?.failed_total || 0;
  const genSuccessRate = genTotal > 0 ? Math.round((genSuccess / genTotal) * 100) : 0;

  const qbTotal = metrics?.question_bank?.generated_total || 0;
  const qbApproved = metrics?.question_bank?.approved_total || 0;
  const qbRejected = metrics?.question_bank?.rejected_total || 0;
  const qbApprovalRate = metrics?.question_bank?.approval_rate ? Math.round(metrics.question_bank.approval_rate * 100) : 0;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Insights</h1>
        <p className="text-muted-foreground mt-2">Performance and quality analytics for your current workspace.</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Generation Performance */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Zap className="h-5 w-5 text-amber-500" />
                <span>Generation Performance</span>
              </CardTitle>
              <CardDescription>Success vs. Failure rates of AI tasks</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex justify-between items-end">
                <div>
                  <div className="text-4xl font-bold">{genTotal}</div>
                  <p className="text-sm text-muted-foreground font-medium">Total Generation Runs</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-emerald-600">{genSuccessRate}%</div>
                  <p className="text-sm text-muted-foreground font-medium">Success Rate</p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-emerald-600">Completed ({genSuccess})</span>
                  <span className="font-medium text-rose-500">Failed ({genFailed})</span>
                </div>
                <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex">
                  <div 
                    className="h-full bg-emerald-500 transition-all duration-1000" 
                    style={{ width: `${genTotal > 0 ? (genSuccess/genTotal)*100 : 0}%` }}
                  />
                  <div 
                    className="h-full bg-rose-500 transition-all duration-1000" 
                    style={{ width: `${genTotal > 0 ? (genFailed/genTotal)*100 : 0}%` }}
                  />
                </div>
              </div>

              <div className="pt-4 grid grid-cols-3 gap-4 text-center">
                <div className="bg-slate-50 p-3 rounded-lg">
                  <div className="text-lg font-semibold">{metrics?.generation?.llm_call_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">LLM Calls</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg">
                  <div className="text-lg font-semibold">{metrics?.generation?.repair_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">Repairs</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg">
                  <div className="text-lg font-semibold">{metrics?.generation?.validation_failure_total || 0}</div>
                  <div className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">Invalid</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quality Control */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <ShieldCheck className="h-5 w-5 text-indigo-500" />
                <span>Quality Control</span>
              </CardTitle>
              <CardDescription>Approval rates for generated questions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex justify-between items-end">
                <div>
                  <div className="text-4xl font-bold">{qbTotal}</div>
                  <p className="text-sm text-muted-foreground font-medium">Total Generated Questions</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-indigo-600">{qbApprovalRate}%</div>
                  <p className="text-sm text-muted-foreground font-medium">Approval Rate</p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-indigo-600">Approved ({qbApproved})</span>
                  <span className="font-medium text-rose-500">Rejected ({qbRejected})</span>
                </div>
                <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex">
                  <div 
                    className="h-full bg-indigo-500 transition-all duration-1000" 
                    style={{ width: `${(qbApproved + qbRejected) > 0 ? (qbApproved/(qbApproved + qbRejected))*100 : 0}%` }}
                  />
                  <div 
                    className="h-full bg-rose-500 transition-all duration-1000" 
                    style={{ width: `${(qbApproved + qbRejected) > 0 ? (qbRejected/(qbApproved + qbRejected))*100 : 0}%` }}
                  />
                </div>
              </div>

              <div className="pt-4 grid grid-cols-2 gap-4 text-center">
                <div className="bg-slate-50 p-3 rounded-lg border border-indigo-100">
                  <div className="text-xl font-semibold text-indigo-700">{metrics?.question_bank?.pending_total || 0}</div>
                  <div className="text-[10px] uppercase font-semibold text-indigo-400 tracking-wider">Pending Review</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-emerald-100">
                  <div className="text-xl font-semibold text-emerald-700">{metrics?.papers?.created_total || 0}</div>
                  <div className="text-[10px] uppercase font-semibold text-emerald-500 tracking-wider">Papers Created</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

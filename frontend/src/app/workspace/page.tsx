"use client";

import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { createClient } from "@/lib/supabase";
import { 
  FileText, Database, FileSignature, AlertCircle, 
  CheckCircle2, Clock, CheckSquare, Loader2
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { parseUtc } from "@/lib/date";

export default function WorkspaceDashboard() {
  const { examId, subjectId } = useWorkspaceStore();
  const [userName, setUserName] = useState("");

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) {
        setUserName(user.user_metadata?.full_name?.split(' ')[0] || user.email?.split('@')[0] || "");
      }
    });
  }, []);

  const { data: metrics, isLoading: loadingMetrics } = useQuery({
    queryKey: ["metrics", examId, subjectId],
    queryFn: () => {
      const params = new URLSearchParams();
      if (examId) params.append("exam_id", examId);
      if (subjectId) params.append("subject_id", subjectId);
      return api.get(`/api/v1/metrics?${params.toString()}`).then(res => res.data);
    },
    enabled: !!examId && !!subjectId,
  });

  const { data: activities = [], isLoading: loadingActivity } = useQuery({
    queryKey: ["activity", examId, subjectId],
    queryFn: () => {
      const params = new URLSearchParams();
      if (examId) params.append("exam_id", examId);
      if (subjectId) params.append("subject_id", subjectId);
      params.append("limit", "5");
      return api.get(`/api/v1/metrics/activity?${params.toString()}`).then(res => res.data);
    },
    enabled: !!examId && !!subjectId,
  });

  const stats = [
    { label: "Generations Run", value: metrics?.generation?.requests_total || "0", icon: Database, href: "/workspace/history" },
    { label: "Pending Review", value: metrics?.question_bank?.pending_total || "0", icon: FileSignature, href: "/workspace/review" },
    { label: "Approved Questions", value: metrics?.question_bank?.approved_total || "0", icon: CheckCircle2, href: "/workspace/questions" },
    { label: "Assembled Papers", value: metrics?.papers?.created_total || "0", icon: FileText, href: "/workspace/papers" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-violet-600 p-8 text-white shadow-lg">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
            Welcome back{userName ? `, ${userName}` : ''}
          </h1>
          <p className="text-indigo-100 max-w-xl text-lg">
            Here's what's happening in your Learnova workspace today. Select an exam and subject to start building your question bank.
          </p>
        </div>
        
        {/* Decorative background circles */}
        <div className="absolute -right-10 -top-24 h-64 w-64 rounded-full bg-white/10 blur-3xl"></div>
        <div className="absolute right-32 -bottom-24 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl"></div>
      </div>

      {(!examId || !subjectId) ? (
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-3 text-amber-800">
              <AlertCircle className="h-5 w-5" />
              <p className="font-medium">No context selected</p>
            </div>
            <p className="mt-2 text-sm text-amber-700">
              Please select both an Exam and Subject from the header to view metrics and activity.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {stats.map((stat, i) => (
              <Card key={i} className="hover:shadow-md transition-all hover:border-primary/50 group">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {stat.label}
                  </CardTitle>
                  <stat.icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {loadingMetrics ? <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /> : stat.value}
                  </div>
                  <Link href={stat.href} className="text-xs text-primary hover:underline mt-2 inline-block">
                    View all &rarr;
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>Common tasks for your workspace</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Link href="/workspace/knowledge" className={cn(buttonVariants({ variant: "outline" }), "h-auto py-4 flex flex-col items-center justify-center space-y-2 bg-gradient-to-b from-white to-slate-50 hover:to-slate-100")}>
                  <Database className="h-6 w-6 text-violet-500 mb-1" />
                  <span className="font-semibold text-slate-700">Upload Knowledge</span>
                </Link>
                <Link href="/workspace/patterns" className={cn(buttonVariants({ variant: "outline" }), "h-auto py-4 flex flex-col items-center justify-center space-y-2 bg-gradient-to-b from-white to-slate-50 hover:to-slate-100")}>
                  <FileSignature className="h-6 w-6 text-indigo-500 mb-1" />
                  <span className="font-semibold text-slate-700">Upload Pattern</span>
                </Link>
                <Link href="/workspace/generate" className={cn(buttonVariants({ variant: "outline" }), "h-auto py-4 flex flex-col items-center justify-center space-y-2 bg-gradient-to-b from-white to-slate-50 hover:to-slate-100")}>
                  <FileText className="h-6 w-6 text-amber-500 mb-1" />
                  <span className="font-semibold text-slate-700">Generate Questions</span>
                </Link>
                <Link href="/workspace/papers" className={cn(buttonVariants({ variant: "outline" }), "h-auto py-4 flex flex-col items-center justify-center space-y-2 bg-gradient-to-b from-white to-slate-50 hover:to-slate-100")}>
                  <CheckSquare className="h-6 w-6 text-emerald-500 mb-1" />
                  <span className="font-semibold text-slate-700">Assemble Paper</span>
                </Link>
              </CardContent>
            </Card>

            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Your latest actions in this context</CardDescription>
              </CardHeader>
              <CardContent>
                {loadingActivity ? (
                  <div className="flex justify-center py-10">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : activities.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
                    <div className="rounded-full bg-slate-100 p-3">
                      <Clock className="h-6 w-6 text-slate-400" />
                    </div>
                    <h3 className="font-semibold text-slate-700">No recent activity</h3>
                    <p className="text-sm text-slate-500 max-w-xs">
                      Your actions like generating questions or assembling papers will appear here.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {activities.map((activity: any) => (
                      <div key={activity.id} className="flex items-start space-x-3">
                        <div className="rounded-full bg-slate-100 p-2 mt-0.5">
                          {activity.type === 'generation' ? (
                            <Database className="h-4 w-4 text-violet-500" />
                          ) : (
                            <CheckSquare className="h-4 w-4 text-emerald-500" />
                          )}
                        </div>
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium leading-none">{activity.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatDistanceToNow(parseUtc(activity.created_at), { addSuffix: true })}
                            <span className="mx-2">•</span>
                            <span className="uppercase text-[10px] tracking-wider font-semibold">
                              {activity.status}
                            </span>
                          </p>
                        </div>
                      </div>
                    ))}
                    <div className="pt-2">
                      <Link href="/workspace/history" className="text-sm text-primary hover:underline">
                        View full history &rarr;
                      </Link>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

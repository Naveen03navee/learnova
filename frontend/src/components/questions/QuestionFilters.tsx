"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

interface QuestionFiltersProps {
  examId: string;
  setExamId: (v: string) => void;
  subjectId: string;
  setSubjectId: (v: string) => void;
}

export function QuestionFilters({ examId, setExamId, subjectId, setSubjectId }: QuestionFiltersProps) {
  // Fetch Exams
  const { data: exams = [] } = useQuery({
    queryKey: ["exams"],
    queryFn: () => api.get("/api/v1/exams").then(res => res.data),
  });

  // Fetch Subjects for selected Exam
  const { data: subjects = [] } = useQuery({
    queryKey: ["subjects", examId],
    queryFn: () => api.get(`/api/v1/subjects?exam_id=${examId}`).then(res => res.data),
    enabled: !!examId,
  });

  return (
    <div className="flex gap-4 p-4 border rounded-md bg-card">
      <div className="flex-1 space-y-1">
        <Label>Exam</Label>
        <Select value={examId} onValueChange={(val) => { if(val !== null) { setExamId(val); setSubjectId(""); } }}>
          <SelectTrigger><SelectValue placeholder="All Exams" /></SelectTrigger>
          <SelectContent>
             <SelectItem value="">All Exams</SelectItem>
            {exams.map((e: any) => <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      
      <div className="flex-1 space-y-1">
        <Label>Subject</Label>
        <Select value={subjectId} onValueChange={(val) => { if(val !== null) setSubjectId(val); }} disabled={!examId}>
          <SelectTrigger><SelectValue placeholder="All Subjects" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Subjects</SelectItem>
            {subjects.map((s: any) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

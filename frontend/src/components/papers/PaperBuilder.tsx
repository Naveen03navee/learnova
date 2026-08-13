"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { useNotificationStore } from "@/store/notificationStore";

import { useWorkspaceStore } from "@/store/workspaceStore";

interface SectionConfig {
  id: string;
  name: string;
  question_type: string;
  difficulty: string;
  count: number;
  marks_per_question: number;
}

export function PaperBuilder() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);
  const { examId: globalExamId, subjectId: globalSubjectId } = useWorkspaceStore();
  
  const [title, setTitle] = useState("");
  const [examId, setExamId] = useState(globalExamId || "");
  const [subjectId, setSubjectId] = useState(globalSubjectId || "");
  
  const [sections, setSections] = useState<SectionConfig[]>([
    { id: "1", name: "Section A: Multiple Choice", question_type: "MCQ", difficulty: "Easy", count: 10, marks_per_question: 1 }
  ]);

  const { data: exams = [] } = useQuery({
    queryKey: ["exams"],
    queryFn: () => api.get("/api/v1/exams").then(res => res.data),
  });

  const { data: subjects = [] } = useQuery({
    queryKey: ["subjects", examId],
    queryFn: () => api.get(`/api/v1/subjects?exam_id=${examId}`).then(res => res.data),
    enabled: !!examId,
  });

  const buildMutation = useMutation({
    mutationFn: (data: any) => api.post("/api/v1/papers/build", data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      notify.success("Paper Draft Created", "Your new paper draft has been successfully created!");
      router.push(`/workspace/papers/${res.data.id}`);
    },
    onError: (error: any) => {
      notify.error("Build failed", error.response?.data?.detail || "Failed to build paper.");
    }
  });

  const addSection = () => {
    setSections([...sections, {
      id: Math.random().toString(),
      name: `Section ${String.fromCharCode(65 + sections.length)}`,
      question_type: "SAQ",
      difficulty: "Medium",
      count: 5,
      marks_per_question: 2
    }]);
  };

  const removeSection = (id: string) => {
    setSections(sections.filter(s => s.id !== id));
  };

  const updateSection = (id: string, field: keyof SectionConfig, value: any) => {
    setSections(sections.map(s => s.id === id ? { ...s, [field]: value } : s));
  };

  const handleBuild = () => {
    if (!title || !examId || !subjectId) {
      notify.error("Validation Error", "Please fill in the title, exam, and subject.");
      return;
    }
    
    if (sections.length === 0) {
      notify.error("Validation Error", "Please add at least one section.");
      return;
    }

    buildMutation.mutate({
      title,
      exam_id: examId,
      subject_id: subjectId,
      sections: sections.map(({ id, ...rest }) => rest)
    });
  };

  return (
    <div className="flex flex-col h-full overflow-auto pb-10">
      <div className="space-y-6 max-w-4xl mx-auto w-full">
        <Card>
          <CardHeader>
            <CardTitle>Paper Configuration</CardTitle>
            <CardDescription>Set the scope and title for this question paper.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label>Paper Title</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Midterm Physics 2026" />
            </div>
            <div className="flex gap-4">
              <div className="flex-1 space-y-1">
                <Label>Exam</Label>
                <Select value={examId} onValueChange={(val) => { if(val) { setExamId(val); setSubjectId(""); } }}>
                  <SelectTrigger><SelectValue placeholder="Select Exam" /></SelectTrigger>
                  <SelectContent>
                    {exams.map((e: any) => <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1 space-y-1">
                <Label>Subject</Label>
                <Select value={subjectId} onValueChange={(val) => val && setSubjectId(val)} disabled={!examId}>
                  <SelectTrigger><SelectValue placeholder="Select Subject" /></SelectTrigger>
                  <SelectContent>
                    {subjects.map((s: any) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold">Blueprint Sections</h2>
          <Button variant="outline" size="sm" onClick={addSection}>
            <Plus className="w-4 h-4 mr-2" /> Add Section
          </Button>
        </div>

        <div className="space-y-4">
          {sections.map((section, index) => (
            <Card key={section.id}>
              <CardHeader className="py-3 flex flex-row items-center justify-between bg-muted/30">
                <Input 
                  value={section.name} 
                  onChange={(e) => updateSection(section.id, "name", e.target.value)}
                  className="font-semibold bg-transparent border-none shadow-none h-8 max-w-sm px-0 focus-visible:ring-0" 
                />
                <Button variant="ghost" size="icon" className="h-6 w-6 text-red-500" onClick={() => removeSection(section.id)}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="py-4 flex gap-4">
                <div className="flex-1 space-y-1">
                  <Label className="text-xs">Type</Label>
                  <Select value={section.question_type} onValueChange={(val) => val && updateSection(section.id, "question_type", val)}>
                    <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MCQ">Multiple Choice</SelectItem>
                      <SelectItem value="SAQ">Short Answer</SelectItem>
                      <SelectItem value="LAQ">Long Answer</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 space-y-1">
                  <Label className="text-xs">Difficulty</Label>
                  <Select value={section.difficulty} onValueChange={(val) => val && updateSection(section.id, "difficulty", val)}>
                    <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Easy">Easy</SelectItem>
                      <SelectItem value="Medium">Medium</SelectItem>
                      <SelectItem value="Hard">Hard</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="w-24 space-y-1">
                  <Label className="text-xs">Count</Label>
                  <Input type="number" min={1} className="h-8" value={section.count} onChange={(e) => updateSection(section.id, "count", parseInt(e.target.value) || 1)} />
                </div>
                <div className="w-24 space-y-1">
                  <Label className="text-xs">Marks/Q</Label>
                  <Input type="number" min={1} className="h-8" value={section.marks_per_question} onChange={(e) => updateSection(section.id, "marks_per_question", parseInt(e.target.value) || 1)} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Button 
          className="w-full" 
          size="lg" 
          onClick={handleBuild}
          disabled={buildMutation.isPending || sections.length === 0}
        >
          {buildMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Building Paper...</> : "Build Question Paper"}
        </Button>
      </div>
    </div>
  );
}

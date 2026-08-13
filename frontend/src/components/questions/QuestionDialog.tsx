"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useNotificationStore } from "@/store/notificationStore";

interface QuestionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  examId: string;
  subjectId: string;
  question?: any; // If provided, it's edit mode
}

export function QuestionDialog({ isOpen, onOpenChange, examId, subjectId, question }: QuestionDialogProps) {
  const queryClient = useQueryClient();
  const notify = useNotificationStore(s => s.notify);
  
  const isEdit = !!question;

  // Fetch human-readable context
  const { data: exams = [] } = useQuery({
    queryKey: ["exams"],
    queryFn: () => api.get("/api/v1/exams").then(res => res.data),
    enabled: isOpen
  });
  
  const { data: subjects = [] } = useQuery({
    queryKey: ["subjects", examId],
    queryFn: () => api.get(`/api/v1/subjects?exam_id=${examId}`).then(res => res.data),
    enabled: isOpen && !!examId
  });

  const examName = exams.find((e: any) => e.id === examId)?.name || "Unknown Exam";
  const subjectName = subjects.find((s: any) => s.id === subjectId)?.name || "Unknown Subject";

  const [questionType, setQuestionType] = useState("MCQ");
  const [difficulty, setDifficulty] = useState("medium");
  const [marks, setMarks] = useState(1);
  const [questionText, setQuestionText] = useState("");
  
  // MCQ specific
  const [options, setOptions] = useState([
    { id: "A", text: "" },
    { id: "B", text: "" },
    { id: "C", text: "" },
    { id: "D", text: "" }
  ]);
  const [correctAnswer, setCorrectAnswer] = useState("A");
  
  // Explanation
  const [explanation, setExplanation] = useState("");

  useEffect(() => {
    if (isOpen) {
      if (isEdit && question) {
        setQuestionType(question.question_type);
        setDifficulty(question.difficulty);
        setMarks(question.marks);
        setQuestionText(question.question_text);
        setExplanation(question.content?.explanation || "");
        
        if (question.question_type === "MCQ") {
          setOptions(question.content?.options || [
            { id: "A", text: "" }, { id: "B", text: "" }, { id: "C", text: "" }, { id: "D", text: "" }
          ]);
          setCorrectAnswer(question.content?.correct_answer || "A");
        } else {
          setCorrectAnswer(question.content?.correct_answer || "");
        }
      } else {
        // Reset form
        setQuestionType("MCQ");
        setDifficulty("medium");
        setMarks(1);
        setQuestionText("");
        setOptions([{ id: "A", text: "" }, { id: "B", text: "" }, { id: "C", text: "" }, { id: "D", text: "" }]);
        setCorrectAnswer("A");
        setExplanation("");
      }
    }
  }, [isOpen, isEdit, question]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        exam_id: examId,
        subject_id: subjectId,
        question_type: questionType,
        difficulty,
        marks,
        question_text: questionText,
        content: {
          explanation,
          ...(questionType === "MCQ" ? { options, correct_answer: correctAnswer } : { correct_answer: correctAnswer })
        }
      };

      if (isEdit) {
        return api.put(`/api/v1/questions/${question.id}`, payload);
      } else {
        return api.post(`/api/v1/questions`, payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      notify.success("Success", isEdit ? "Question updated successfully" : "Question created successfully");
      onOpenChange(false);
    },
    onError: (error: any) => {
      notify.error("Action failed", error.response?.data?.detail || "An error occurred");
    }
  });

  const handleSave = () => {
    if (!questionText.trim()) {
      notify.error("Validation", "Question text cannot be empty");
      return;
    }
    saveMutation.mutate();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="w-[calc(100%-2rem)] sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Question" : "Create Question"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update this question in the bank." : "Add a new question directly to the bank."}
            <div className="mt-2 font-medium text-foreground bg-muted/50 p-2 rounded-md inline-block">
              Context: {examName} / {subjectName}
            </div>
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={questionType} onValueChange={(v) => { if (v) setQuestionType(v); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="MCQ">MCQ</SelectItem>
                  <SelectItem value="Descriptive">Descriptive</SelectItem>
                  <SelectItem value="True/False">True/False</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Difficulty</Label>
              <Select value={difficulty} onValueChange={(v) => { if (v) setDifficulty(v); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="easy">Easy</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="hard">Hard</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Marks</Label>
              <Input type="number" min={1} max={100} value={marks} onChange={(e: any) => setMarks(parseInt(e.target.value) || 1)} />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>Question Text</Label>
            <Textarea 
              className="min-h-[100px]" 
              value={questionText}
              onChange={(e: any) => setQuestionText(e.target.value)}
              placeholder="Enter the question here..."
            />
          </div>

          {questionType === "MCQ" ? (
            <div className="space-y-4 border p-4 rounded-md bg-muted/20">
              <Label>Options & Correct Answer</Label>
              {options.map((opt, index) => (
                <div key={opt.id} className="flex items-center gap-3">
                  <span className="font-semibold w-6">{opt.id}.</span>
                  <Input 
                    value={opt.text} 
                    onChange={(e: any) => {
                      const newOpts = [...options];
                      newOpts[index].text = e.target.value;
                      setOptions(newOpts);
                    }}
                    placeholder={`Option ${opt.id}`}
                  />
                  <Button 
                    variant={correctAnswer === opt.id ? "default" : "outline"}
                    className={correctAnswer === opt.id ? "bg-green-600 hover:bg-green-700" : ""}
                    onClick={() => setCorrectAnswer(opt.id)}
                  >
                    {correctAnswer === opt.id ? "Correct" : "Mark"}
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Correct Answer (or Rubric)</Label>
              <Textarea 
                value={correctAnswer}
                onChange={(e: any) => setCorrectAnswer(e.target.value)}
                placeholder="Expected answer..."
              />
            </div>
          )}

          <div className="space-y-2">
            <Label>Explanation / Solution</Label>
            <Textarea 
              value={explanation}
              onChange={(e: any) => setExplanation(e.target.value)}
              placeholder="Step-by-step solution..."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving..." : "Save Question"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { GenerationProgress } from "./GenerationProgress";
import { GenerationResults } from "./GenerationResults";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { AlertCircle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

export function GenerationForm() {
  const { examId, subjectId, activeSessionId, setActiveSessionId } = useWorkspaceStore();
  const router = useRouter();
  
  const [topic, setTopic] = useState("");
  const [questionType, setQuestionType] = useState("MCQ");
  const [difficulty, setDifficulty] = useState("medium");
  const [marks, setMarks] = useState<number | "">(1);
  const [count, setCount] = useState<number | "">(5);
  const [patternId, setPatternId] = useState<string>("none");

  const [isGenerating, setIsGenerating] = useState(false);
  const [hasHydrated, setHasHydrated] = useState(false);

  // Handle Zustand hydration
  useEffect(() => {
    setHasHydrated(true);
    if (activeSessionId) setIsGenerating(true);
  }, [activeSessionId]);

  // Fetch ACTIVE Patterns for current context
  const { data: patterns = [] } = useQuery({
    queryKey: ["patterns", examId, subjectId],
    queryFn: () => api.get(`/api/v1/patterns?exam_id=${examId}&subject_id=${subjectId}&status=ACTIVE`).then(res => res.data),
    enabled: !!examId && !!subjectId,
  });

  const selectedPattern = patterns.find((p: any) => p.id === patternId);
  const patternDisplayText = selectedPattern 
    ? (selectedPattern.year ? `${selectedPattern.year} Pattern (${selectedPattern.file_name})` : selectedPattern.file_name || "Pattern")
    : "No pattern selected";

  const handleGenerate = async () => {
    if (!examId || !subjectId || !count || !marks) return;

    setIsGenerating(true);
    setActiveSessionId(null);

    try {
      const response = await api.post("/api/v1/generation/start", {
        exam_id: examId,
        subject_id: subjectId,
        pattern_id: patternId === "none" ? null : patternId,
        topic,
        question_type: questionType,
        difficulty,
        marks,
        count
      });
      
      setActiveSessionId(response.data.id);
    } catch (error) {
      console.error("Failed to start generation", error);
      setIsGenerating(false);
    }
  };

  const handleGenerationComplete = useCallback(() => {
    setIsGenerating(false);
  }, []);

  const handleInitialTerminalState = useCallback(() => {
    setActiveSessionId(null);
    setIsGenerating(false);
  }, [setActiveSessionId]);

  if (!hasHydrated) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (activeSessionId) {
    return (
      <div className="space-y-6">
        <GenerationProgress 
          sessionId={activeSessionId} 
          onComplete={handleGenerationComplete} 
          onInitialTerminalState={handleInitialTerminalState}
        />
        {!isGenerating && (
           <div className="flex flex-col gap-4">
              <Button 
                onClick={() => {
                  const sessionId = activeSessionId;
                  setActiveSessionId(null);
                  router.push(`/workspace/review?session_id=${sessionId}`);
                }}
              >
                Review Generated Questions
              </Button>
              <Button variant="outline" onClick={() => setActiveSessionId(null)}>
                Generate More Questions
              </Button>
           </div>
        )}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generation Parameters</CardTitle>
        <CardDescription>Configure the constraints for the AI generation.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        
        {!examId || !subjectId ? (
          <div className="flex items-center gap-2 p-4 text-amber-800 bg-amber-50 rounded-md">
            <AlertCircle className="w-5 h-5" />
            <p>Please select an Exam and Subject from the header to begin.</p>
          </div>
        ) : null}

        <div className="space-y-2">
          <Label>Topic Focus</Label>
          <Input 
            placeholder="e.g. Thermodynamics, Newton's Laws" 
            value={topic} 
            onChange={(e) => setTopic(e.target.value)}
            disabled={isGenerating}
          />
        </div>

        <div className="space-y-2">
          <Label>Approved Exam Pattern (Optional)</Label>
          <Select value={patternId} onValueChange={(val) => setPatternId(val || "none")} disabled={isGenerating}>
            <SelectTrigger>
              <SelectValue placeholder="No pattern selected">
                {patternId !== "none" ? patternDisplayText : "No pattern selected"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No pattern selected</SelectItem>
              {patterns.map((p: any) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.year ? `${p.year} Pattern (${p.file_name})` : p.file_name || "Pattern"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label>Question Type</Label>
            <Select value={questionType} onValueChange={(val) => val && setQuestionType(val)} disabled={isGenerating}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="MCQ">MCQ</SelectItem>
                <SelectItem value="SAQ">Short Answer</SelectItem>
                <SelectItem value="LAQ">Long Answer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-2">
            <Label>Difficulty</Label>
            <Select value={difficulty} onValueChange={(val) => val && setDifficulty(val)} disabled={isGenerating}>
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
            <Input type="number" min={1} value={marks} onChange={(e) => setMarks(e.target.value === "" ? "" : parseInt(e.target.value))} disabled={isGenerating} />
          </div>

          <div className="space-y-2">
            <Label>Count</Label>
            <Input type="number" min={1} max={50} value={count} onChange={(e) => setCount(e.target.value === "" ? "" : parseInt(e.target.value))} disabled={isGenerating} />
          </div>
        </div>

        <Button 
          className="w-full mt-4" 
          onClick={handleGenerate} 
          disabled={!examId || !subjectId || !count || !marks || isGenerating}
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            "Generate Questions"
          )}
        </Button>

      </CardContent>
    </Card>
  );
}

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { QuestionBank } from "@/components/questions/QuestionBank";
import { GeneratedReview } from "@/components/questions/GeneratedReview";

export default function QuestionsPage() {
  return (
    <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto h-[calc(100vh-100px)]">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Questions</h1>
        <p className="text-muted-foreground mt-2">
          Manage your permanent Question Bank and review AI-generated questions.
        </p>
      </div>

      <Tabs defaultValue="bank" className="flex-1 flex flex-col min-h-0">
        <TabsList className="w-full max-w-sm grid grid-cols-2">
          <TabsTrigger value="bank">Question Bank</TabsTrigger>
          <TabsTrigger value="review">Review Generated</TabsTrigger>
        </TabsList>
        <div className="flex-1 overflow-auto mt-4 min-h-0 relative">
          <TabsContent value="bank" className="h-full m-0 data-[state=active]:flex flex-col">
            <QuestionBank />
          </TabsContent>
          <TabsContent value="review" className="h-full m-0 data-[state=active]:flex flex-col">
            <GeneratedReview />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

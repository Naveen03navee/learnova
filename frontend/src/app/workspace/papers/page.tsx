import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PapersList } from "@/components/papers/PapersList";
import { PaperBuilder } from "@/components/papers/PaperBuilder";

export default function PapersPage() {
  return (
    <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto h-[calc(100vh-100px)]">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Question Papers</h1>
        <p className="text-muted-foreground mt-2">
          Build structured exam papers from the trusted Question Bank.
        </p>
      </div>

      <Tabs defaultValue="list" className="flex-1 flex flex-col min-h-0">
        <TabsList className="w-full max-w-sm grid grid-cols-2">
          <TabsTrigger value="list">My Papers</TabsTrigger>
          <TabsTrigger value="build">Build New</TabsTrigger>
        </TabsList>
        <div className="flex-1 overflow-auto mt-4 min-h-0 relative">
          <TabsContent value="list" className="h-full m-0 data-[state=active]:flex flex-col">
            <PapersList />
          </TabsContent>
          <TabsContent value="build" className="h-full m-0 data-[state=active]:flex flex-col">
            <PaperBuilder />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

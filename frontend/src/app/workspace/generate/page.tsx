import { GenerationForm } from "@/components/generation/GenerationForm";

export default function GenerationPage() {
  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Question Generation</h1>
        <p className="text-muted-foreground mt-2">
          Generate questions strictly from your uploaded knowledge base.
        </p>
      </div>
      
      <GenerationForm />
    </div>
  );
}

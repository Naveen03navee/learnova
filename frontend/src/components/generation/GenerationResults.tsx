export function GenerationResults({ sessionId }: { sessionId: string }) {
  // To be implemented in Phase 8 (Question Bank review)
  return (
    <div className="p-4 border rounded-md bg-muted">
      <h3 className="font-semibold">Generation Completed</h3>
      <p className="text-sm text-muted-foreground mt-2">
        Questions have been staged for review. In Phase 8, you will be able to review, edit, and approve them into the Question Bank here.
      </p>
    </div>
  );
}

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface WorkspaceState {
  examId: string | null;
  subjectId: string | null;
  setExamId: (id: string | null) => void;
  setSubjectId: (id: string | null) => void;
  setContext: (examId: string, subjectId: string) => void;
  clearContext: () => void;
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      examId: null,
      subjectId: null,
      setExamId: (id) => set((state) => {
        if (state.examId === id) return {};
        // Aggressively clear downstream state when exam changes
        return { examId: id, subjectId: null, activeSessionId: null };
      }),
      setSubjectId: (id) => set({ subjectId: id, activeSessionId: null }),
      setContext: (examId: string, subjectId: string) => set({ examId, subjectId, activeSessionId: null }),
      clearContext: () => set({ examId: null, subjectId: null, activeSessionId: null }),
      activeSessionId: null,
      setActiveSessionId: (id) => set({ activeSessionId: id }),
    }),
    {
      name: 'learnova-workspace-storage',
      partialize: (state) => ({ examId: state.examId, subjectId: state.subjectId }),
    }
  )
);

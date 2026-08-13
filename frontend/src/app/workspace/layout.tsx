'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ToastOverlay } from "@/components/notifications/ToastOverlay";
import { Loader2 } from 'lucide-react';
import Image from 'next/image';

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { examId, subjectId } = useWorkspaceStore();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const supabase = createClient();

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.replace('/login');
      } else {
        setChecking(false);
      }
    });

    // Only redirect on explicit sign-out — do NOT redirect on INITIAL_SESSION
    // to avoid a race-condition redirect loop
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_OUT') {
        router.replace('/login');
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  if (checking) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-muted-foreground animate-in fade-in duration-500">
          <div className="animate-pulse flex items-center justify-center">
            <Image 
              src="/logo-light.png" 
              alt="Learnova" 
              width={160} 
              height={48} 
              className="dark:hidden object-contain h-[40px] w-auto animate-bounce" 
              priority
            />
            <Image 
              src="/logo-dark.png" 
              alt="Learnova" 
              width={160} 
              height={48} 
              className="hidden dark:block object-contain h-[40px] w-auto animate-bounce" 
              priority
            />
          </div>
          <span className="text-sm font-medium tracking-wide">Loading workspace...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background font-sans">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <div key={`${examId}-${subjectId}`} className="flex-1 overflow-y-auto bg-[#fafafa] dark:bg-background">
          {children}
        </div>
      </main>
      <ToastOverlay />
    </div>
  );
}

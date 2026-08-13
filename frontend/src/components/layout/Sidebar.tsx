"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { 
  LayoutDashboard, Database, FileSignature, Wand2, 
  CheckCircle2, LibraryBig, FileText, CheckSquare, 
  Archive, LineChart, History, Settings, Brain, LogOut
} from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase";
import Image from "next/image";

const NAV_GROUPS = [
  {
    title: "Context",
    items: [
      { href: "/workspace/setup", icon: Settings, label: "Setup Context" },
      { href: "/workspace/knowledge", icon: Database, label: "Knowledge Base" },
      { href: "/workspace/patterns", icon: FileSignature, label: "Exam Patterns" },
    ]
  },
  {
    title: "Creation",
    items: [
      { href: "/workspace/generate", icon: Wand2, label: "Generate" },
      { href: "/workspace/review", icon: CheckCircle2, label: "Review" },
      { href: "/workspace/questions", icon: LibraryBig, label: "Question Bank" },
    ]
  },
  {
    title: "Assembly",
    items: [
      { href: "/workspace/papers", icon: FileText, label: "Question Papers" },
      { href: "/workspace/answers", icon: CheckSquare, label: "Answers" },
      { href: "/workspace/packages", icon: Archive, label: "Packages" },
    ]
  },
  {
    title: "System",
    items: [
      { href: "/workspace/insights", icon: LineChart, label: "AI Insights" },
      { href: "/workspace/history", icon: History, label: "History" },
      { href: "/workspace/settings", icon: Settings, label: "Settings" },
    ]
  }
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const isActive = (href: string) => {
    if (href === "/workspace") return pathname === href;
    return pathname.startsWith(href);
  };

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/login");
  };

  return (
    <aside className="w-56 border-r bg-sidebar flex flex-col hidden md:flex shrink-0 h-full">
      {/* Brand */}
      <div className="h-14 border-b flex items-center px-4 shrink-0 overflow-hidden">
        <Image 
          src="/logo-light.png" 
          alt="Learnova Logo" 
          width={150} 
          height={40} 
          className="dark:hidden object-contain h-[32px] w-auto" 
          priority
        />
        <Image 
          src="/logo-dark.png" 
          alt="Learnova Logo" 
          width={150} 
          height={40} 
          className="hidden dark:block object-contain h-[32px] w-auto" 
          priority
        />
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-3">
        {/* Dashboard */}
        <div>
          <Link
            href="/workspace"
            className={cn(
              "flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-150",
              isActive("/workspace")
                ? "bg-indigo-50 text-indigo-700 font-semibold"
                : "hover:bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            <LayoutDashboard size={15} className={isActive("/workspace") ? "text-indigo-600" : ""} />
            Dashboard
          </Link>
        </div>

        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <p className="pb-1 px-3 text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
              {group.title}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-150",
                      active
                        ? "bg-indigo-50 text-indigo-700 font-semibold"
                        : "hover:bg-muted text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Icon size={15} className={cn("shrink-0", active ? "text-indigo-600" : "")} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer — Sign Out */}
      <div className="border-t px-2 py-3">
        <button
          onClick={handleSignOut}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg text-muted-foreground hover:bg-red-50 hover:text-red-600 transition-all duration-150 group"
        >
          <LogOut size={15} className="group-hover:text-red-500 transition-colors" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}

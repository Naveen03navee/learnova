"use client";

import { usePathname } from "next/navigation";
import { GlobalContextSelector } from "@/components/workspace/GlobalContextSelector";
import { NotificationTray } from "./NotificationTray";
import { ProfileMenu } from "./ProfileMenu";
import { MobileNav } from "./MobileNav";

// Pages that don't need the context selector
const GLOBAL_ROUTES = [
  "/workspace/settings",
  "/workspace/history"
];

export function Header() {
  const pathname = usePathname();
  
  // Show context selector unless we are on a global route
  const showContext = !GLOBAL_ROUTES.some(route => pathname.startsWith(route));

  return (
    <header className="min-h-14 h-auto py-2 sm:py-0 sm:h-14 border-b flex items-center px-4 md:px-6 justify-between bg-card shrink-0 shadow-sm">
      <div className="flex flex-wrap items-center gap-3 flex-1">
        {/* Mobile-only hamburger — hidden on md+ where the sidebar is visible */}
        <MobileNav />
        {showContext && <GlobalContextSelector />}
      </div>
      
      <div className="flex items-center space-x-4 text-muted-foreground">
        <NotificationTray />
        <ProfileMenu />
      </div>
    </header>
  );
}


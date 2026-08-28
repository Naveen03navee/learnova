"use client";

import { useEffect, useState } from "react";
import { Settings, LogOut, UserCircle } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";

type UserInfo = { name: string; email: string; initials: string };

export function ProfileMenu() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      const name = user.user_metadata?.full_name ?? user.email ?? 'Teacher';
      const email = user.email ?? '';
      const initials = name
        .split(' ')
        .map((n: string) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2) || email[0]?.toUpperCase() || 'T';
      setUser({ name, email, initials });
    });
  }, []);

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 rounded-full hover:bg-muted transition-colors outline-none focus:ring-2 focus:ring-ring px-2 py-1">
        {user ? (
          <div className="h-7 w-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
            {user.initials}
          </div>
        ) : (
          <div className="h-7 w-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold shrink-0">T</div>
        )}
        {user && (
          <span className="hidden md:block text-sm font-medium max-w-[120px] truncate">
            {user.name}
          </span>
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-60">
        {/* User info — must be inside DropdownMenuGroup for DropdownMenuLabel to work */}
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <p className="font-semibold text-sm truncate">{user?.name ?? 'My Account'}</p>
            <p className="text-xs font-normal text-muted-foreground truncate mt-0.5">{user?.email}</p>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem onSelect={() => router.push("/workspace/profile")} className="gap-2">
            <UserCircle size={15} /> Profile
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => router.push("/workspace/settings")} className="gap-2">
            <Settings size={15} /> Settings
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem
            onSelect={handleLogout}
            className="text-destructive focus:text-destructive focus:bg-destructive/10 gap-2"
          >
            <LogOut size={15} /> Sign Out
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

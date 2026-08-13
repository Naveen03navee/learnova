"use client";

import { Bell, CheckCircle2, XCircle, Info, Loader2, Trash2, CheckCheck } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useNotificationStore, Notification } from "@/store/notificationStore";
import { formatDistanceToNow } from "date-fns";

const typeIcon = (type: Notification['type']) => ({
  success: <CheckCircle2 size={14} className="text-emerald-500 shrink-0 mt-0.5" />,
  error:   <XCircle      size={14} className="text-red-500 shrink-0 mt-0.5" />,
  info:    <Info         size={14} className="text-blue-500 shrink-0 mt-0.5" />,
  loading: <Loader2      size={14} className="text-indigo-500 shrink-0 mt-0.5 animate-spin" />,
}[type]);

export function NotificationTray() {
  const { notifications, markRead, markAllRead, dismiss, clear } = useNotificationStore();
  const unread = notifications.filter(n => !n.read).length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="relative flex items-center justify-center hover:text-foreground transition-colors h-8 w-8 rounded-full hover:bg-muted outline-none focus:ring-2 focus:ring-ring">
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-indigo-600 text-white text-[9px] font-bold flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-96 max-h-[480px] flex flex-col">
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm">
                Notifications {unread > 0 && <span className="text-indigo-600">({unread} new)</span>}
              </span>
              <div className="flex gap-1">
                {unread > 0 && (
                  <button
                    onClick={e => { e.stopPropagation(); markAllRead(); }}
                    className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
                    title="Mark all read"
                  >
                    <CheckCheck size={12} /> All read
                  </button>
                )}
                {notifications.length > 0 && (
                  <button
                    onClick={e => { e.stopPropagation(); clear(); }}
                    className="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1 ml-2"
                    title="Clear all"
                  >
                    <Trash2 size={12} /> Clear
                  </button>
                )}
              </div>
            </div>
          </DropdownMenuLabel>
        </DropdownMenuGroup>

        <DropdownMenuSeparator />

        <div className="overflow-y-auto flex-1">
          {notifications.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground flex flex-col items-center gap-2">
              <Bell size={28} className="text-muted-foreground/30" strokeWidth={1.5} />
              <p>No notifications yet</p>
              <p className="text-xs">Events like generation, uploads, and errors will appear here.</p>
            </div>
          ) : (
            <DropdownMenuGroup>
              {notifications.map(n => (
                <div
                  key={n.id}
                  onClick={() => markRead(n.id)}
                  className={`flex gap-2.5 px-3 py-2.5 cursor-pointer transition-colors hover:bg-muted/60 ${!n.read ? 'bg-indigo-50/50' : ''}`}
                >
                  {typeIcon(n.type)}
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm leading-snug ${!n.read ? 'font-semibold' : 'font-medium'}`}>{n.title}</p>
                    {n.message && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.message}</p>}
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {formatDistanceToNow(n.timestamp, { addSuffix: true })}
                    </p>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); dismiss(n.id); }}
                    className="text-muted-foreground hover:text-destructive transition-colors p-0.5 shrink-0 self-start"
                  >
                    ×
                  </button>
                </div>
              ))}
            </DropdownMenuGroup>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

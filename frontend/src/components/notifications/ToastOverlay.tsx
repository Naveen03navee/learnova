'use client';

import { useNotificationStore, Notification } from '@/store/notificationStore';
import { CheckCircle2, XCircle, Info, Loader2, X } from 'lucide-react';
import { useEffect, useState } from 'react';

function ToastItem({ notif, onDismiss }: { notif: Notification; onDismiss: () => void }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Small delay so CSS transition fires
    const t = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(t);
  }, []);

  const icon = {
    success: <CheckCircle2 size={18} className="text-emerald-500 shrink-0" />,
    error:   <XCircle    size={18} className="text-red-500 shrink-0" />,
    info:    <Info       size={18} className="text-blue-500 shrink-0" />,
    loading: <Loader2    size={18} className="text-indigo-500 shrink-0 animate-spin" />,
  }[notif.type];

  const border = {
    success: 'border-l-emerald-500',
    error:   'border-l-red-500',
    info:    'border-l-blue-500',
    loading: 'border-l-indigo-500',
  }[notif.type];

  return (
    <div
      className={`
        toast-item ${border}
        ${visible ? 'toast-item-visible' : 'toast-item-hidden'}
      `}
    >
      {icon}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 leading-tight">{notif.title}</p>
        {notif.message && (
          <p className="text-xs text-gray-500 mt-0.5 leading-snug line-clamp-2">{notif.message}</p>
        )}
      </div>
      <button
        onClick={onDismiss}
        className="text-gray-400 hover:text-gray-600 transition-colors p-0.5 rounded shrink-0"
      >
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastOverlay() {
  const { notifications, toasts, dismissToast } = useNotificationStore();

  const activeToasts = toasts
    .map(id => notifications.find(n => n.id === id))
    .filter(Boolean) as Notification[];

  if (activeToasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2.5 items-end pointer-events-none">
      {activeToasts.slice(0, 5).map(n => (
        <div key={n.id} className="pointer-events-auto">
          <ToastItem notif={n} onDismiss={() => dismissToast(n.id)} />
        </div>
      ))}
    </div>
  );
}

import { create } from 'zustand';

export type NotifType = 'success' | 'error' | 'info' | 'loading';

export interface Notification {
  id: string;
  type: NotifType;
  title: string;
  message?: string;
  timestamp: Date;
  read: boolean;
  /** If set, this notification auto-dismisses from the toast overlay after ms */
  autoDismissMs?: number;
}

interface NotificationStore {
  notifications: Notification[];
  /** Toast overlay queue (subset of notifications that show as popups) */
  toasts: string[]; // IDs of active toast popups
  push: (n: Omit<Notification, 'id' | 'timestamp' | 'read'>) => string;
  markRead: (id: string) => void;
  markAllRead: () => void;
  dismiss: (id: string) => void;
  clear: () => void;
  dismissToast: (id: string) => void;
  notify: {
    success: (title: string, message?: string) => void;
    error: (title: string, message?: string) => void;
    info: (title: string, message?: string) => void;
    loading: (title: string, message?: string) => void;
  };
}

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: [],
  toasts: [],

  push: (n) => {
    const id = `notif-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const notif: Notification = {
      ...n,
      id,
      timestamp: new Date(),
      read: false,
    };
    set(s => ({
      notifications: [notif, ...s.notifications].slice(0, 100), // cap at 100
      toasts: [...s.toasts, id],
    }));

    // Auto-dismiss toast popup
    const ms = n.autoDismissMs ?? (n.type === 'error' ? 6000 : 4000);
    setTimeout(() => get().dismissToast(id), ms);

    return id;
  },

  markRead: (id) =>
    set(s => ({
      notifications: s.notifications.map(n => n.id === id ? { ...n, read: true } : n),
    })),

  markAllRead: () =>
    set(s => ({
      notifications: s.notifications.map(n => ({ ...n, read: true })),
    })),

  dismiss: (id) =>
    set(s => ({
      notifications: s.notifications.filter(n => n.id !== id),
      toasts: s.toasts.filter(t => t !== id),
    })),

  clear: () => set({ notifications: [], toasts: [] }),

  dismissToast: (id) =>
    set(s => ({ toasts: s.toasts.filter(t => t !== id) })),

  notify: {
    success: (title, message) => get().push({ type: 'success', title, message }),
    error: (title, message) => get().push({ type: 'error', title, message }),
    info: (title, message) => get().push({ type: 'info', title, message }),
    loading: (title, message) => get().push({ type: 'loading', title, message }),
  }
}));

/** Convenience helper usable anywhere (no React hooks required) */
export const notify = {
  success: (title: string, message?: string) =>
    useNotificationStore.getState().push({ type: 'success', title, message }),
  error: (title: string, message?: string) =>
    useNotificationStore.getState().push({ type: 'error', title, message }),
  info: (title: string, message?: string) =>
    useNotificationStore.getState().push({ type: 'info', title, message }),
  loading: (title: string, message?: string) =>
    useNotificationStore.getState().push({ type: 'loading', title, message }),
};

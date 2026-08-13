'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase';
import { notify } from '@/store/notificationStore';
import { useTheme } from 'next-themes';
import {
  Bell, Moon, Sun, Monitor, Globe, Shield, Database, Trash2,
  CheckCircle2, AlertCircle, Loader2, ChevronRight, Palette
} from 'lucide-react';

function SettingSection({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b bg-muted/30 flex items-center gap-2">
        <span className="text-indigo-500">{icon}</span>
        <h2 className="font-semibold text-sm tracking-wide uppercase text-muted-foreground">{title}</h2>
      </div>
      <div className="divide-y">
        {children}
      </div>
    </div>
  );
}

function ToggleRow({ label, description, checked, onChange }: {
  label: string; description?: string; checked: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between px-6 py-4 hover:bg-muted/20 transition-colors">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 ${checked ? 'bg-indigo-600' : 'bg-gray-200'}`}
      >
        <span className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  const [notifGeneration, setNotifGeneration] = useState(true);
  const [notifUpload, setNotifUpload] = useState(true);
  const [notifErrors, setNotifErrors] = useState(true);
  const [language, setLanguage] = useState('en');
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState('');

  // Load settings from localStorage
  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem('learnova_settings');
    if (saved) {
      const s = JSON.parse(saved);
      if (s.notifGeneration !== undefined) setNotifGeneration(s.notifGeneration);
      if (s.notifUpload !== undefined) setNotifUpload(s.notifUpload);
      if (s.notifErrors !== undefined) setNotifErrors(s.notifErrors);
      if (s.language) setLanguage(s.language);
    }
  }, []);

  const save = (patch: object) => {
    const current = JSON.parse(localStorage.getItem('learnova_settings') || '{}');
    const next = { ...current, ...patch };
    localStorage.setItem('learnova_settings', JSON.stringify(next));
    notify.success('Settings saved', 'Your preferences have been updated.');
  };

  const themeOptions = [
    { value: 'light', label: 'Light', icon: <Sun size={16} /> },
    { value: 'dark', label: 'Dark', icon: <Moon size={16} /> },
    { value: 'system', label: 'System', icon: <Monitor size={16} /> },
  ];

  return (
    <main className="p-6 md:p-10 max-w-3xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Customize your Learnova workspace experience.</p>
      </div>

      {/* Appearance */}
      <SettingSection title="Appearance" icon={<Palette size={16} />}>
        <div className="px-6 py-4">
          <p className="text-sm font-medium mb-3">Theme</p>
          <div className="flex gap-3">
            {mounted && themeOptions.map(opt => (
              <button
                key={opt.value}
                onClick={() => setTheme(opt.value)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                  theme === opt.value
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-md'
                    : 'border-border hover:bg-muted'
                }`}
              >
                {opt.icon} {opt.label}
              </button>
            ))}
          </div>
        </div>
      </SettingSection>

      {/* Notifications */}
      <SettingSection title="Notifications" icon={<Bell size={16} />}>
        <ToggleRow
          label="Generation events"
          description="Get notified when question generation completes, partially completes, or fails."
          checked={notifGeneration}
          onChange={v => { setNotifGeneration(v); save({ notifGeneration: v }); }}
        />
        <ToggleRow
          label="Upload events"
          description="Notify when a file finishes uploading and starts processing."
          checked={notifUpload}
          onChange={v => { setNotifUpload(v); save({ notifUpload: v }); }}
        />
        <ToggleRow
          label="Error alerts"
          description="Show pop-up notifications for any errors or failures."
          checked={notifErrors}
          onChange={v => { setNotifErrors(v); save({ notifErrors: v }); }}
        />
      </SettingSection>

      {/* Language */}
      <SettingSection title="Language & Region" icon={<Globe size={16} />}>
        <div className="flex items-center justify-between px-6 py-4 hover:bg-muted/20 transition-colors">
          <div>
            <p className="text-sm font-medium">Interface Language</p>
            <p className="text-xs text-muted-foreground mt-0.5">Select your preferred display language.</p>
          </div>
          <select
            value={language}
            onChange={e => { setLanguage(e.target.value); save({ language: e.target.value }); }}
            className="text-sm border rounded-lg px-3 py-1.5 bg-background focus:ring-2 focus:ring-indigo-300 outline-none"
          >
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="kn">Kannada</option>
            <option value="ta">Tamil</option>
            <option value="te">Telugu</option>
            <option value="mr">Marathi</option>
          </select>
        </div>
      </SettingSection>

      {/* Privacy */}
      <SettingSection title="Privacy & Security" icon={<Shield size={16} />}>
        <div className="flex items-center justify-between px-6 py-4 hover:bg-muted/20 transition-colors cursor-pointer" onClick={() => notify.info('Coming soon', 'Active session management will be available in a future update.')}>
          <div>
            <p className="text-sm font-medium">Active Sessions</p>
            <p className="text-xs text-muted-foreground mt-0.5">View and revoke active login sessions.</p>
          </div>
          <ChevronRight size={16} className="text-muted-foreground" />
        </div>
      </SettingSection>

      {/* Data */}
      <SettingSection title="Data & Storage" icon={<Database size={16} />}>
        <div className="flex items-center justify-between px-6 py-4 hover:bg-muted/20 transition-colors cursor-pointer" onClick={() => { notify.info('Export requested', 'Your data export will be ready shortly.'); }}>
          <div>
            <p className="text-sm font-medium">Export My Data</p>
            <p className="text-xs text-muted-foreground mt-0.5">Download a copy of all your questions, papers, and resources.</p>
          </div>
          <ChevronRight size={16} className="text-muted-foreground" />
        </div>
      </SettingSection>

      {/* Danger Zone */}
      <div className="rounded-2xl border border-red-200 bg-red-50/30 overflow-hidden">
        <div className="px-6 py-4 border-b border-red-100 flex items-center gap-2">
          <Trash2 size={16} className="text-red-500" />
          <h2 className="font-semibold text-sm tracking-wide uppercase text-red-600">Danger Zone</h2>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div>
            <p className="text-sm font-medium text-red-800">Delete Account</p>
            <p className="text-xs text-muted-foreground mt-1">
              Permanently delete your account, all your exams, subjects, knowledge, questions, and papers. This action cannot be undone.
            </p>
          </div>
          {!deletingAccount ? (
            <button
              onClick={() => setDeletingAccount(true)}
              className="text-sm font-semibold text-red-600 border border-red-200 px-4 py-2 rounded-lg hover:bg-red-100 transition"
            >
              Delete My Account
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-red-700 font-medium">Type <code className="bg-red-100 px-1 rounded">DELETE</code> to confirm:</p>
              <input
                type="text"
                value={confirmDelete}
                onChange={e => setConfirmDelete(e.target.value)}
                className="w-full max-w-xs px-3 py-2 border border-red-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                placeholder="Type DELETE"
              />
              <div className="flex gap-2">
                <button
                  disabled={confirmDelete !== 'DELETE'}
                  className="text-sm font-semibold bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  onClick={() => notify.info('Account deletion', 'Please contact support to complete account deletion for security reasons.')}
                >
                  Confirm Delete
                </button>
                <button
                  onClick={() => { setDeletingAccount(false); setConfirmDelete(''); }}
                  className="text-sm px-4 py-2 rounded-lg hover:bg-muted transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

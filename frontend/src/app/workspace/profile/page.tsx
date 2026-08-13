'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import {
  User, Mail, Lock, LogOut, Loader2, CheckCircle2,
  AlertCircle, Eye, EyeOff, Shield, BookOpen, Calendar
} from 'lucide-react';

type UserProfile = {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
};

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Edit name
  const [editName, setEditName] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [nameMsg, setNameMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  // Change password
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [savingPw, setSavingPw] = useState(false);
  const [pwMsg, setPwMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  useEffect(() => {
    const load = async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { router.replace('/login'); return; }
      const p: UserProfile = {
        id: user.id,
        email: user.email ?? '',
        full_name: user.user_metadata?.full_name ?? '',
        created_at: user.created_at,
      };
      setProfile(p);
      setEditName(p.full_name);
      setLoading(false);
    };
    load();
  }, [router]);

  const handleSaveName = async () => {
    if (!editName.trim()) return;
    setSavingName(true);
    setNameMsg(null);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ data: { full_name: editName.trim() } });
    setSavingName(false);
    if (error) {
      setNameMsg({ type: 'err', text: error.message });
    } else {
      setProfile(p => p ? { ...p, full_name: editName.trim() } : p);
      setNameMsg({ type: 'ok', text: 'Name updated successfully!' });
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    if (newPw !== confirmPw) { setPwMsg({ type: 'err', text: 'New passwords do not match.' }); return; }
    if (newPw.length < 6) { setPwMsg({ type: 'err', text: 'Password must be at least 6 characters.' }); return; }
    setSavingPw(true);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ password: newPw });
    setSavingPw(false);
    if (error) {
      setPwMsg({ type: 'err', text: error.message });
    } else {
      setPwMsg({ type: 'ok', text: 'Password changed successfully!' });
      setCurrentPw(''); setNewPw(''); setConfirmPw('');
    }
  };

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace('/login');
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const initials = profile?.full_name
    ? profile.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : profile?.email?.[0]?.toUpperCase() ?? '?';

  const joinedDate = profile?.created_at
    ? new Date(profile.created_at).toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' })
    : '';

  return (
    <main className="p-6 md:p-10 max-w-3xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">My Profile</h1>
        <p className="text-muted-foreground mt-1">Manage your account information and security settings.</p>
      </div>

      {/* Profile Card */}
      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        {/* Hero banner */}
        <div className="h-24 bg-gradient-to-r from-indigo-500 via-purple-500 to-violet-600" />

        <div className="px-6 pb-6">
          {/* Avatar */}
          <div className="-mt-12 mb-4 flex items-end justify-between">
            <div
              className="h-20 w-20 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center text-white text-2xl font-bold shadow-lg border-4 border-background"
            >
              {initials}
            </div>
          </div>

          <h2 className="text-xl font-bold">{profile?.full_name || 'Teacher'}</h2>
          <p className="text-muted-foreground text-sm">{profile?.email}</p>

          <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-muted font-medium">
              <Shield size={12} className="text-indigo-500" /> Teacher Account
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-muted font-medium">
              <Calendar size={12} /> Joined {joinedDate}
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-muted font-medium">
              <BookOpen size={12} className="text-violet-500" /> Learnova Workspace
            </span>
          </div>
        </div>
      </div>

      {/* Edit Name */}
      <div className="rounded-2xl border bg-card shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <User size={18} className="text-indigo-500" />
          <h3 className="font-semibold text-base">Display Name</h3>
        </div>

        {nameMsg && (
          <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg ${nameMsg.type === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
            {nameMsg.type === 'ok' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
            {nameMsg.text}
          </div>
        )}

        <div className="flex gap-3">
          <input
            type="text"
            value={editName}
            onChange={e => setEditName(e.target.value)}
            className="flex-1 px-3 py-2 text-sm border rounded-lg bg-muted/30 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 transition"
            placeholder="Your full name"
          />
          <button
            onClick={handleSaveName}
            disabled={savingName || !editName.trim()}
            className="px-4 py-2 text-sm font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
          >
            {savingName && <Loader2 size={13} className="animate-spin" />}
            Save
          </button>
        </div>
      </div>

      {/* Email (readonly) */}
      <div className="rounded-2xl border bg-card shadow-sm p-6 space-y-2">
        <div className="flex items-center gap-2">
          <Mail size={18} className="text-indigo-500" />
          <h3 className="font-semibold text-base">Email Address</h3>
        </div>
        <p className="text-xs text-muted-foreground">Email is managed by your authentication provider.</p>
        <div className="mt-2 px-3 py-2 border rounded-lg bg-muted/30 text-sm text-muted-foreground">
          {profile?.email}
        </div>
      </div>

      {/* Change Password */}
      <div className="rounded-2xl border bg-card shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Lock size={18} className="text-indigo-500" />
          <h3 className="font-semibold text-base">Change Password</h3>
        </div>

        {pwMsg && (
          <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg ${pwMsg.type === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
            {pwMsg.type === 'ok' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
            {pwMsg.text}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-3">
          <div className="relative">
            <input
              type="password"
              value={newPw}
              onChange={e => setNewPw(e.target.value)}
              className="w-full px-3 py-2 pr-10 text-sm border rounded-lg bg-muted/30 focus:outline-none focus:ring-2 focus:ring-indigo-300 transition"
              placeholder="New password (min. 6 chars)"
              required
            />
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" onClick={() => setShowNew(p => !p)}>
              {showNew ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          <input
            type="password"
            value={confirmPw}
            onChange={e => setConfirmPw(e.target.value)}
            className="w-full px-3 py-2 text-sm border rounded-lg bg-muted/30 focus:outline-none focus:ring-2 focus:ring-indigo-300 transition"
            placeholder="Confirm new password"
            required
          />
          <button
            type="submit"
            disabled={savingPw || !newPw || !confirmPw}
            className="px-4 py-2 text-sm font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
          >
            {savingPw && <Loader2 size={13} className="animate-spin" />}
            Update Password
          </button>
        </form>
      </div>

      {/* Danger Zone */}
      <div className="rounded-2xl border border-red-100 bg-red-50/30 p-6 space-y-3">
        <h3 className="font-semibold text-base text-red-700 flex items-center gap-2">
          <LogOut size={18} /> Sign Out
        </h3>
        <p className="text-sm text-muted-foreground">You will be signed out of all sessions on this device.</p>
        <button
          onClick={handleLogout}
          className="px-4 py-2 text-sm font-semibold text-red-600 border border-red-200 rounded-lg hover:bg-red-100 transition"
        >
          Sign Out
        </button>
      </div>
    </main>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import Image from 'next/image';

export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return; }

    setLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ password });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      setSuccess(true);
      setTimeout(() => router.push('/workspace'), 2000);
    }
  };

  return (
    <div className="auth-root">
      <div className="auth-left">
        <div className="auth-left-inner">
          <div className="auth-brand">
            <Image 
              src="/logo-light.png" 
              alt="Learnova Logo" 
              width={200} 
              height={60} 
              className="dark:hidden object-contain h-[48px] w-auto" 
              priority
            />
            <Image 
              src="/logo-dark.png" 
              alt="Learnova Logo" 
              width={200} 
              height={60} 
              className="hidden dark:block object-contain h-[48px] w-auto" 
              priority
            />
          </div>
          <div className="auth-hero">
            <h1 className="auth-hero-title">Secure your account</h1>
            <p className="auth-hero-sub">Choose a strong password to protect your workspace.</p>
          </div>
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-forgot-header">
            <div className="auth-forgot-icon" style={{ background: 'var(--auth-accent-light)', color: 'var(--auth-accent)' }}>
              <CheckCircle2 size={24} />
            </div>
            <h2 className="auth-form-title">Set New Password</h2>
            <p className="auth-form-sub">Enter and confirm your new password below.</p>
          </div>

          {error && <div className="auth-alert auth-alert-error"><AlertCircle size={15} /> {error}</div>}

          {success ? (
            <div className="auth-alert auth-alert-success" style={{ justifyContent: 'center', padding: '1.5rem', fontSize: '1rem' }}>
              <CheckCircle2 size={20} /> Password updated! Redirecting...
            </div>
          ) : (
            <form onSubmit={handleReset} className="auth-form">
              <div className="auth-field">
                <label className="auth-label">New Password</label>
                <div className="auth-input-wrap">
                  <input
                    type={showPw ? 'text' : 'password'}
                    className="auth-input auth-input-pw"
                    placeholder="Min. 6 characters"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                  />
                  <button type="button" className="auth-eye" onClick={() => setShowPw(p => !p)}>
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <div className="auth-field">
                <label className="auth-label">Confirm Password</label>
                <div className="auth-input-wrap">
                  <input
                    type="password"
                    className="auth-input auth-input-pw"
                    placeholder="••••••••"
                    value={confirm}
                    onChange={e => setConfirm(e.target.value)}
                    required
                  />
                </div>
              </div>
              <button type="submit" className="auth-btn-primary" disabled={loading}>
                {loading ? <><Loader2 size={16} className="auth-spin" /> Updating...</> : 'Update Password'}
              </button>
            </form>
          )}
        </div>
        <p className="auth-footer">© {new Date().getFullYear()} Learnova · AI Education Platform</p>
      </div>
    </div>
  );
}

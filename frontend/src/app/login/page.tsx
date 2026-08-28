'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, CheckCircle2, Loader2, AlertCircle, ArrowLeft, Mail } from 'lucide-react';
import Image from 'next/image';

type AuthMode = 'login' | 'register' | 'forgot';

export default function AuthPage() {
  const [mode, setMode] = useState<AuthMode>('login');
  const router = useRouter();

  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const resetMessages = () => { setError(''); setSuccess(''); };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();
    setLoading(true);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      setLoading(false);
      if (error) {
        setError(error.message);
      } else {
        router.push('/workspace');
      }
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'An unexpected error occurred during sign in.');
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { 
          data: { full_name: fullName },
          emailRedirectTo: `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/callback`,
        },
      });
      setLoading(false);
      if (error) {
        setError(error.message);
      } else {
        setSuccess('Account created! Check your email to confirm, or sign in if auto-confirmed.');
        setMode('login');
      }
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'An unexpected error occurred during registration.');
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (!email) { setError('Please enter your email address.'); return; }
    setLoading(true);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      });
      setLoading(false);
      if (error) {
        setError(error.message);
      } else {
        setSuccess('Password reset link sent! Check your inbox.');
      }
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'An unexpected error occurred.');
    }
  };

  const switchMode = (m: AuthMode) => {
    setMode(m);
    resetMessages();
  };

  return (
    <div className="auth-root">
      {/* Left Panel */}
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
            <h1 className="auth-hero-title">AI-Powered Question Generation</h1>
            <p className="auth-hero-sub">
              Transform your teaching materials into smart, exam-ready question banks in minutes.
            </p>
          </div>

          <ul className="auth-features">
            {[
              'Upload notes & textbooks as knowledge base',
              'Generate questions aligned to exam patterns',
              'Build, review & export question papers',
            ].map((f) => (
              <li key={f} className="auth-feature-item">
                <CheckCircle2 size={18} className="auth-check" />
                <span>{f}</span>
              </li>
            ))}
          </ul>

          <div className="auth-quote">
            <blockquote>"The future of education is personalized, intelligent, and efficient."</blockquote>
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="auth-right">
        <div className="auth-card">
          {/* Header */}
          {mode === 'login' && (
            <div className="auth-card-header">
              <h2 className="auth-form-title">Welcome back</h2>
              <p className="auth-form-sub">Sign in to your Learnova account</p>
            </div>
          )}
          {mode === 'register' && (
            <div className="auth-card-header">
              <h2 className="auth-form-title">Create account</h2>
              <p className="auth-form-sub">Join Learnova and start building your question bank</p>
            </div>
          )}

          {/* Forgot Password header */}
          {mode === 'forgot' && (
            <div className="auth-forgot-header">
              <button suppressHydrationWarning className="auth-back-btn" onClick={() => switchMode('login')} type="button">
                <ArrowLeft size={16} /> Back to Sign In
              </button>
              <div className="auth-forgot-icon"><Mail size={24} /></div>
              <h2 className="auth-form-title">Reset Password</h2>
              <p className="auth-form-sub">Enter your email and we'll send a reset link.</p>
            </div>
          )}

          {/* Alerts */}
          {error && (
            <div className="auth-alert auth-alert-error">
              <AlertCircle size={15} /> {error}
            </div>
          )}
          {success && (
            <div className="auth-alert auth-alert-success">
              <CheckCircle2 size={15} /> {success}
            </div>
          )}

          {/* LOGIN FORM */}
          {mode === 'login' && (
            <form suppressHydrationWarning onSubmit={handleLogin} className="auth-form">
              <div className="auth-field">
                <label className="auth-label">Email Address</label>
                <input suppressHydrationWarning
                  type="email"
                  className="auth-input"
                  placeholder="teacher@institution.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>

              <div className="auth-field">
                <div className="auth-label-row">
                  <label className="auth-label">Password</label>
                  <button suppressHydrationWarning type="button" className="auth-forgot-link" onClick={() => switchMode('forgot')}>
                    Forgot password?
                  </button>
                </div>
                <div className="auth-input-wrap">
                  <input suppressHydrationWarning
                    type={showPassword ? 'text' : 'password'}
                    className="auth-input auth-input-pw"
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                  <button suppressHydrationWarning type="button" className="auth-eye" onClick={() => setShowPassword(p => !p)}>
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <label className="auth-remember">
                <input suppressHydrationWarning
                  type="checkbox"
                  checked={rememberMe}
                  onChange={e => setRememberMe(e.target.checked)}
                  className="auth-checkbox"
                />
                <span>Remember me for 30 days</span>
              </label>

              <button suppressHydrationWarning type="submit" className="auth-btn-primary" disabled={loading}>
                {loading ? <><Loader2 size={16} className="auth-spin" /> Signing in...</> : 'Sign In'}
              </button>

              <p className="auth-switch-hint">
                Don't have an account?{' '}
                <button suppressHydrationWarning type="button" className="auth-switch-link" onClick={() => switchMode('register')}>
                  Create one free
                </button>
              </p>
            </form>
          )}

          {/* REGISTER FORM */}
          {mode === 'register' && (
            <form suppressHydrationWarning onSubmit={handleRegister} className="auth-form">
              <div className="auth-field">
                <label className="auth-label">Full Name</label>
                <input suppressHydrationWarning
                  type="text"
                  className="auth-input"
                  placeholder="YOUR NAME "
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  required
                  autoComplete="name"
                />
              </div>

              <div className="auth-field">
                <label className="auth-label">Email Address</label>
                <input suppressHydrationWarning
                  type="email"
                  className="auth-input"
                  placeholder="YOUR MAIL ID"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>

              <div className="auth-field">
                <label className="auth-label">Password</label>
                <div className="auth-input-wrap">
                  <input suppressHydrationWarning
                    type={showPassword ? 'text' : 'password'}
                    className="auth-input auth-input-pw"
                    placeholder="Min. 6 characters"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                  />
                  <button suppressHydrationWarning type="button" className="auth-eye" onClick={() => setShowPassword(p => !p)}>
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="auth-field">
                <label className="auth-label">Confirm Password</label>
                <div className="auth-input-wrap">
                  <input suppressHydrationWarning
                    type={showConfirm ? 'text' : 'password'}
                    className="auth-input auth-input-pw"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                  />
                  <button suppressHydrationWarning type="button" className="auth-eye" onClick={() => setShowConfirm(p => !p)}>
                    {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button suppressHydrationWarning type="submit" className="auth-btn-primary" disabled={loading}>
                {loading ? <><Loader2 size={16} className="auth-spin" /> Creating account...</> : 'Create Account'}
              </button>

              <p className="auth-switch-hint">
                Already have an account?{' '}
                <button suppressHydrationWarning type="button" className="auth-switch-link" onClick={() => switchMode('login')}>
                  Sign in
                </button>
              </p>
            </form>
          )}

          {/* FORGOT PASSWORD FORM */}
          {mode === 'forgot' && (
            <form suppressHydrationWarning onSubmit={handleForgotPassword} className="auth-form">
              <div className="auth-field">
                <label className="auth-label">Email Address</label>
                <input suppressHydrationWarning
                  type="email"
                  className="auth-input"
                  placeholder="teacher@institution.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <button suppressHydrationWarning type="submit" className="auth-btn-primary" disabled={loading}>
                {loading ? <><Loader2 size={16} className="auth-spin" /> Sending...</> : 'Send Reset Link'}
              </button>
            </form>
          )}
        </div>

        <p suppressHydrationWarning className="auth-footer">
          © {new Date().getFullYear()} Learnova · AI Education Platform
        </p>
      </div>
    </div>
  );
}

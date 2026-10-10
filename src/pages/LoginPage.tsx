import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';
import { ThemeToggle } from '../components/common/ThemeToggle';

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('prasanna@accountable.com');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/dashboard');
  };

  return (
    <div
      className="relative isolate flex min-h-[100dvh] items-center justify-center px-6 py-16"
      style={{ background: 'var(--bg)', color: 'var(--text)' }}
    >
      <BackgroundVideo showOverlay={true} dimmed={true} />

      {/* Brand + ThemeToggle row */}
      <div className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-8 py-6 sm:px-10">
        <Link
          to="/"
          className="font-serif text-3xl font-normal tracking-tight transition-opacity hover:opacity-90"
          style={{ color: 'var(--text-secondary)', textShadow: '0 1px 8px rgba(0,0,0,0.35)' }}
        >
          Accountable
        </Link>
        <ThemeToggle />
      </div>

      {/* Login Card */}
      <div
        className="relative z-10 w-full max-w-[480px] rounded-2xl border p-9 backdrop-blur-2xl sm:p-12"
        style={{
          borderColor: 'var(--border-strong)',
          background: 'color-mix(in srgb, var(--surface) 96%, transparent)',
          boxShadow: 'var(--shadow-modal)',
        }}
      >
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal sm:text-4xl" style={{ color: 'var(--text)' }}>
            Welcome back
          </h1>
          <p className="mt-3 text-base" style={{ color: 'var(--accent-warm)' }}>
            Sign in to your Accountable workspace
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-9 space-y-6">
          <div>
            <label
              className="block text-xs font-semibold tracking-wider uppercase"
              style={{ color: 'var(--text-secondary)' }}
            >
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="mt-2.5 w-full rounded-xl border px-5 py-4 text-base font-medium transition-colors focus:outline-hidden"
              style={{
                borderColor: 'var(--border)',
                background: 'var(--surface-input)',
                color: 'var(--text)',
              }}
              onFocus={(e) => (e.target.style.borderColor = 'var(--accent)')}
              onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
            />
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label
                className="block text-xs font-semibold tracking-wider uppercase"
                style={{ color: 'var(--text-secondary)' }}
              >
                Password
              </label>
              <button
                type="button"
                onClick={() => alert('Password reset link sent to registered email.')}
                className="text-xs font-medium hover:underline"
                style={{ color: 'var(--accent)' }}
              >
                Forgot password?
              </button>
            </div>
            <div className="relative mt-2.5">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border px-5 py-4 pr-12 text-base font-medium transition-colors focus:outline-hidden"
                style={{
                  borderColor: 'var(--border)',
                  background: 'var(--surface-input)',
                  color: 'var(--text)',
                }}
                onFocus={(e) => (e.target.style.borderColor = 'var(--accent)')}
                onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                style={{ color: 'var(--text-muted)' }}
              >
                {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="flex h-[56px] w-full items-center justify-center gap-2.5 rounded-xl text-base font-semibold tracking-wide transition-all"
            style={{
              background: 'var(--accent-warm)',
              color: 'var(--accent-contrast)',
              boxShadow: 'var(--shadow-gold)',
            }}
          >
            <span>Sign in</span>
            <ArrowRight className="size-5" />
          </button>
        </form>

        <p className="mt-8 text-center text-base" style={{ color: 'var(--text-muted)' }}>
          Don't have an account?{' '}
          <Link to="/signup" className="font-semibold hover:underline" style={{ color: 'var(--accent)' }}>
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

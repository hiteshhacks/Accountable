import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';
import { ThemeToggle } from '../components/common/ThemeToggle';

export function SignupPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/dashboard');
  };

  const inputClass = 'mt-2 w-full rounded-xl border px-4 py-3.5 text-base transition-colors focus:outline-hidden';
  const inputStyle = (focused: boolean) => ({
    borderColor: focused ? 'var(--accent)' : 'var(--border)',
    background: 'var(--surface-input)',
    color: 'var(--text)',
  });

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

      {/* Sign-up Card */}
      <div
        className="relative z-10 w-full max-w-[500px] rounded-2xl border p-8 backdrop-blur-2xl sm:p-11"
        style={{
          borderColor: 'var(--border)',
          background: 'color-mix(in srgb, var(--surface) 96%, transparent)',
          boxShadow: 'var(--shadow-modal)',
        }}
      >
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal sm:text-4xl" style={{ color: 'var(--text)' }}>
            Create your Accountable account
          </h1>
          <p className="mt-2.5 text-base" style={{ color: 'var(--text-muted)' }}>
            Start intelligent accounting classification in minutes
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          {/* Full name */}
          <div>
            <label className="block text-xs font-semibold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>
              Full name
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your Name"
              className={inputClass}
              style={inputStyle(false)}
              onFocus={(e) => Object.assign(e.target.style, { borderColor: 'var(--accent)' })}
              onBlur={(e) => Object.assign(e.target.style, { borderColor: 'var(--border)' })}
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-xs font-semibold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className={inputClass}
              style={inputStyle(false)}
              onFocus={(e) => Object.assign(e.target.style, { borderColor: 'var(--accent)' })}
              onBlur={(e) => Object.assign(e.target.style, { borderColor: 'var(--border)' })}
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-semibold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>
              Password
            </label>
            <div className="relative mt-2">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border px-4 py-3.5 pr-12 text-base transition-colors focus:outline-hidden"
                style={inputStyle(false)}
                onFocus={(e) => Object.assign(e.target.style, { borderColor: 'var(--accent)' })}
                onBlur={(e) => Object.assign(e.target.style, { borderColor: 'var(--border)' })}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                style={{ color: 'var(--text-faint)' }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-muted)')}
                onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-faint)')}
              >
                {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
              </button>
            </div>
          </div>

          {/* Confirm Password */}
          <div>
            <label className="block text-xs font-semibold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>
              Confirm password
            </label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              className={inputClass}
              style={inputStyle(false)}
              onFocus={(e) => Object.assign(e.target.style, { borderColor: 'var(--accent)' })}
              onBlur={(e) => Object.assign(e.target.style, { borderColor: 'var(--border)' })}
            />
          </div>

          <button
            type="submit"
            className="flex h-[54px] w-full items-center justify-center gap-2 rounded-xl text-base font-semibold tracking-wide transition-all"
            style={{
              background: 'var(--accent-warm)',
              color: 'var(--accent-contrast)',
              boxShadow: 'var(--shadow-gold)',
            }}
          >
            <span>Create account</span>
            <ArrowRight className="size-5" />
          </button>
        </form>

        <p className="mt-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
          Already have an account?{' '}
          <Link to="/login" className="font-medium hover:underline" style={{ color: 'var(--accent)' }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('prasanna@abc.com');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/onboarding');
  };

  return (
    <div className="relative isolate flex min-h-screen items-center justify-center px-4 py-12 bg-[#0A0805] text-[#F1E7CF]">
      {/* Background with cinematic ambience */}
      <BackgroundVideo showOverlay={true} dimmed={true} />

      {/* Brand in top-left */}
      <div className="fixed top-6 left-6 sm:top-8 sm:left-10">
        <Link to="/" className="font-serif text-2xl tracking-tight text-[#E8D29A] hover:text-[#F1E7CF]">
          Accountable
        </Link>
      </div>

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-[440px] rounded-2xl border border-[rgba(200,168,90,0.22)] bg-[#17130D]/90 p-8 shadow-[0_24px_70px_rgba(0,0,0,0.7)] backdrop-blur-xl sm:p-10">
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal text-[#F1E7CF]">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-[#B9AD92]">
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <div>
            <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="mt-2 w-full rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 text-sm text-[#F1E7CF] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
            />
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
                Password
              </label>
              <button
                type="button"
                onClick={() => alert('Password reset link sent to registered email.')}
                className="text-xs text-[#C8A85A] hover:underline"
              >
                Forgot password?
              </button>
            </div>
            <div className="relative mt-2">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 pr-11 text-sm text-[#F1E7CF] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#756B58] hover:text-[#B9AD92]"
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#C8A85A] py-3 text-sm font-semibold tracking-wide text-[#0A0805] shadow-[0_4px_20px_rgba(200,168,90,0.18)] transition-all hover:bg-[#D8BC78]"
          >
            <span>Sign in</span>
            <ArrowRight className="size-4" />
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[rgba(200,168,90,0.15)]" />
          </div>
          <span className="relative bg-[#17130D] px-3 text-xs text-[#756B58]">
            or continue with
          </span>
        </div>

        {/* Google OAuth Option */}
        <button
          type="button"
          onClick={() => navigate('/onboarding')}
          className="flex w-full items-center justify-center gap-3 rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] py-2.5 text-sm font-medium text-[#F1E7CF] transition-colors hover:border-[rgba(200,168,90,0.4)] hover:bg-[#1D1810]"
        >
          <svg className="size-4" viewBox="0 0 24 24">
            <path
              fill="#EA4335"
              d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
            />
            <path
              fill="#4285F4"
              d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
            />
            <path
              fill="#FBBC05"
              d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.8 0 12s.7 3.3 1.9 5.7l3.7-2.9z"
            />
            <path
              fill="#34A853"
              d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z"
            />
          </svg>
          <span>Continue with Google</span>
        </button>

        {/* Footer Link */}
        <p className="mt-7 text-center text-xs text-[#756B58]">
          Don't have an account?{' '}
          <Link to="/signup" className="text-[#C8A85A] hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

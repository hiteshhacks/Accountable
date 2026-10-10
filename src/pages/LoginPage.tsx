import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';

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
    <div className="relative isolate flex min-h-screen items-center justify-center px-6 py-12 bg-[#090704] text-[#F0E5CA]">
      <BackgroundVideo showOverlay={true} dimmed={true} />

      {/* Brand Logo */}
      <div className="fixed top-8 left-8 sm:top-10 sm:left-12">
        <Link to="/" className="font-serif text-3xl font-normal tracking-tight text-[#E8D29A] hover:text-[#F0E5CA]">
          Accountable
        </Link>
      </div>

      {/* High-Readability Login Card */}
      <div className="relative z-10 w-full max-w-[480px] rounded-2xl border border-[rgba(200,168,90,0.35)] bg-[#17130D]/95 p-9 shadow-[0_24px_70px_rgba(0,0,0,0.9)] backdrop-blur-2xl sm:p-12">
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl">
            Welcome back
          </h1>
          <p className="mt-3 text-base text-[#D8BC78]">
            Sign in to your Accountable workspace
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-9 space-y-6">
          <div>
            <label className="block text-xs font-semibold tracking-wider text-[#E8D29A] uppercase">
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="mt-2.5 w-full rounded-xl border border-[rgba(200,168,90,0.35)] bg-[#100D08] px-5 py-4 text-base font-medium text-[#F0E5CA] placeholder-[#8F7742] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
            />
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold tracking-wider text-[#E8D29A] uppercase">
                Password
              </label>
              <button
                type="button"
                onClick={() => alert('Password reset link sent to registered email.')}
                className="text-xs font-medium text-[#C8A85A] hover:underline"
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
                className="w-full rounded-xl border border-[rgba(200,168,90,0.35)] bg-[#100D08] px-5 py-4 pr-12 text-base font-medium text-[#F0E5CA] placeholder-[#8F7742] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-[#B9AD92] hover:text-[#F0E5CA]"
              >
                {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="flex h-[56px] w-full items-center justify-center gap-2.5 rounded-xl bg-[#D8BC78] text-base font-semibold tracking-wide text-[#090704] shadow-[0_4px_24px_rgba(200,168,90,0.3)] transition-all hover:bg-[#E8D29A]"
          >
            <span>Sign in</span>
            <ArrowRight className="size-5" />
          </button>
        </form>

        <p className="mt-9 text-center text-base text-[#B9AD92]">
          Don't have an account?{' '}
          <Link to="/signup" className="font-semibold text-[#C8A85A] hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';

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

  return (
    <div className="relative isolate flex min-h-screen items-center justify-center px-6 py-12 bg-[#090704] text-[#F0E5CA]">
      <BackgroundVideo showOverlay={true} dimmed={true} />

      <div className="fixed top-8 left-8 sm:top-10 sm:left-12">
        <Link to="/" className="font-serif text-3xl font-normal tracking-tight text-[#E8D29A] hover:text-[#F0E5CA]">
          Accountable
        </Link>
      </div>

      <div className="relative z-10 w-full max-w-[500px] rounded-2xl border border-[rgba(200,168,90,0.28)] bg-[#17130D]/95 p-8 shadow-[0_24px_70px_rgba(0,0,0,0.85)] backdrop-blur-2xl sm:p-11">
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl">
            Create your Accountable account
          </h1>
          <p className="mt-2.5 text-base text-[#B9AD92]">
            Start intelligent accounting classification in minutes
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <div>
            <label className="block text-xs font-semibold tracking-wider text-[#D8BC78] uppercase">
              Full name
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your Name"
              className="mt-2 w-full rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] px-4.5 py-3.5 text-base text-[#F0E5CA] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold tracking-wider text-[#D8BC78] uppercase">
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="mt-2 w-full rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] px-4.5 py-3.5 text-base text-[#F0E5CA] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold tracking-wider text-[#D8BC78] uppercase">
              Password
            </label>
            <div className="relative mt-2">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] px-4.5 py-3.5 pr-12 text-base text-[#F0E5CA] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-[#756B58] hover:text-[#B9AD92]"
              >
                {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold tracking-wider text-[#D8BC78] uppercase">
              Confirm password
            </label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-2 w-full rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] px-4.5 py-3.5 text-base text-[#F0E5CA] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
            />
          </div>

          <button
            type="submit"
            className="flex h-[54px] w-full items-center justify-center gap-2 rounded-xl bg-[#D8BC78] text-base font-semibold tracking-wide text-[#090704] shadow-[0_4px_24px_rgba(200,168,90,0.2)] transition-all hover:bg-[#E8D29A]"
          >
            <span>Create account</span>
            <ArrowRight className="size-5" />
          </button>
        </form>

        <div className="relative my-7 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[rgba(200,168,90,0.18)]" />
          </div>
          <span className="relative bg-[#17130D] px-4 text-xs font-medium text-[#B9AD92]">
            or continue with
          </span>
        </div>

        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          className="flex h-[54px] w-full items-center justify-center gap-3.5 rounded-xl border border-[rgba(200,168,90,0.35)] bg-[#100D08] text-base font-medium text-[#F0E5CA] transition-all hover:border-[#C8A85A] hover:bg-[#1D1810]"
        >
          <svg className="size-5" viewBox="0 0 24 24">
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

        <p className="mt-8 text-center text-sm text-[#B9AD92]">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-[#C8A85A] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

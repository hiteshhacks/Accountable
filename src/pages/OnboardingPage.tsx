import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, ChevronDown } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';

export function OnboardingPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    companyName: 'ABC Private Limited',
    gstin: '27ABCDE1234F1Z5',
    pan: 'ABCDE1234F',
    financialYear: '2024-25',
    state: 'Maharashtra',
    currency: 'INR',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/dashboard');
  };

  return (
    <div className="relative isolate min-h-screen bg-[#0A0805] text-[#F1E7CF]">
      <BackgroundVideo showOverlay={true} dimmed={true} />

      {/* Top Bar with brand and progress indicator */}
      <header className="flex items-center justify-between px-8 py-6 sm:px-12">
        <Link to="/" className="font-serif text-2xl tracking-tight text-[#E8D29A] hover:text-[#F1E7CF]">
          Accountable
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="h-0.5 w-8 rounded-full bg-[#C8A85A]" />
            <div className="h-0.5 w-8 rounded-full bg-[rgba(200,168,90,0.25)]" />
          </div>
          <span className="text-xs font-medium tracking-wide text-[#B9AD92]">Step 1 of 2</span>
        </div>
      </header>

      {/* Centered Form */}
      <main className="mx-auto flex max-w-[620px] flex-col justify-center px-6 py-8">
        <div className="mb-8">
          <h1 className="font-serif text-3xl font-normal text-[#F1E7CF] sm:text-4xl">
            Set up your organization
          </h1>
          <p className="mt-2 font-serif text-base text-[#B9AD92]">
            Let's get your company details to get started
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#17130D]/90 p-8 shadow-[0_20px_60px_rgba(0,0,0,0.6)] backdrop-blur-xl sm:p-10">
          <div>
            <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
              Company name
            </label>
            <input
              type="text"
              required
              value={formData.companyName}
              onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
              className="mt-2 w-full rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 text-sm text-[#F1E7CF] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
            />
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
                GSTIN
              </label>
              <input
                type="text"
                required
                value={formData.gstin}
                onChange={(e) => setFormData({ ...formData, gstin: e.target.value })}
                className="mt-2 w-full rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 text-sm font-mono text-[#F1E7CF] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
              />
            </div>
            <div>
              <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
                PAN
              </label>
              <input
                type="text"
                required
                value={formData.pan}
                onChange={(e) => setFormData({ ...formData, pan: e.target.value })}
                className="mt-2 w-full rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 text-sm font-mono text-[#F1E7CF] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
                Financial year
              </label>
              <div className="relative mt-2">
                <select
                  value={formData.financialYear}
                  onChange={(e) => setFormData({ ...formData, financialYear: e.target.value })}
                  className="w-full appearance-none rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 text-sm text-[#F1E7CF] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
                >
                  <option value="2024-25">2024–25</option>
                  <option value="2023-24">2023–24</option>
                  <option value="2022-23">2022–23</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 size-4 text-[#8F7742]" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
                State
              </label>
              <div className="relative mt-2">
                <select
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  className="w-full appearance-none rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 text-sm text-[#F1E7CF] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
                >
                  <option value="Maharashtra">Maharashtra</option>
                  <option value="Gujarat">Gujarat</option>
                  <option value="Karnataka">Karnataka</option>
                  <option value="Delhi">Delhi</option>
                  <option value="Tamil Nadu">Tamil Nadu</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 size-4 text-[#8F7742]" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium tracking-wide text-[#B9AD92] uppercase">
                Currency
              </label>
              <div className="relative mt-2">
                <select
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  className="w-full appearance-none rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] px-4 py-3 text-sm text-[#F1E7CF] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 size-4 text-[#8F7742]" />
              </div>
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              className="inline-flex min-w-[170px] items-center justify-center gap-2 rounded-lg bg-[#C8A85A] px-6 py-3 text-sm font-semibold tracking-wide text-[#0A0805] shadow-[0_4px_20px_rgba(200,168,90,0.2)] transition-all hover:bg-[#D8BC78]"
            >
              <span>Continue</span>
              <ArrowRight className="size-4" />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

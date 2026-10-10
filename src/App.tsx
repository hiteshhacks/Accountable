import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { ValidationPage } from './pages/ValidationPage';
import { ProcessingPage } from './pages/ProcessingPage';
import { ResultsPage } from './pages/ResultsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public & Authentication Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />

        {/* Core Product Workflow Routes */}
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/validation" element={<ValidationPage />} />
        <Route path="/processing/:jobId" element={<ProcessingPage />} />
        <Route path="/processing" element={<Navigate to="/processing/job-1024" replace />} />
        <Route path="/results/:jobId" element={<ResultsPage />} />
        <Route path="/results" element={<Navigate to="/results/job-1024" replace />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

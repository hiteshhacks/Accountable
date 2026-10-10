import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { WorkspaceProvider } from './context/WorkspaceContext';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { DashboardPage } from './pages/DashboardPage';
import { TransactionsPage } from './pages/TransactionsPage';
import { GstIntelligencePage } from './pages/GstIntelligencePage';

export default function App() {
  return (
    <AppProvider>
      <WorkspaceProvider>
        <BrowserRouter>
          <Routes>
            {/* Public & Authentication Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Workspace console (backed by the VYOM API) */}
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            <Route path="/gst" element={<GstIntelligencePage />} />

            {/* The earlier in-browser upload flow is replaced by the API-backed dialogs */}
            <Route path="/upload" element={<Navigate to="/dashboard?upload=1" replace />} />
            <Route path="/validation" element={<Navigate to="/transactions" replace />} />
            <Route path="/processing/*" element={<Navigate to="/transactions" replace />} />
            <Route path="/results/*" element={<Navigate to="/transactions" replace />} />
            <Route path="/onboarding" element={<Navigate to="/dashboard" replace />} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </WorkspaceProvider>
    </AppProvider>
  );
}

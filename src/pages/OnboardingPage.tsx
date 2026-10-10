// Onboarding page completely removed as requested
import { Navigate } from 'react-router-dom';

export function OnboardingPage() {
  return <Navigate to="/dashboard" replace />;
}

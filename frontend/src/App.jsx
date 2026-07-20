import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ThemeProvider from "@/context/ThemeContext";
import ErrorBoundary from "@/components/ErrorBoundary";
import Spinner from "@/components/ui/Spinner";
import LandingPage from "@/pages/LandingPage";

const Dashboard       = lazy(() => import("@/pages/Dashboard"));
const CitizenAdvisory = lazy(() => import("@/pages/CitizenAdvisory"));
const Enforcement     = lazy(() => import("@/pages/Enforcement"));

function PageFallback() {
  return (
    <div className="loader-overlay">
      <Spinner size="lg" />
      <span className="loader-text">Loading…</span>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <ErrorBoundary>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/"            element={<LandingPage />} />
              <Route path="/dashboard"   element={<Dashboard />} />
              <Route path="/advisory"    element={<CitizenAdvisory />} />
              <Route path="/predictor"   element={<Navigate to="/advisory" replace />} />
              <Route path="/enforcement" element={<Enforcement />} />
              <Route path="*"            element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </BrowserRouter>
    </ThemeProvider>
  );
}

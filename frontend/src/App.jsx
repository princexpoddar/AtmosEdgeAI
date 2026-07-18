import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ThemeProvider from "@/context/ThemeContext";
import ErrorBoundary from "@/components/ErrorBoundary";
import Spinner from "@/components/ui/Spinner";
import LandingPage from "@/pages/LandingPage";

const Dashboard  = lazy(() => import("@/pages/Dashboard"));
const Predictor  = lazy(() => import("@/pages/Predictor"));
const Enforcement = lazy(() => import("@/pages/Enforcement"));

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
              <Route path="/predictor"   element={<Predictor />} />
              <Route path="/enforcement" element={<Enforcement />} />
              <Route path="*"            element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </BrowserRouter>
    </ThemeProvider>
  );
}

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { useState, useEffect, createContext, useContext } from "react";
import { fetchWithRetry } from "@/lib/api";
import "@/App.css";

// Pages
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import Dashboard from "@/pages/Dashboard";
import EmployeeSurvey from "@/pages/EmployeeSurvey";
import EmployeeManagement from "@/pages/EmployeeManagement";
import AnalyticsPage from "@/pages/AnalyticsPage";
import ReportsPage from "@/pages/ReportsPage";
import ReportDetail from "@/pages/ReportDetail";
import PricingPage from "@/pages/PricingPage";
import BillingPage from "@/pages/BillingPage";
import PaymentCallbackPage from "@/pages/PaymentCallbackPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import SecuritySettingsPage from "@/pages/SecuritySettingsPage";
import PhishingSimulationPage from "@/pages/PhishingSimulationPage";
import PhishingTrainingPage from "@/pages/PhishingTrainingPage";
import StandardsSummaryPage from "@/pages/StandardsSummaryPage";

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  const clearAppCaches = () => {
    if ("caches" in window) {
      caches.keys().then((keys) =>
        Promise.all(keys.filter((key) => key.startsWith("cultureshield-")).map((key) => caches.delete(key)))
      );
    }
  };

  useEffect(() => {
    const verifyToken = async () => {
      const currentToken = token;
      setLoading(true);

      if (currentToken) {
        try {
          const { response, data } = await fetchWithRetry(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${currentToken}` },
          });

          if (currentToken !== localStorage.getItem("token")) {
            return;
          }

          if (response.ok) {
            setUser(data);
          } else {
            localStorage.removeItem("token");
            setToken(null);
            setUser(null);
          }
        } catch (error) {
          console.error("Token verification failed:", error);
          if (currentToken === localStorage.getItem("token")) {
            setUser(null);
          }
        }
      } else {
        setUser(null);
      }
      setLoading(false);
    };
    verifyToken();
  }, [token, API]);

  const login = (accessToken, company) => {
    clearAppCaches();
    localStorage.setItem("token", accessToken);
    setUser(company);
    setToken(accessToken);
  };

  const logout = () => {
    if (token) {
      fetch(`${API}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => null);
    }
    clearAppCaches();
    localStorage.removeItem("token");
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-[#18181B] border-t-transparent"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename={process.env.PUBLIC_URL || "/"}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/phishing/simulation/:token" element={<PhishingTrainingPage />} />
          <Route path="/survey/:employeeId" element={<EmployeeSurvey />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/employees"
            element={
              <ProtectedRoute>
                <EmployeeManagement />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <AnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <ReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/:reportId"
            element={
              <ProtectedRoute>
                <ReportDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/billing"
            element={
              <ProtectedRoute>
                <BillingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/phishing"
            element={
              <ProtectedRoute>
                <PhishingSimulationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/standards-summary"
            element={
              <ProtectedRoute>
                <StandardsSummaryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings/security"
            element={
              <ProtectedRoute>
                <SecuritySettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/billing/callback"
            element={
              <ProtectedRoute>
                <PaymentCallbackPage />
              </ProtectedRoute>
            }
          />
        </Routes>
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

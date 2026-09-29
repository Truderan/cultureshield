import { useState } from "react";
import { Brand } from "@/components/Brand";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchWithRetry } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/App";
import { Shield, Mail, Lock, ArrowLeft, Loader2, KeyRound } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [mfaToken, setMfaToken] = useState("");
  const [mfaStep, setMfaStep] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setLoading(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        if (data.mfa_required) {
          setMfaToken(data.mfa_token);
          setMfaStep(true);
          toast.success("Enter your authenticator code to continue.");
        } else {
          login(data.access_token, data.company);
          toast.success("Welcome back!");
          navigate(data.mfa_setup_required ? "/settings/security" : "/dashboard", {
            state: data.mfa_setup_required ? { enforceSetup: true } : null,
          });
        }
      } else {
        toast.error(data.detail || "Login failed");
      }
    } catch (error) {
      toast.error("Unable to reach the server. Please refresh and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyMfa = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/mfa/verify-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mfa_token: mfaToken, code: verificationCode }),
      });

      if (!response.ok) {
        throw new Error(data.detail || "Verification failed");
      }

      login(data.access_token, data.company);
      toast.success("Verification successful.");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error.message || "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFFFFF] via-[#e0f2fe] to-[#FFFFFF] flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Back Link */}
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-zinc-600 hover:text-[#18181B] mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        {/* Login Card */}
        <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-xl border border-white/50 p-8">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <Brand size="lg" className="mb-4" />
            <h1 className="text-2xl font-bold text-[#18181B] ">
              Welcome Back
            </h1>
            <p className="text-zinc-600 mt-1">Sign in to your CultureShield account</p>
          </div>

          {!mfaStep ? (
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-zinc-700">
                Email Address
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-zinc-400" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="pl-10 h-12 border-zinc-300 focus:border-[#00A8E8] focus:ring-[#00A8E8]"
                  data-testid="login-email-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-zinc-700">
                Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-zinc-400" />
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-10 h-12 border-zinc-300 focus:border-[#00A8E8] focus:ring-[#00A8E8]"
                  data-testid="login-password-input"
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-12 bg-[#18181B] hover:bg-[#000000] text-white text-base font-medium"
              disabled={loading}
              data-testid="login-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
          ) : (
          <form onSubmit={handleVerifyMfa} className="space-y-5" data-testid="login-mfa-form">
            <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-600">
              Enter the 6-digit code from your authenticator app. You can also use a one-time backup code.
            </div>
            <div className="space-y-2">
              <Label htmlFor="mfa-code" className="text-zinc-700">Verification code</Label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-400" />
                <Input id="mfa-code" value={verificationCode} onChange={(event) => setVerificationCode(event.target.value)} placeholder="123456 or backup code" className="h-12 pl-10" data-testid="login-mfa-code-input" />
              </div>
            </div>
            <Button type="submit" className="w-full h-12 bg-[#18181B] hover:bg-[#000000] text-white" disabled={loading} data-testid="login-mfa-submit-btn">
              {loading ? <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Verifying...</> : "Verify and sign in"}
            </Button>
            <Button type="button" variant="outline" className="w-full h-12 border-zinc-300" onClick={() => { setMfaStep(false); setVerificationCode(""); setMfaToken(""); }} data-testid="login-mfa-back-btn">
              Back to password login
            </Button>
          </form>
          )}

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-white text-zinc-500">New to CultureShield?</span>
            </div>
          </div>

          {/* Register Link */}
          <Link to="/register">
            <Button
              variant="outline"
              className="w-full h-12 border-2 border-[#00A8E8] text-[#00A8E8] hover:bg-[#00A8E8] hover:text-white"
              data-testid="login-register-link"
            >
              Create an Account
            </Button>
          </Link>
          <Link to="/forgot-password" className="mt-4 block text-center text-sm font-medium text-[#00A8E8] hover:underline" data-testid="forgot-password-link">
            Forgot your password?
          </Link>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-zinc-500 mt-6">
          Protected by enterprise-grade security <Shield className="inline w-4 h-4 ml-1" />
        </p>
      </motion.div>
    </div>
  );
};

export default LoginPage;

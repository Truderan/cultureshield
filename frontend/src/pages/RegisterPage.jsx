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
import { Shield, Building2, Mail, Lock, ArrowLeft, Loader2, CheckCircle } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RegisterPage = () => {
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    
    if (!companyName || !email || !password || !confirmPassword) {
      toast.error("Please fill in all fields");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (password.length < 10) {
      toast.error("Password must be at least 10 characters");
      return;
    }

    setLoading(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName,
          email,
          password,
        }),
      });

      if (response.ok) {
        login(data.access_token, data.company);
        toast.success("Account created successfully!");
        navigate("/settings/security", { state: { enforceSetup: true } });
      } else {
        toast.error(data.detail || "Registration failed");
      }
    } catch (error) {
      toast.error("Unable to reach the server. Please refresh and try again.");
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

        {/* Register Card */}
        <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-xl border border-white/50 p-8">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <Brand size="lg" className="mb-4" />
            <h1 className="text-2xl font-bold text-[#18181B] ">
              Create Account
            </h1>
            <p className="text-zinc-600 mt-1">Start your cybersecurity culture journey</p>
          </div>

          {/* Features */}
          <div className="bg-zinc-50 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-sm text-zinc-600">
              <CheckCircle className="w-4 h-4 text-[#2ECC71]" />
              Free culture assessment
            </div>
            <div className="flex items-center gap-2 text-sm text-zinc-600 mt-2">
              <CheckCircle className="w-4 h-4 text-[#2ECC71]" />
              AI-powered insights
            </div>
            <div className="flex items-center gap-2 text-sm text-zinc-600 mt-2">
              <CheckCircle className="w-4 h-4 text-[#2ECC71]" />
              Up to 5 employees on the free plan
            </div>
            <div className="flex items-center gap-2 text-sm text-zinc-600 mt-2">
              <CheckCircle className="w-4 h-4 text-[#2ECC71]" />
              MFA setup recommended for every admin account
            </div>
          </div>

          {/* Register Form */}
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="companyName" className="text-zinc-700">
                Company Name
              </Label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-zinc-400" />
                <Input
                  id="companyName"
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Acme Corporation"
                  className="pl-10 h-12 border-zinc-300 focus:border-[#00A8E8] focus:ring-[#00A8E8]"
                  data-testid="register-company-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className="text-zinc-700">
                Work Email
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
                  data-testid="register-email-input"
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
                  data-testid="register-password-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-zinc-700">
                Confirm Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-zinc-400" />
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-10 h-12 border-zinc-300 focus:border-[#00A8E8] focus:ring-[#00A8E8]"
                  data-testid="register-confirm-password-input"
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-12 bg-[#18181B] hover:bg-[#000000] text-white text-base font-medium mt-2"
              disabled={loading}
              data-testid="register-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Creating account...
                </>
              ) : (
                "Create Account"
              )}
            </Button>
          </form>

          {/* Login Link */}
          <p className="text-center text-sm text-zinc-600 mt-6">
            Already have an account?{" "}
            <Link to="/login" className="text-[#00A8E8] hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-zinc-500 mt-6">
          Protected by enterprise-grade security <Shield className="inline w-4 h-4 ml-1" />
        </p>
      </motion.div>
    </div>
  );
};

export default RegisterPage;

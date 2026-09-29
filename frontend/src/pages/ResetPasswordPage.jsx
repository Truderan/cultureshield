import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Loader2, Lock, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchWithRetry } from "@/lib/api";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(true);
  const [isValidToken, setIsValidToken] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setValidating(false);
        return;
      }

      try {
        const { data } = await fetchWithRetry(`${API}/auth/reset-password/validate?token=${encodeURIComponent(token)}`);
        setIsValidToken(Boolean(data.valid));
      } catch {
        setIsValidToken(false);
      } finally {
        setValidating(false);
      }
    };

    validateToken();
  }, [token]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      if (!response.ok) {
        throw new Error(data.detail || "Unable to reset password.");
      }

      toast.success(data.message || "Password reset successfully.");
      setIsComplete(true);
    } catch (error) {
      toast.error(error.message || "Unable to reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFFFFF] via-[#e0f2fe] to-[#FFFFFF] flex items-center justify-center p-6" data-testid="reset-password-page">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <Link to="/login" className="mb-8 inline-flex items-center gap-2 text-zinc-600 hover:text-[#18181B]" data-testid="reset-password-back-link">
          <ArrowLeft className="h-4 w-4" /> Back to login
        </Link>
        <div className="rounded-2xl border border-white/50 bg-white/80 p-8 shadow-xl backdrop-blur-md">
          <div className="mb-8 text-center">
            <h1 className=" text-2xl font-bold text-[#18181B]">Create a new password</h1>
            <p className="mt-2 text-zinc-600">Use a strong password with upper/lowercase letters, numbers, and symbols.</p>
          </div>

          {validating ? (
            <div className="flex items-center justify-center py-12 text-zinc-500" data-testid="reset-password-validating-state">
              <Loader2 className="mr-2 h-5 w-5 animate-spin text-[#00A8E8]" /> Validating reset link...
            </div>
          ) : !isValidToken ? (
            <div className="rounded-2xl bg-red-50 p-5 text-sm text-red-700" data-testid="reset-password-invalid-token-state">
              This password reset link is invalid or has expired.
            </div>
          ) : isComplete ? (
            <div className="space-y-4 rounded-2xl bg-zinc-50 p-5 text-sm text-zinc-600" data-testid="reset-password-success-state">
              <p>Your password has been updated successfully.</p>
              <Link to="/login" data-testid="reset-password-login-link">
                <Button className="w-full bg-[#18181B] text-white hover:bg-[#000000]">Return to login</Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="new-password">New password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-400" />
                  <Input id="new-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="h-12 pl-10" data-testid="reset-password-new-input" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm-new-password">Confirm password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-400" />
                  <Input id="confirm-new-password" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="h-12 pl-10" data-testid="reset-password-confirm-input" />
                </div>
              </div>
              <Button type="submit" className="h-12 w-full bg-[#18181B] text-white hover:bg-[#000000]" disabled={loading} data-testid="reset-password-submit-button">
                {loading ? <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Updating password...</> : "Update password"}
              </Button>
            </form>
          )}
        </div>
        <p className="mt-6 text-center text-sm text-zinc-500">Protected by enterprise-grade security <Shield className="ml-1 inline h-4 w-4" /></p>
      </motion.div>
    </div>
  );
}
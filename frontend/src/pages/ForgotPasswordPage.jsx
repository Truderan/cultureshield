import { useState } from "react";
import { Brand } from "@/components/Brand";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Loader2, Mail, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchWithRetry } from "@/lib/api";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const { data } = await fetchWithRetry(`${API}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setSubmitted(true);
      toast.success(data.message || "If an account exists, a reset link has been sent.");
    } catch {
      toast.error("Unable to process your request right now.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFFFFF] via-[#e0f2fe] to-[#FFFFFF] flex items-center justify-center p-6" data-testid="forgot-password-page">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <Link to="/login" className="mb-8 inline-flex items-center gap-2 text-zinc-600 hover:text-[#18181B]" data-testid="forgot-password-back-link">
          <ArrowLeft className="h-4 w-4" /> Back to login
        </Link>
        <div className="rounded-2xl border border-white/50 bg-white/80 p-8 shadow-xl backdrop-blur-md">
          <div className="mb-8 flex flex-col items-center text-center">
            <Brand size="lg" className="mb-4" />
            <h1 className=" text-2xl font-bold text-[#18181B]">Reset your password</h1>
            <p className="mt-2 text-zinc-600">We’ll email you a secure reset link that expires in 20 minutes.</p>
          </div>

          {submitted ? (
            <div className="rounded-2xl bg-zinc-50 p-5 text-sm text-zinc-600" data-testid="forgot-password-success-panel">
              If an account exists for <strong>{email}</strong>, a password reset email has been sent.
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="reset-email">Email address</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-400" />
                  <Input id="reset-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="h-12 pl-10" placeholder="you@company.com" data-testid="forgot-password-email-input" />
                </div>
              </div>

              <Button type="submit" className="h-12 w-full bg-[#18181B] text-white hover:bg-[#000000]" disabled={loading} data-testid="forgot-password-submit-button">
                {loading ? <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Sending link...</> : "Send reset link"}
              </Button>
            </form>
          )}
        </div>
        <p className="mt-6 text-center text-sm text-zinc-500">Protected by enterprise-grade security <Shield className="ml-1 inline h-4 w-4" /></p>
      </motion.div>
    </div>
  );
}
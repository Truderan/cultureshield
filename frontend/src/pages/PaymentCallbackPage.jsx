import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/App";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PaymentCallbackPage() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const [message, setMessage] = useState("Verifying your Paystack payment...");

  useEffect(() => {
    const verifyPayment = async () => {
      const reference = searchParams.get("reference") || searchParams.get("trxref");

      if (!reference || !token) {
        setMessage("Missing payment reference. Returning to billing.");
        window.location.href = `${process.env.PUBLIC_URL}/billing?payment=failed`;
        return;
      }

      try {
        const response = await fetch(`${API}/billing/checkout/verify/${reference}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();

        if (!response.ok || data.status !== "success") {
          throw new Error(data.detail || data.message || "Payment verification failed");
        }

        toast.success("Payment verified successfully.");
        setMessage("Payment confirmed. Opening your billing portal...");
        window.location.href = `${process.env.PUBLIC_URL}/billing?payment=success`;
      } catch (error) {
        toast.error(error.message || "Unable to verify payment.");
        setMessage("Verification failed. Returning to billing...");
        window.location.href = `${process.env.PUBLIC_URL}/billing?payment=failed`;
      }
    };

    verifyPayment();
  }, [searchParams, token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6" data-testid="billing-callback-page">
      <div className="w-full max-w-lg rounded-[28px] border border-zinc-200 bg-white p-10 text-center shadow-lg">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-[#18181B]/10 text-[#18181B]">
          <ShieldCheck className="h-8 w-8" />
        </div>
        <h1 className=" text-3xl font-bold text-[#18181B]" data-testid="billing-callback-heading">
          Finalizing your billing update
        </h1>
        <p className="mt-4 text-zinc-600" data-testid="billing-callback-message">
          {message}
        </p>
        <div className="mt-8 flex items-center justify-center gap-3 rounded-2xl bg-zinc-50 px-4 py-3 text-sm text-zinc-500" data-testid="billing-callback-loader">
          <Loader2 className="h-4 w-4 animate-spin text-[#00A8E8]" />
          Syncing your subscription, invoice, and payment method...
        </div>
      </div>
    </div>
  );
}
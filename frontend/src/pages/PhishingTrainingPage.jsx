import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchWithRetry } from "@/lib/api";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PhishingTrainingPage() {
  const { token } = useParams();
  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reporting, setReporting] = useState(false);

  useEffect(() => {
    const loadSimulation = async () => {
      try {
        const { response, data } = await fetchWithRetry(`${API}/phishing/simulations/${token}`);
        if (!response.ok) throw new Error(data.detail || "Simulation not found.");
        setSimulation(data);
      } catch (error) {
        toast.error(error.message || "Unable to load this simulation.");
      } finally {
        setLoading(false);
      }
    };
    loadSimulation();
  }, [token]);

  const handleReport = async () => {
    setReporting(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/phishing/simulations/${token}/report`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(data.detail || "Unable to submit report.");
      setSimulation((current) => ({ ...current, already_reported: true }));
      toast.success(data.message || "Report logged.");
    } catch (error) {
      toast.error(error.message || "Unable to report this simulation.");
    } finally {
      setReporting(false);
    }
  };

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-background" data-testid="phishing-training-loading"><Loader2 className="h-8 w-8 animate-spin text-[#00A8E8]" /></div>;
  }

  if (!simulation) {
    return <div className="flex min-h-screen items-center justify-center bg-background p-6 text-center text-zinc-500" data-testid="phishing-training-missing">This phishing simulation link is unavailable.</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFFFFF] via-[#e0f2fe] to-[#FFFFFF] px-6 py-10" data-testid="phishing-training-page">
      <div className="mx-auto max-w-4xl space-y-6">
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="rounded-[32px] bg-[#18181B] p-8 text-white">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm text-[#7DD3FC]">
            <ShieldAlert className="h-4 w-4" /> This was a CultureShield simulation
          </div>
          <h1 className=" text-4xl font-bold" data-testid="phishing-training-heading">Nice catch, {simulation.employee_name}</h1>
          <p className="mt-4 max-w-3xl text-zinc-200">You opened <strong>{simulation.campaign_name}</strong>, a safe internal phishing simulation for {simulation.company_name}. The click has been tracked so your team can coach safer habits without exposing anyone to real risk.</p>
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Card className="rounded-[28px] border-zinc-200" data-testid="phishing-training-red-flags-card">
            <CardHeader>
              <CardTitle className=" text-2xl text-[#18181B]">Why this message was risky</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-600">{simulation.scenario}</div>
              {simulation.red_flags.map((flag) => (
                <div key={flag} className="flex items-start gap-3 rounded-2xl border border-zinc-200 p-4" data-testid={`phishing-red-flag-${flag.replace(/\s+/g, "-").toLowerCase()}`}>
                  <AlertTriangle className="mt-0.5 h-4 w-4 text-red-600" />
                  <span className="text-sm text-zinc-600">{flag}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-[28px] border-zinc-200" data-testid="phishing-training-learning-card">
            <CardHeader>
              <CardTitle className=" text-2xl text-[#18181B]">How to respond better next time</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {simulation.learning_points.map((point) => (
                <div key={point} className="flex items-start gap-3 rounded-2xl border border-zinc-200 p-4" data-testid={`phishing-learning-point-${point.replace(/\s+/g, "-").toLowerCase().slice(0, 40)}`}>
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
                  <span className="text-sm text-zinc-600">{point}</span>
                </div>
              ))}
              <Button className="w-full bg-[#18181B] text-white hover:bg-[#000000]" onClick={handleReport} disabled={reporting || simulation.already_reported} data-testid="phishing-report-button">
                {simulation.already_reported ? "Already reported" : reporting ? "Reporting..." : "I would report this message"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
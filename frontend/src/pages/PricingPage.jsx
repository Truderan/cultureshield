import { useEffect, useMemo, useState } from "react";
import { Brand } from "@/components/Brand";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { CheckCircle, CreditCard, Shield, Sparkles } from "lucide-react";
import { useAuth } from "@/App";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PLAN_ORDER = ["free", "starter", "business", "pro", "pay_per_audit"];

const formatCurrency = (amount, currency) =>
  new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount || 0);

export default function PricingPage() {
  const { user } = useAuth();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const response = await fetch(`${API}/billing/plans?currency=NGN`);
        if (!response.ok) {
          throw new Error("Failed to load pricing");
        }
        setPlans(await response.json());
      } catch (error) {
        toast.error("Unable to load pricing plans right now.");
      } finally {
        setLoading(false);
      }
    };

    fetchPlans();
  }, []);

  const orderedPlans = useMemo(
    () => PLAN_ORDER.map((id) => plans.find((plan) => plan.id === id)).filter(Boolean),
    [plans]
  );

  return (
    <div className="min-h-screen bg-background" data-testid="pricing-page">
      <nav className="border-b border-zinc-200 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-3" data-testid="pricing-home-link">
            <Brand size="md" />
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/login" data-testid="pricing-login-link">
              <Button variant="ghost" className="text-[#18181B] hover:text-[#00A8E8]">
                Login
              </Button>
            </Link>
            <Link to={user ? "/billing" : "/register"} data-testid="pricing-primary-link">
              <Button className="bg-[#18181B] text-white hover:bg-[#000000]">
                {user ? "Open Billing" : "Get Started"}
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-14 max-w-3xl"
          >
            <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-[#00A8E8]/10 px-4 py-2 text-sm font-medium text-[#00A8E8]">
              <Sparkles className="h-4 w-4" />
              Pricing built for security-conscious teams
            </div>
            <h1 className=" text-4xl font-bold text-[#18181B] sm:text-5xl lg:text-6xl" data-testid="pricing-heading">
              Choose the CultureShield plan that matches your audit maturity.
            </h1>
            <p className="mt-5 max-w-2xl text-base text-zinc-600 md:text-lg" data-testid="pricing-subheading">
              Start free, move into recurring subscriptions as your team scales, or buy one-off audits when you need a quick security culture snapshot.
            </p>
          </motion.div>

          {loading ? (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3" data-testid="pricing-loading-state">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-80 rounded-3xl border border-zinc-200 bg-white/70" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-5" data-testid="pricing-plan-grid">
              {orderedPlans.map((plan) => {
                const isPopular = plan.id === "business";
                const buttonLabel = user ? "Choose in billing" : plan.id === "free" ? "Start free" : "Create account";

                return (
                  <Card
                    key={plan.id}
                    className={`relative flex h-full flex-col rounded-[28px] border p-0  transition-transform duration-200 hover:-translate-y-1 ${
                      isPopular ? "border-[#00A8E8] bg-[#18181B] text-white" : "border-zinc-200 bg-white"
                    }`}
                    data-testid={`pricing-plan-${plan.id}`}
                  >
                    {isPopular && (
                      <div className="absolute right-5 top-5 rounded-full bg-[#00A8E8] px-3 py-1 text-xs font-semibold text-white" data-testid="pricing-popular-badge">
                        Most Popular
                      </div>
                    )}
                    <CardHeader className="space-y-4 p-7">
                      <div className="flex items-center justify-between">
                        <CardTitle className={` text-2xl ${isPopular ? "text-white" : "text-[#18181B]"}`}>
                          {plan.name}
                        </CardTitle>
                        <CreditCard className={`h-5 w-5 ${isPopular ? "text-[#00A8E8]" : "text-zinc-400"}`} />
                      </div>
                      <div data-testid={`pricing-plan-price-${plan.id}`}>
                        <div className={` text-4xl font-bold ${isPopular ? "text-white" : "text-[#18181B]"}`}>
                          {formatCurrency(plan.display_price, plan.currency)}
                        </div>
                        <p className={`mt-2 text-sm ${isPopular ? "text-zinc-200" : "text-zinc-500"}`}>
                          {plan.interval === "one_time" ? "one-time purchase" : "per month"}
                        </p>
                        {plan.trial_days > 0 && (
                          <p className={`mt-2 text-sm font-medium ${isPopular ? "text-[#7DD3FC]" : "text-[#00A8E8]"}`} data-testid={`pricing-trial-${plan.id}`}>
                            Includes {plan.trial_days}-day trial window
                          </p>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="flex flex-1 flex-col justify-between gap-8 p-7 pt-0">
                      <div className="space-y-3">
                        {plan.features.map((feature) => (
                          <div key={feature} className="flex items-start gap-3" data-testid={`pricing-feature-${plan.id}-${feature.replace(/\s+/g, "-").toLowerCase()}`}>
                            <CheckCircle className={`mt-0.5 h-4 w-4 shrink-0 ${isPopular ? "text-[#7DD3FC]" : "text-[#2ECC71]"}`} />
                            <span className={`text-sm leading-relaxed ${isPopular ? "text-zinc-100" : "text-zinc-600"}`}>{feature}</span>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-3">
                        <div className={`rounded-2xl border px-4 py-3 text-sm ${isPopular ? "border-white/10 bg-white/10 text-zinc-100" : "border-zinc-200 bg-zinc-50 text-zinc-600"}`}>
                          {plan.max_employees === -1 ? "Unlimited employees" : `Up to ${plan.max_employees} employees`}
                        </div>
                        <Link to={user ? `/billing?plan=${plan.id}` : "/register"} data-testid={`pricing-cta-${plan.id}`}>
                          <Button className={`h-12 w-full ${isPopular ? "bg-white text-[#18181B] hover:bg-zinc-100" : "bg-[#18181B] text-white hover:bg-[#000000]"}`}>
                            {buttonLabel}
                          </Button>
                        </Link>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          <div className="mt-14 grid gap-6 rounded-[28px] border border-zinc-200 bg-white p-8 lg:grid-cols-[1.4fr_1fr] lg:items-center" data-testid="pricing-footer-panel">
            <div>
              <h2 className=" text-3xl font-bold text-[#18181B]">Secure hosted checkout. Mocked billing notifications. Clear upgrade paths.</h2>
              <p className="mt-3 text-zinc-600">
                CultureShield uses Paystack-hosted checkout for payment capture, stores only provider references, and keeps transactional emails mocked to console logs in this environment.
              </p>
            </div>
            <div className="rounded-[24px] bg-[#18181B] p-6 text-white" data-testid="pricing-assurance-card">
              <div className="mb-4 flex items-center gap-3 text-sm uppercase tracking-[0.2em] text-[#7DD3FC]">
                <Shield className="h-4 w-4" />
                Billing assurance
              </div>
              <ul className="space-y-3 text-sm text-zinc-200">
                <li>• Recurring subscriptions for Starter, Business, and Pro</li>
                <li>• One-time audits for pay-as-you-go use cases</li>
                <li>• Business and Pro include phishing simulation drills</li>
                <li>• Coupons, proration, invoice history, and billing intelligence</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
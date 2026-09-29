import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Loader2, Shield, Sparkles, TrendingUp } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/App";
import { InstallAppButton } from "@/components/InstallAppButton";
import { EmailActivityPanel } from "@/components/EmailActivityPanel";
import { AppShell } from "@/components/AppShell";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PLAN_ORDER = ["free", "starter", "business", "pro", "pay_per_audit"];

const formatCurrency = (amount, currency = "USD") =>
  new Intl.NumberFormat(currency === "NGN" ? "en-NG" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount || 0);

const MetricCard = ({ label, value, testId }) => (
  <Card className="rounded-[24px] border-zinc-200 " data-testid={testId}>
    <CardContent className="p-6">
      <p className="text-sm uppercase tracking-[0.18em] text-zinc-400">{label}</p>
      <p className="mt-3  text-3xl font-bold text-[#18181B]">{value}</p>
    </CardContent>
  </Card>
);

export default function BillingPage() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [plans, setPlans] = useState([]);
  const [billingInfo, setBillingInfo] = useState(null);
  const [adminStats, setAdminStats] = useState(null);
  const [emailActivity, setEmailActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checkoutPlanId, setCheckoutPlanId] = useState(null);
  const [changePlanId, setChangePlanId] = useState(null);
  const [exportingEmails, setExportingEmails] = useState(false);
  const [couponCode, setCouponCode] = useState("");
  const activeTab = searchParams.get("view") || "portal";

  useEffect(() => {
    const paymentStatus = searchParams.get("payment");
    if (paymentStatus === "success") {
      toast.success("Your billing update has been completed.");
    }
    if (paymentStatus === "failed") {
      toast.error("We could not complete that payment flow.");
    }
  }, [searchParams]);

  useEffect(() => {
    const fetchBillingData = async () => {
      try {
        const [plansResult, billingResult, adminResult, emailResult] = await Promise.allSettled([
          fetch(`${API}/billing/plans?currency=NGN`),
          fetch(`${API}/billing/info`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${API}/billing/admin/dashboard`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${API}/billing/admin/email-activity`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);

        if (plansResult.status === "fulfilled" && plansResult.value.ok) {
          setPlans(await plansResult.value.json());
        }

        if (billingResult.status === "fulfilled" && billingResult.value.ok) {
          setBillingInfo(await billingResult.value.json());
        } else {
          throw new Error("Failed to load billing portal");
        }

        if (adminResult.status === "fulfilled" && adminResult.value.ok) {
          setAdminStats(await adminResult.value.json());
        }

        if (emailResult.status === "fulfilled" && emailResult.value.ok) {
          setEmailActivity(await emailResult.value.json());
        }
      } catch (error) {
        toast.error(error.message || "Unable to load billing data.");
      } finally {
        setLoading(false);
      }
    };

    fetchBillingData();
  }, [token]);

  const orderedPlans = useMemo(
    () => PLAN_ORDER.map((id) => plans.find((plan) => plan.id === id)).filter(Boolean),
    [plans]
  );

  const setView = (view) => {
    const next = new URLSearchParams(searchParams);
    next.set("view", view);
    next.delete("payment");
    setSearchParams(next);
  };

  const refreshBilling = async () => {
    const [billingResponse, adminResponse, emailResponse] = await Promise.allSettled([
      fetch(`${API}/billing/info`, { headers: { Authorization: `Bearer ${token}` } }),
      fetch(`${API}/billing/admin/dashboard`, { headers: { Authorization: `Bearer ${token}` } }),
      fetch(`${API}/billing/admin/email-activity`, { headers: { Authorization: `Bearer ${token}` } }),
    ]);

    if (billingResponse.status === "fulfilled" && billingResponse.value.ok) {
      setBillingInfo(await billingResponse.value.json());
    }
    if (adminResponse.status === "fulfilled" && adminResponse.value.ok) {
      setAdminStats(await adminResponse.value.json());
    }
    if (emailResponse.status === "fulfilled" && emailResponse.value.ok) {
      setEmailActivity(await emailResponse.value.json());
    }
  };

  const handleDownloadEmailHistory = async () => {
    try {
      setExportingEmails(true);
      const response = await fetch(`${API}/billing/admin/email-activity/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error("Unable to export email history");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${user?.company_name?.replace(/\s+/g, "-").toLowerCase() || "cultureshield"}-email-history.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Email history downloaded.");
    } catch (error) {
      toast.error(error.message || "Unable to download email history.");
    } finally {
      setExportingEmails(false);
    }
  };

  const handleCheckout = async (plan) => {
    try {
      setCheckoutPlanId(plan.id);
      const endpoint = plan.interval === "one_time" ? "audit" : "subscribe";
      const response = await fetch(`${API}/billing/checkout/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          plan_id: plan.id,
          coupon_code: couponCode || undefined,
          callback_url: `${window.location.origin}/billing/callback`,
          currency: "NGN",
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to initialize checkout");
      }

      if (data.is_free) {
        toast.success("Your plan has been updated.");
        await refreshBilling();
        return;
      }

      window.location.href = data.authorization_url;
    } catch (error) {
      toast.error(error.message || "Unable to start checkout.");
    } finally {
      setCheckoutPlanId(null);
    }
  };

  const handleChangePlan = async (planId) => {
    try {
      setChangePlanId(planId);
      const response = await fetch(`${API}/billing/subscription/change-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ new_plan_id: planId, prorate: true }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to change plan");
      }

      toast.success(`Plan updated. Proration: ${formatCurrency(data.proration_amount, "USD")}`);
      await refreshBilling();
    } catch (error) {
      toast.error(error.message || "Unable to update plan.");
    } finally {
      setChangePlanId(null);
    }
  };

  const handleSubscriptionAction = async (endpoint, body, successMessage) => {
    try {
      const response = await fetch(`${API}/billing/subscription/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to update subscription");
      }

      toast.success(successMessage);
      await refreshBilling();
    } catch (error) {
      toast.error(error.message || "Unable to update subscription.");
    }
  };

  const handleDeleteMethod = async (methodId) => {
    try {
      const response = await fetch(`${API}/billing/payment-methods/${methodId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to remove payment method");
      }

      toast.success(data.message || "Payment method removed.");
      await refreshBilling();
    } catch (error) {
      toast.error(error.message || "Unable to remove payment method.");
    }
  };

  const openPortal = async () => {
    try {
      const response = await fetch(`${API}/billing/portal`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to open billing portal");
      }
      navigate(data.portal_url);
      setView("portal");
    } catch (error) {
      toast.error(error.message || "Unable to open the portal.");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background" data-testid="billing-loading-state">
        <Loader2 className="h-8 w-8 animate-spin text-[#00A8E8]" />
      </div>
    );
  }

  const currentPlanId = billingInfo?.plan_details?.id || billingInfo?.subscription?.plan_id || "free";
  const statusLabel = billingInfo?.subscription?.status || "free";
  const intelligenceTitle = (adminStats?.total_customers || 0) <= 1 ? "Account health" : "At-risk customers";

  return (
    <AppShell current="billing" testId="billing-main-content" rootTestId="billing-page">
<motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
          <section className="grid gap-6 rounded-[32px] bg-[#18181B] p-8 text-white lg:grid-cols-[1.3fr_0.7fr]" data-testid="billing-hero-panel">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm text-[#7DD3FC]">
                <Sparkles className="h-4 w-4" /> Revenue controls and subscription intelligence
              </div>
              <h1 className=" text-4xl font-bold sm:text-5xl" data-testid="billing-heading">Billing & subscription control center</h1>
              <p className="mt-4 max-w-2xl text-zinc-200" data-testid="billing-subheading">
                Manage your plan, review invoices, keep payment methods healthy, and monitor expansion or churn signals from one portal.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-[24px] bg-white/10 p-5" data-testid="current-plan-card">
                <p className="text-sm uppercase tracking-[0.18em] text-[#7DD3FC]">Current plan</p>
                <p className="mt-3  text-3xl font-bold" data-testid="current-plan-name">{billingInfo?.plan_details?.name || "Free"}</p>
                <p className="mt-2 text-sm text-zinc-200" data-testid="current-plan-status">Status: {statusLabel}</p>
              </div>
              <div className="rounded-[24px] bg-white/10 p-5" data-testid="next-billing-card">
                <p className="text-sm uppercase tracking-[0.18em] text-[#7DD3FC]">Next billing</p>
                <p className="mt-3  text-2xl font-bold" data-testid="next-billing-date">
                  {billingInfo?.next_billing_date ? new Date(billingInfo.next_billing_date).toLocaleDateString() : "No scheduled renewal"}
                </p>
                <p className="mt-2 text-sm text-zinc-200">Invoices and card updates live in the portal tab.</p>
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
            <Card className="rounded-[28px] border-zinc-200" data-testid="billing-plan-summary-card">
              <CardContent className="flex flex-col gap-4 p-6 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.18em] text-zinc-400">Recommendation</p>
                  <h2 className="mt-2  text-3xl font-bold text-[#18181B]" data-testid="billing-recommendation-heading">
                    {billingInfo?.recommended_plan ? `Consider ${billingInfo.recommended_plan}` : "Your current plan fits your usage"}
                  </h2>
                  <p className="mt-2 text-zinc-600" data-testid="billing-usage-summary">
                    {billingInfo?.usage_this_period?.audits || 0} audits • {billingInfo?.usage_this_period?.employees || 0} employees • {billingInfo?.usage_this_period?.surveys || 0} surveys this period.
                  </p>
                </div>
                <div className="space-y-3">
                  <Input value={couponCode} onChange={(event) => setCouponCode(event.target.value.toUpperCase())} placeholder="Coupon code" className="h-11 border-zinc-300" data-testid="billing-coupon-input" />
                  <Button className="w-full bg-[#00A8E8] text-white hover:bg-[#008dc2]" onClick={openPortal} data-testid="open-billing-portal-button">
                    Open portal view
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-[28px] border-zinc-200 bg-white" data-testid="billing-navigation-card">
              <CardHeader className="pb-3">
                <CardTitle className=" text-xl text-[#18181B]">Quick actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button variant="outline" className="w-full justify-start border-zinc-300" onClick={() => setView("plans")} data-testid="billing-view-plans-button">View plans</Button>
                <Button variant="outline" className="w-full justify-start border-zinc-300" onClick={() => setView("portal")} data-testid="billing-view-portal-button">Invoices & payment methods</Button>
                <Button variant="outline" className="w-full justify-start border-zinc-300" onClick={() => setView("intelligence")} data-testid="billing-view-intelligence-button">Revenue intelligence</Button>
                <Link to="/settings/security" data-testid="billing-security-link">
                  <Button variant="outline" className="w-full justify-start border-zinc-300">Security settings</Button>
                </Link>
                <InstallAppButton className="w-full justify-start border-zinc-300" testId="billing-download-app-button" />
              </CardContent>
            </Card>
          </section>

          <Tabs value={activeTab} onValueChange={setView} className="space-y-6">
            <TabsList className="grid w-full max-w-xl grid-cols-3 bg-white p-1" data-testid="billing-tabs">
              <TabsTrigger value="plans" data-testid="billing-tab-plans">Plans</TabsTrigger>
              <TabsTrigger value="portal" data-testid="billing-tab-portal">Portal</TabsTrigger>
              <TabsTrigger value="intelligence" data-testid="billing-tab-intelligence">Intelligence</TabsTrigger>
            </TabsList>

            <TabsContent value="plans" className="space-y-6" data-testid="billing-tab-content-plans">
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
                {orderedPlans.map((plan) => {
                  const isCurrentPlan = currentPlanId === plan.id;
                  const canChangeDirectly = billingInfo?.subscription && currentPlanId !== "free" && plan.interval === "monthly" && plan.id !== currentPlanId;

                  return (
                    <Card key={plan.id} className={`rounded-[28px] border p-0  ${plan.id === "business" ? "border-[#00A8E8] bg-[#18181B] text-white" : "border-zinc-200 bg-white"}`} data-testid={`billing-plan-${plan.id}`}>
                      <CardHeader className="space-y-4 p-6">
                        <div className="flex items-center justify-between">
                          <CardTitle className={` text-2xl ${plan.id === "business" ? "text-white" : "text-[#18181B]"}`}>{plan.name}</CardTitle>
                          {isCurrentPlan && <span className={`rounded-full px-3 py-1 text-xs font-semibold ${plan.id === "business" ? "bg-white/15 text-[#7DD3FC]" : "bg-[#18181B]/5 text-[#18181B]"}`} data-testid={`billing-current-badge-${plan.id}`}>Current</span>}
                        </div>
                        <div>
                          <p className={` text-4xl font-bold ${plan.id === "business" ? "text-white" : "text-[#18181B]"}`} data-testid={`billing-plan-price-${plan.id}`}>{formatCurrency(plan.display_price, plan.currency)}</p>
                          <p className={`mt-2 text-sm ${plan.id === "business" ? "text-zinc-200" : "text-zinc-500"}`}>{plan.interval === "one_time" ? "One-time audit" : "per month"}</p>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-5 p-6 pt-0">
                        <div className="space-y-3">
                          {plan.features.map((feature) => (
                            <div key={feature} className="flex items-start gap-3 text-sm" data-testid={`billing-plan-feature-${plan.id}-${feature.replace(/\s+/g, "-").toLowerCase()}`}>
                              <Shield className={`mt-0.5 h-4 w-4 shrink-0 ${plan.id === "business" ? "text-[#7DD3FC]" : "text-[#00A8E8]"}`} />
                              <span className={plan.id === "business" ? "text-zinc-100" : "text-zinc-600"}>{feature}</span>
                            </div>
                          ))}
                        </div>
                        <div className={`rounded-2xl px-4 py-3 text-sm ${plan.id === "business" ? "bg-white/10 text-zinc-100" : "bg-zinc-50 text-zinc-600"}`}>
                          {plan.max_employees === -1 ? "Unlimited employees" : `Up to ${plan.max_employees} employees`}
                        </div>
                        <Button
                          className={`h-12 w-full ${plan.id === "business" ? "bg-white text-[#18181B] hover:bg-zinc-100" : "bg-[#18181B] text-white hover:bg-[#000000]"}`}
                          disabled={isCurrentPlan || checkoutPlanId === plan.id || changePlanId === plan.id}
                          onClick={() => (canChangeDirectly ? handleChangePlan(plan.id) : handleCheckout(plan))}
                          data-testid={`billing-plan-action-${plan.id}`}
                        >
                          {checkoutPlanId === plan.id || changePlanId === plan.id ? (
                            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing...</>
                          ) : isCurrentPlan ? (
                            "Current plan"
                          ) : canChangeDirectly ? (
                            "Switch with proration"
                          ) : (
                            "Open hosted checkout"
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </TabsContent>

            <TabsContent value="portal" className="space-y-6" data-testid="billing-tab-content-portal">
              <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
                <Card className="rounded-[28px] border-zinc-200" data-testid="subscription-management-card">
                  <CardHeader>
                    <CardTitle className=" text-2xl text-[#18181B]">Subscription management</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="rounded-2xl bg-zinc-50 p-4" data-testid="subscription-status-panel">
                      <p className="text-sm text-zinc-500">Plan</p>
                      <p className="mt-1  text-3xl font-bold text-[#18181B]">{billingInfo?.plan_details?.name || "Free"}</p>
                      <p className="mt-2 text-sm text-zinc-600">Status: {statusLabel}</p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Button variant="outline" className="border-zinc-300" onClick={() => handleSubscriptionAction("cancel", { cancel_immediately: false }, "Your subscription will cancel at the period end.")} data-testid="cancel-subscription-button">
                        Cancel at period end
                      </Button>
                      <Button className="bg-[#18181B] text-white hover:bg-[#000000]" onClick={() => handleSubscriptionAction("resume", null, "Your subscription has been resumed.")} data-testid="resume-subscription-button">
                        Resume subscription
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <Card className="rounded-[28px] border-zinc-200" data-testid="payment-methods-card">
                  <CardHeader>
                    <CardTitle className=" text-2xl text-[#18181B]">Payment methods</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {billingInfo?.payment_methods?.length ? (
                      billingInfo.payment_methods.map((method) => (
                        <div key={method.id} className="flex items-center justify-between rounded-2xl border border-zinc-200 p-4" data-testid={`payment-method-${method.id}`}>
                          <div>
                            <p className="font-semibold text-[#18181B]">{method.card_type || "Saved card"} •••• {method.last4 || "----"}</p>
                            <p className="text-sm text-zinc-500">{method.bank || "Paystack authorization"}</p>
                          </div>
                          <Button variant="ghost" className="text-red-600 hover:bg-red-50 hover:text-red-700" onClick={() => handleDeleteMethod(method.id)} data-testid={`delete-payment-method-${method.id}`}>
                            Remove
                          </Button>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500" data-testid="payment-method-empty-state">
                        No saved payment methods yet. Your first successful Paystack checkout will store a reusable provider authorization.
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <Card className="rounded-[28px] border-zinc-200" data-testid="invoice-history-card">
                <CardHeader>
                  <CardTitle className=" text-2xl text-[#18181B]">Invoices</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {billingInfo?.invoices?.length ? (
                    billingInfo.invoices.map((invoice) => (
                      <div key={invoice.id} className="grid gap-4 rounded-2xl border border-zinc-200 p-4 md:grid-cols-[1fr_auto_auto_auto] md:items-center" data-testid={`invoice-row-${invoice.id}`}>
                        <div>
                          <p className="font-semibold text-[#18181B]">{invoice.description}</p>
                          <p className="text-sm text-zinc-500">{new Date(invoice.created_at).toLocaleString()}</p>
                        </div>
                        <p className="font-semibold text-zinc-700" data-testid={`invoice-amount-${invoice.id}`}>{formatCurrency(invoice.amount_paid || invoice.amount_due, invoice.currency)}</p>
                        <p className="text-sm capitalize text-zinc-500">{invoice.status}</p>
                        {invoice.hosted_url ? (
                          <a href={invoice.hosted_url} target="_blank" rel="noreferrer" className="text-sm font-medium text-[#00A8E8]" data-testid={`invoice-link-${invoice.id}`}>Open receipt</a>
                        ) : (
                          <span className="text-sm text-zinc-400">No hosted receipt</span>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500" data-testid="invoice-empty-state">
                      Invoices will appear here once you complete your first billing event.
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="intelligence" className="space-y-6" data-testid="billing-tab-content-intelligence">
              <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                <MetricCard label="MRR" value={formatCurrency(adminStats?.mrr, "USD")} testId="billing-mrr-card" />
                <MetricCard label="ARR" value={formatCurrency(adminStats?.arr, "USD")} testId="billing-arr-card" />
                <MetricCard label="Churn rate" value={`${adminStats?.churn_rate || 0}%`} testId="billing-churn-card" />
              </div>

              <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
                <Card className="rounded-[28px] border-zinc-200" data-testid="billing-revenue-by-plan-card">
                  <CardHeader>
                    <CardTitle className=" text-2xl text-[#18181B]">Revenue by plan</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {Object.entries(adminStats?.revenue_by_plan || {}).map(([planName, revenue]) => (
                      <div key={planName} className="flex items-center justify-between rounded-2xl bg-zinc-50 px-4 py-3" data-testid={`revenue-row-${planName.replace(/\s+/g, "-").toLowerCase()}`}>
                        <span className="text-zinc-600">{planName}</span>
                        <span className="font-semibold text-[#18181B]">{formatCurrency(revenue, "USD")}</span>
                      </div>
                    ))}
                    {!Object.keys(adminStats?.revenue_by_plan || {}).length && (
                      <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500">Revenue data will populate as subscriptions become active.</div>
                    )}
                  </CardContent>
                </Card>

                <Card className="rounded-[28px] border-zinc-200" data-testid="billing-at-risk-card">
                  <CardHeader>
                    <CardTitle className=" text-2xl text-[#18181B]">{intelligenceTitle}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {adminStats?.at_risk_customers?.length ? (
                      adminStats.at_risk_customers.map((customer) => (
                        <div key={customer.company_id} className="rounded-2xl border border-zinc-200 p-4" data-testid={`at-risk-customer-${customer.company_id}`}>
                          <div className="flex items-center justify-between gap-4">
                            <div>
                              <p className="font-semibold text-[#18181B]">{customer.company_name}</p>
                              <p className="text-sm text-zinc-500">Risk: {customer.risk_level} • Score {customer.risk_score}</p>
                            </div>
                            <TrendingUp className="h-5 w-5 text-[#F39C12]" />
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500" data-testid="billing-account-health-empty-state">No account health risks detected yet.</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <EmailActivityPanel activity={emailActivity} onDownload={handleDownloadEmailHistory} downloading={exportingEmails} />
            </TabsContent>
          </Tabs>
        </motion.div>
      </AppShell>
  );
}
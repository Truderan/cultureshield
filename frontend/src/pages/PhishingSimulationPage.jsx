import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Loader2, Mail, ShieldAlert, Send, Users } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { AppShell } from "@/components/AppShell";
import { fetchWithRetry } from "@/lib/api";
import { useAuth } from "@/App";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MetricCard = ({ title, value, icon: Icon, testId }) => (
  <Card className="rounded-[24px] border-zinc-200" data-testid={testId}>
    <CardContent className="flex items-center justify-between p-5">
      <div>
        <p className="text-sm uppercase tracking-[0.16em] text-zinc-400">{title}</p>
        <p className="mt-2  text-3xl font-bold text-[#18181B]">{value}</p>
      </div>
      <div className="rounded-2xl bg-[#18181B]/5 p-3 text-[#18181B]">
        <Icon className="h-5 w-5" />
      </div>
    </CardContent>
  </Card>
);

export default function PhishingSimulationPage() {
  const { token, user, logout } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState("");
  const [campaignName, setCampaignName] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState([]);
  const [accessState, setAccessState] = useState({ checked: false, allowed: true, message: "" });
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);

  const loadData = async () => {
    const accessResult = await fetchWithRetry(`${API}/billing/access/phishing_simulation`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!accessResult.response.ok || !accessResult.data.allowed) {
      setAccessState({ checked: true, allowed: false, message: accessResult.data.message || "Upgrade to access phishing simulations." });
      setTemplates([]);
      setEmployees([]);
      setCampaigns([]);
      return;
    }

    setAccessState({ checked: true, allowed: true, message: "" });

    const [templateResult, employeeResult, campaignResult] = await Promise.all([
      fetchWithRetry(`${API}/phishing/templates`, { headers: { Authorization: `Bearer ${token}` } }),
      fetchWithRetry(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } }),
      fetchWithRetry(`${API}/phishing/campaigns`, { headers: { Authorization: `Bearer ${token}` } }),
    ]);

    if (!templateResult.response.ok) throw new Error(templateResult.data.detail || "Unable to load phishing templates.");
    if (!employeeResult.response.ok) throw new Error(employeeResult.data.detail || "Unable to load employees.");
    if (!campaignResult.response.ok) throw new Error(campaignResult.data.detail || "Unable to load campaigns.");

    setTemplates(templateResult.data);
    setEmployees(employeeResult.data);
    setCampaigns(campaignResult.data);

    if (!selectedTemplateId && templateResult.data.length) {
      setSelectedTemplateId(templateResult.data[0].id);
    }
    if (!selectedCampaignId && campaignResult.data.length) {
      setSelectedCampaignId(campaignResult.data[0].id);
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await loadData();
      } catch (error) {
        toast.error(error.message || "Unable to load phishing simulation tools.");
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, [token]);

  const selectedCampaign = useMemo(
    () => campaigns.find((campaign) => campaign.id === selectedCampaignId) || campaigns[0] || null,
    [campaigns, selectedCampaignId]
  );

  const summary = useMemo(() => {
    return campaigns.reduce(
      (acc, campaign) => {
        acc.totalCampaigns += 1;
        acc.totalTargets += campaign.total_targets;
        acc.totalClicks += campaign.clicked_count;
        acc.totalReports += campaign.reported_count;
        return acc;
      },
      { totalCampaigns: 0, totalTargets: 0, totalClicks: 0, totalReports: 0 }
    );
  }, [campaigns]);

  const toggleEmployee = (employeeId) => {
    setSelectedEmployeeIds((current) =>
      current.includes(employeeId) ? current.filter((id) => id !== employeeId) : [...current, employeeId]
    );
  };

  const handleCreateCampaign = async (sendImmediately) => {
    if (!campaignName.trim()) {
      toast.error("Campaign name is required.");
      return;
    }
    if (!selectedTemplateId) {
      toast.error("Select a phishing template.");
      return;
    }
    if (!selectedEmployeeIds.length) {
      toast.error("Select at least one employee.");
      return;
    }

    setWorking(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/phishing/campaigns`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: campaignName.trim(),
          template_id: selectedTemplateId,
          target_employee_ids: selectedEmployeeIds,
          send_immediately: sendImmediately,
        }),
      });
      if (!response.ok) throw new Error(data.detail || "Unable to create phishing campaign.");

      toast.success(sendImmediately ? "Campaign created and emails launched." : "Phishing campaign drafted successfully.");
      setCampaignName("");
      setSelectedEmployeeIds([]);
      await loadData();
      setSelectedCampaignId(data.id);
    } catch (error) {
      toast.error(error.message || "Unable to create phishing campaign.");
    } finally {
      setWorking(false);
    }
  };

  const handleSendCampaign = async (campaignId) => {
    setWorking(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/phishing/campaigns/${campaignId}/send`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(data.detail || "Unable to send campaign.");

      toast.success("Simulation emails are being sent.");
      await loadData();
      setSelectedCampaignId(campaignId);
    } catch (error) {
      toast.error(error.message || "Unable to send campaign.");
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-background" data-testid="phishing-loading-state"><Loader2 className="h-8 w-8 animate-spin text-[#00A8E8]" /></div>;
  }

  return (
    <AppShell current="phishing" testId="phishing-page">
<motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
          <section className="grid gap-6 rounded-[32px] bg-[#18181B] p-8 text-white lg:grid-cols-[1.1fr_0.9fr]" data-testid="phishing-hero-panel">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm text-[#7DD3FC]">
                <ShieldAlert className="h-4 w-4" /> In-app phishing simulations
              </div>
              <h1 className=" text-4xl font-bold sm:text-5xl" data-testid="phishing-heading">Train employees with safe, trackable phishing exercises</h1>
              <p className="mt-4 max-w-2xl text-zinc-200">Launch polished simulations, measure click and report behavior, and coach employees with instant lessons on suspicious cues.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <MetricCard title="Campaigns" value={summary.totalCampaigns} icon={Mail} testId="phishing-summary-campaigns" />
              <MetricCard title="Targets" value={summary.totalTargets} icon={Users} testId="phishing-summary-targets" />
              <MetricCard title="Clicks" value={summary.totalClicks} icon={AlertTriangle} testId="phishing-summary-clicks" />
              <MetricCard title="Reports" value={summary.totalReports} icon={CheckCircle2} testId="phishing-summary-reports" />
            </div>
          </section>

          <section className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">
            {!accessState.allowed ? (
              <Card className="rounded-[28px] border-zinc-200 xl:col-span-2" data-testid="phishing-upgrade-required-card">
                <CardContent className="flex flex-col gap-4 p-8 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.18em] text-zinc-400">Upgrade required</p>
                    <h2 className="mt-2  text-3xl font-bold text-[#18181B]">Phishing simulations are included on Business and Pro plans</h2>
                    <p className="mt-3 max-w-2xl text-zinc-600">{accessState.message}</p>
                  </div>
                  <Link to="/billing?view=plans" data-testid="phishing-upgrade-link">
                    <Button className="bg-[#18181B] text-white hover:bg-[#000000]">View plans</Button>
                  </Link>
                </CardContent>
              </Card>
            ) : (
              <>
            <Card className="rounded-[28px] border-zinc-200" data-testid="phishing-create-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Create simulation campaign</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-700">Campaign name</label>
                  <Input value={campaignName} onChange={(event) => setCampaignName(event.target.value)} placeholder="Q2 credential phishing drill" data-testid="phishing-campaign-name-input" />
                </div>

                <div className="space-y-3">
                  <p className="text-sm font-medium text-zinc-700">Choose a template</p>
                  <div className="space-y-3">
                    {templates.map((template) => (
                      <button
                        key={template.id}
                        type="button"
                        className={`w-full rounded-2xl border p-4 text-left transition ${selectedTemplateId === template.id ? "border-[#00A8E8] bg-[#00A8E8]/5" : "border-zinc-200 bg-white hover:border-zinc-300"}`}
                        onClick={() => setSelectedTemplateId(template.id)}
                        data-testid={`phishing-template-${template.id}`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-[#18181B]">{template.name}</p>
                            <p className="mt-1 text-sm text-zinc-500">{template.subject}</p>
                          </div>
                          <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs font-semibold text-zinc-500">{template.difficulty}</span>
                        </div>
                        <p className="mt-3 text-sm text-zinc-600">{template.scenario}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-4">
                    <p className="text-sm font-medium text-zinc-700">Select employees</p>
                    <Button type="button" variant="outline" className="border-zinc-300" onClick={() => setSelectedEmployeeIds(employees.map((employee) => employee.id))} data-testid="phishing-select-all-employees-button">Select all</Button>
                  </div>
                  <div className="max-h-80 space-y-2 overflow-y-auto rounded-2xl border border-zinc-200 p-3" data-testid="phishing-employee-selector">
                    {employees.length ? employees.map((employee) => (
                      <label key={employee.id} className="flex items-center gap-3 rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-700" data-testid={`phishing-employee-option-${employee.id}`}>
                        <input type="checkbox" checked={selectedEmployeeIds.includes(employee.id)} onChange={() => toggleEmployee(employee.id)} data-testid={`phishing-employee-checkbox-${employee.id}`} />
                        <span className="flex-1">
                          <strong className="text-[#18181B]">{employee.name}</strong>
                          <span className="block text-xs text-zinc-500">{employee.email} • {employee.department}</span>
                        </span>
                      </label>
                    )) : <div className="rounded-xl bg-zinc-50 p-4 text-sm text-zinc-500">Add employees first to launch a simulation.</div>}
                  </div>
                </div>

                <div className="flex flex-wrap gap-3">
                  <Button className="bg-[#18181B] text-white hover:bg-[#000000]" onClick={() => handleCreateCampaign(false)} disabled={working} data-testid="phishing-create-draft-button">
                    {working ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Save draft
                  </Button>
                  <Button className="bg-[#00A8E8] text-white hover:bg-[#008dc2]" onClick={() => handleCreateCampaign(true)} disabled={working} data-testid="phishing-create-send-button">
                    {working ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                    Launch simulation
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-[28px] border-zinc-200" data-testid="phishing-results-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Campaign results</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                {campaigns.length ? (
                  <>
                    <div className="flex flex-wrap gap-2">
                      {campaigns.map((campaign) => (
                        <Button
                          key={campaign.id}
                          variant={selectedCampaign?.id === campaign.id ? "default" : "outline"}
                          className={selectedCampaign?.id === campaign.id ? "bg-[#18181B] text-white" : "border-zinc-300 text-[#18181B]"}
                          onClick={() => setSelectedCampaignId(campaign.id)}
                          data-testid={`phishing-campaign-tab-${campaign.id}`}
                        >
                          {campaign.name}
                        </Button>
                      ))}
                    </div>

                    {selectedCampaign && (
                      <div className="space-y-5">
                        <div className="grid gap-4 md:grid-cols-4">
                          <MetricCard title="Delivered" value={selectedCampaign.delivered_count} icon={Mail} testId="phishing-selected-delivered" />
                          <MetricCard title="Opened" value={selectedCampaign.opened_count} icon={Users} testId="phishing-selected-opened" />
                          <MetricCard title="Clicked" value={selectedCampaign.clicked_count} icon={AlertTriangle} testId="phishing-selected-clicked" />
                          <MetricCard title="Reported" value={selectedCampaign.reported_count} icon={CheckCircle2} testId="phishing-selected-reported" />
                        </div>

                        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-zinc-50 p-4">
                          <div>
                            <p className="text-sm text-zinc-500">Template</p>
                            <p className="font-semibold text-[#18181B]">{selectedCampaign.template_name}</p>
                          </div>
                          <div>
                            <p className="text-sm text-zinc-500">Status</p>
                            <p className="font-semibold capitalize text-[#18181B]">{selectedCampaign.status.replace(/_/g, " ")}</p>
                          </div>
                          {selectedCampaign.status === "draft" && (
                            <Button className="bg-[#00A8E8] text-white hover:bg-[#008dc2]" onClick={() => handleSendCampaign(selectedCampaign.id)} disabled={working} data-testid="phishing-send-draft-button">
                              <Send className="mr-2 h-4 w-4" /> Send draft
                            </Button>
                          )}
                        </div>

                        <div className="space-y-3">
                          {selectedCampaign.recipients.map((recipient) => (
                            <div key={recipient.id} className="grid gap-4 rounded-2xl border border-zinc-200 p-4 lg:grid-cols-[1fr_0.7fr_0.8fr] lg:items-center" data-testid={`phishing-recipient-row-${recipient.id}`}>
                              <div>
                                <p className="font-semibold text-[#18181B]">{recipient.employee_name}</p>
                                <p className="text-sm text-zinc-500">{recipient.employee_email} • {recipient.department}</p>
                              </div>
                              <div className="space-y-1 text-sm text-zinc-500">
                                <p>Delivery: <span className="font-medium capitalize text-zinc-700">{recipient.delivery_status}</span></p>
                                <p>Opened: <span className="font-medium text-zinc-700">{recipient.opened_at ? "Yes" : "No"}</span></p>
                                <p>Clicked: <span className="font-medium text-zinc-700">{recipient.clicked_at ? "Yes" : "No"}</span></p>
                              </div>
                              <div className="space-y-1 text-sm text-zinc-500">
                                <p>Reported: <span className="font-medium text-zinc-700">{recipient.reported_at ? "Yes" : "No"}</span></p>
                                {recipient.delivery_error ? <p className="text-red-600">{recipient.delivery_error}</p> : <p className="text-emerald-600">No delivery issue logged.</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="rounded-2xl bg-zinc-50 p-5 text-sm text-zinc-500" data-testid="phishing-empty-state">
                    Create your first simulation to start measuring opens, clicks, and reporting behavior.
                  </div>
                )}
              </CardContent>
            </Card>
              </>
            )}
          </section>
        </motion.div>
      </AppShell>
  );
}
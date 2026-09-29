import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, Briefcase, CheckCircle2, FileText, Loader2, Printer, Shield, ShieldAlert, Target, TrendingUp, Users } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AppShell } from "@/components/AppShell";
import { fetchWithRetry } from "@/lib/api";
import { useAuth } from "@/App";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ScoreCard = ({ label, value, subtitle, icon: Icon, testId }) => (
  <Card className="rounded-[24px] border-zinc-200" data-testid={testId}>
    <CardContent className="flex items-center justify-between p-5">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">{label}</p>
        <p className="mt-2  text-3xl font-bold text-[#18181B]">{value}</p>
        {subtitle ? <p className="mt-2 text-sm text-zinc-500">{subtitle}</p> : null}
      </div>
      <div className="rounded-2xl bg-[#18181B]/5 p-3 text-[#18181B]">
        <Icon className="h-5 w-5" />
      </div>
    </CardContent>
  </Card>
);

const buildBoardActions = (stats) => {
  const domainActions = Object.values(stats?.aligned_domains || {})
    .sort((a, b) => a.score - b.score)
    .slice(0, 2)
    .map((domain, index) => ({
      priority: index + 1,
      title: `Strengthen ${domain.label}`,
      detail: `Leadership should sponsor near-term improvements in ${domain.label.toLowerCase()} because the current score is ${domain.score}/100. This maps to ${domain.iso_reference} and ${domain.nist_reference}.`,
    }));

  const actions = [...domainActions];

  if (stats?.phishing_program?.measured) {
    actions.push({
      priority: actions.length + 1,
      title: "Use phishing evidence in board oversight",
      detail: `Phishing resilience currently shows a ${stats.phishing_program.click_rate}% click rate and ${stats.phishing_program.report_rate}% report rate. Track this alongside maturity as a leading human-risk signal.`,
    });
  } else {
    actions.push({
      priority: actions.length + 1,
      title: "Add behavioral evidence beyond surveys",
      detail: "Run recurring phishing simulations so the board can compare self-reported awareness with observed click and reporting behavior.",
    });
  }

  return actions.slice(0, 3);
};

export default function StandardsSummaryPage() {
  const { token, user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exportingPdf, setExportingPdf] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsResult, reportsResult] = await Promise.all([
          fetchWithRetry(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          fetchWithRetry(`${API}/reports`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);

        if (!statsResult.response.ok) {
          throw new Error(statsResult.data.detail || "Unable to load board summary.");
        }

        setStats(statsResult.data);
        setReports(reportsResult.response.ok ? reportsResult.data : []);
      } catch (error) {
        toast.error(error.message || "Unable to load the standards summary.");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [token]);

  const boardActions = useMemo(() => buildBoardActions(stats), [stats]);
  const topDepartments = useMemo(() => {
    return Object.entries(stats?.department_risks || {})
      .map(([name, details]) => ({ name, ...details }))
      .sort((a, b) => (b.critical_flags || 0) - (a.critical_flags || 0) || (b.high_risk_count || 0) - (a.high_risk_count || 0))
      .slice(0, 3);
  }, [stats]);

  const handleDownloadPdf = async () => {
    try {
      setExportingPdf(true);
      const response = await fetch(`${API}/board-summary/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error("Unable to export the board summary PDF.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${user?.company_name?.replace(/\s+/g, "-").toLowerCase() || "cultureshield"}-board-summary.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Board summary PDF downloaded.");
    } catch (error) {
      toast.error(error.message || "Unable to export the PDF.");
    } finally {
      setExportingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background" data-testid="standards-summary-loading">
        <Loader2 className="h-8 w-8 animate-spin text-[#00A8E8]" />
      </div>
    );
  }

  return (
    <AppShell current="board" rootTestId="standards-summary-page">
<motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
          <section className="rounded-[32px] bg-[#18181B] p-8 text-white print:rounded-none print:bg-white print:p-0 print:text-zinc-900" data-testid="standards-summary-hero">
            <div className="flex flex-wrap items-start justify-between gap-4 print:hidden">
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm text-[#7DD3FC]">
                  <Briefcase className="h-4 w-4" /> Board-ready view
                </div>
                <h1 className=" text-4xl font-bold sm:text-5xl" data-testid="standards-summary-heading">Standards Alignment Summary</h1>
                <p className="mt-4 max-w-3xl text-zinc-200">A concise leadership view of cybersecurity culture maturity, framework mapping, human-risk signals, and board-level action priorities.</p>
              </div>
              <div className="flex flex-wrap gap-3">
              <Button className="bg-white text-[#18181B] hover:bg-zinc-100" onClick={handleDownloadPdf} data-testid="standards-summary-download-pdf-button">
                <FileText className="mr-2 h-4 w-4" /> {exportingPdf ? "Preparing PDF..." : "Download PDF"}
              </Button>
              <Button className="bg-white text-[#18181B] hover:bg-zinc-100" onClick={() => window.print()} data-testid="standards-summary-print-button">
                <Printer className="mr-2 h-4 w-4" /> Print summary
              </Button>
              </div>
            </div>

            <div className="hidden print:block">
              <h1 className=" text-4xl font-bold text-[#18181B]">CultureShield AI — Standards Alignment Summary</h1>
              <p className="mt-3 text-zinc-600">{user?.company_name} • Executive-ready overview of human security maturity and board priorities.</p>
            </div>
          </section>

          <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            <ScoreCard label="Overall score" value={`${stats?.overall_score || 0}/100`} subtitle={stats?.risk_level || "Unknown"} icon={Shield} testId="board-score-card" />
            <ScoreCard label="Maturity" value={stats?.maturity_level || "Initial"} subtitle={stats?.maturity_summary} icon={TrendingUp} testId="board-maturity-card" />
            <ScoreCard label="Participation" value={`${stats?.participation_rate || 0}%`} subtitle={`${stats?.completed_surveys || 0} of ${stats?.total_employees || 0} employees`} icon={Users} testId="board-participation-card" />
            <ScoreCard label="Phishing posture" value={stats?.phishing_program?.measured ? `${stats.phishing_program.resilience_score}/100` : "Not measured"} subtitle={stats?.phishing_program?.summary} icon={ShieldAlert} testId="board-phishing-card" />
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <Card className="rounded-[28px] border-zinc-200" data-testid="board-domain-alignment-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Standards-aligned control domains</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-600">{stats?.framework_note}</div>
                {Object.entries(stats?.aligned_domains || {}).map(([key, domain]) => (
                  <div key={key} className="rounded-2xl border border-zinc-200 p-4" data-testid={`board-domain-${key}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[#18181B]">{domain.label}</p>
                        <p className="mt-1 text-sm text-zinc-500">{domain.iso_reference} • {domain.nist_reference}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-[#18181B]">{domain.score}/100</p>
                        <p className="text-xs uppercase tracking-[0.16em] text-zinc-400">{domain.maturity_level}</p>
                      </div>
                    </div>
                    <p className="mt-3 text-sm text-zinc-600">{domain.focus}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="rounded-[28px] border-zinc-200" data-testid="board-actions-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Board action priorities</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {boardActions.map((action) => (
                  <div key={action.priority} className="rounded-2xl border border-zinc-200 p-4" data-testid={`board-action-${action.priority}`}>
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#18181B] text-sm font-bold text-white">{action.priority}</div>
                      <p className="font-semibold text-[#18181B]">{action.title}</p>
                    </div>
                    <p className="mt-3 text-sm text-zinc-600">{action.detail}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <Card className="rounded-[28px] border-zinc-200" data-testid="board-risk-highlights-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Top human-risk signals</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(stats?.behavioral_red_flags || []).slice(0, 4).map((flag) => (
                  <div key={flag.flag_id} className="rounded-2xl border border-zinc-200 p-4" data-testid={`board-risk-flag-${flag.flag_id}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="font-semibold text-[#18181B]">{flag.title}</p>
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${flag.severity === "critical" ? "bg-red-100 text-red-700" : flag.severity === "high" ? "bg-orange-100 text-orange-700" : "bg-zinc-100 text-zinc-600"}`}>{flag.severity}</span>
                    </div>
                    <p className="mt-3 text-sm text-zinc-600">{flag.description}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="rounded-[28px] border-zinc-200" data-testid="board-department-spotlight-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Department spotlight</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {topDepartments.length ? topDepartments.map((department) => (
                  <div key={department.name} className="rounded-2xl border border-zinc-200 p-4" data-testid={`board-department-${department.name.replace(/\s+/g, '-').toLowerCase()}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="font-semibold text-[#18181B]">{department.name}</p>
                      <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-600">{department.risk} risk</span>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.16em] text-zinc-400">Employees</p>
                        <p className="mt-1 text-lg font-bold text-[#18181B]">{department.employees}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.16em] text-zinc-400">Critical flags</p>
                        <p className="mt-1 text-lg font-bold text-[#18181B]">{department.critical_flags || 0}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.16em] text-zinc-400">Avg score</p>
                        <p className="mt-1 text-lg font-bold text-[#18181B]">{department.avg_score || 0}</p>
                      </div>
                    </div>
                  </div>
                )) : <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500">Department-level evidence will appear as more survey data comes in.</div>}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
            <Card className="rounded-[28px] border-zinc-200" data-testid="board-phishing-evidence-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Phishing evidence</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-zinc-600">{stats?.phishing_program?.summary}</p>
                {stats?.phishing_program?.measured ? (
                  <div className="grid gap-4 md:grid-cols-3">
                    <ScoreCard label="Open rate" value={`${stats.phishing_program.open_rate}%`} icon={Target} testId="board-open-rate-card" />
                    <ScoreCard label="Click rate" value={`${stats.phishing_program.click_rate}%`} icon={AlertTriangle} testId="board-click-rate-card" />
                    <ScoreCard label="Report rate" value={`${stats.phishing_program.report_rate}%`} icon={CheckCircle2} testId="board-report-rate-card" />
                  </div>
                ) : (
                  <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500">Run a phishing simulation to add observed behavior evidence to this board view.</div>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-[28px] border-zinc-200" data-testid="board-reporting-card">
              <CardHeader>
                <CardTitle className=" text-2xl text-[#18181B]">Report readiness</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-600">
                  {reports.length ? `Latest audit reports available: ${reports.length}. Use this board summary alongside the detailed report pack.` : "No audit reports have been generated yet. The board summary still reflects live scoring and control-domain maturity."}
                </div>
                <div className="flex flex-wrap gap-3">
                  <Link to="/reports" data-testid="board-open-reports-link">
                    <Button className="bg-[#18181B] text-white hover:bg-[#000000]">
                      <FileText className="mr-2 h-4 w-4" /> Open reports
                    </Button>
                  </Link>
                  <Link to="/dashboard" data-testid="board-open-dashboard-link">
                    <Button variant="outline" className="border-zinc-300 text-[#18181B]">
                      <Users className="mr-2 h-4 w-4" /> Back to dashboard
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </section>
        </motion.div>
      </AppShell>
  );
}
import { useState, useEffect } from "react";
import { Brand } from "@/components/Brand";
import { AppShell } from "@/components/AppShell";
import { Link, useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { useAuth } from "@/App";
import {
  Shield,
  Users,
  FileText,
  LogOut,
  BarChart3,
  Download,
  ArrowLeft,
  Loader2,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  BookOpen,
  Target,
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ReportDetail = () => {
  const { reportId } = useParams();
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReport();
  }, [reportId]);

  const fetchReport = async () => {
    try {
      const response = await fetch(`${API}/reports/${reportId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setReport(data);
      } else {
        toast.error("Report not found");
        navigate("/reports");
      }
    } catch (error) {
      toast.error("Failed to load report");
    } finally {
      setLoading(false);
    }
  };

  const downloadPdf = async () => {
    try {
      const response = await fetch(`${API}/reports/${reportId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `CultureShield_Audit_Report_${reportId.slice(0, 8)}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success("Report downloaded!");
      } else {
        toast.error("Failed to download report");
      }
    } catch (error) {
      toast.error("Download error");
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const content = report?.report_content || {};

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-[#00A8E8]" />
      </div>
    );
  }

  return (
    <AppShell current="reports" testId="report-detail-main">
{/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/reports">
              <Button variant="ghost" size="icon" className="text-zinc-600">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-[#18181B] ">
                Cybersecurity Culture Audit Report
              </h1>
              <p className="text-zinc-600 mt-1">
                Generated on {formatDate(report?.generated_at)}
              </p>
            </div>
          </div>
          <Button
            onClick={downloadPdf}
            className="bg-[#2ECC71] hover:bg-[#27ae60] text-white"
            data-testid="download-pdf-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            Download PDF
          </Button>
        </div>

        {/* Report Content */}
        <div className="max-w-4xl space-y-8">
          {/* Company Header */}
          <Card className="dashboard-card overflow-hidden">
            <div className="bg-gradient-to-r from-[#18181B] to-[#2d4a73] p-8 text-white">
              <div className="flex items-center gap-4 mb-6">
                <Brand size="lg" />
                <div>
                  <p className="text-white/70">Cybersecurity Culture Audit Report</p>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-white/60 text-sm">Company</p>
                  <p className="font-semibold">{user?.company_name}</p>
                </div>
                <div>
                  <p className="text-white/60 text-sm">Report Date</p>
                  <p className="font-semibold">{formatDate(report?.generated_at)}</p>
                </div>
                <div>
                  <p className="text-white/60 text-sm">Report ID</p>
                  <p className="font-mono text-sm">{reportId?.slice(0, 8)}</p>
                </div>
                <div>
                  <p className="text-white/60 text-sm">Powered by</p>
                  <p className="font-semibold">AI Analysis</p>
                </div>
              </div>
            </div>
          </Card>

          {content.framework_notice && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="dashboard-card border-[#00A8E8]/20 bg-[#00A8E8]/5" data-testid="report-framework-notice-card">
                <CardContent className="pt-6">
                  <p className="text-sm leading-relaxed text-zinc-700">{content.framework_notice}</p>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Executive Summary */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Executive Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-zinc-600 leading-relaxed">
                  {content.executive_summary || "No summary available"}
                </p>
              </CardContent>
            </Card>
          </motion.div>

          {content.maturity_assessment && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
              <Card className="dashboard-card" data-testid="report-maturity-card">
                <CardHeader>
                  <CardTitle className="text-[#18181B]  flex items-center gap-2">
                    <Shield className="w-5 h-5" />
                    Maturity Assessment
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-xl bg-zinc-50 p-4">
                    <p className="text-sm uppercase tracking-[0.18em] text-zinc-400">Current level</p>
                    <p className="mt-2 text-2xl font-bold text-[#18181B]">{content.maturity_assessment.level}</p>
                  </div>
                  <p className="text-zinc-600 leading-relaxed">{content.maturity_assessment.summary}</p>
                  {content.maturity_assessment.next_focus && (
                    <div className="rounded-xl border border-zinc-200 p-4 text-sm text-zinc-600">
                      <strong className="text-[#18181B]">Next focus:</strong> {content.maturity_assessment.next_focus}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {content.control_domain_scores && content.control_domain_scores.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
              <Card className="dashboard-card" data-testid="report-control-domain-card">
                <CardHeader>
                  <CardTitle className="text-[#18181B]  flex items-center gap-2">
                    <Target className="w-5 h-5" />
                    Control Domain Scores
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {content.control_domain_scores.map((domain, index) => (
                      <div key={index} className="rounded-xl border border-zinc-200 p-4" data-testid={`report-domain-score-${index}`}>
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="font-semibold text-[#18181B]">{domain.domain}</p>
                            <p className="mt-1 text-sm text-zinc-500">{domain.iso_reference} • {domain.nist_reference}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xl font-bold text-[#18181B]">{domain.score}/100</p>
                            <p className="text-xs font-medium uppercase tracking-[0.12em] text-zinc-400">{domain.maturity}</p>
                          </div>
                        </div>
                        {domain.finding && <p className="mt-3 text-sm text-zinc-600">{domain.finding}</p>}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Key Findings */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Key Findings
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {(content.key_findings || []).map((finding, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <CheckCircle className="w-5 h-5 text-[#00A8E8] mt-0.5 flex-shrink-0" />
                      <span className="text-zinc-600">{finding}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </motion.div>

          {/* Human Risk Factors */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Human Risk Factors
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {(content.human_risk_factors || []).map((risk, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-lg border ${
                        risk.severity === "High"
                          ? "bg-red-50 border-red-200"
                          : risk.severity === "Medium"
                          ? "bg-orange-50 border-orange-200"
                          : "bg-green-50 border-green-200"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-[#18181B]">{risk.risk}</span>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            risk.severity === "High"
                              ? "bg-red-100 text-red-700"
                              : risk.severity === "Medium"
                              ? "bg-orange-100 text-orange-700"
                              : "bg-green-100 text-green-700"
                          }`}
                        >
                          {risk.severity}
                        </span>
                      </div>
                      <p className="text-sm text-zinc-600">{risk.description}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {content.phishing_program_findings?.summary && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.24 }}
            >
              <Card className="dashboard-card" data-testid="report-phishing-findings-card">
                <CardHeader>
                  <CardTitle className="text-[#18181B]  flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    Phishing Program Findings
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-zinc-600 leading-relaxed">{content.phishing_program_findings.summary}</p>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-xl bg-zinc-50 p-4">
                      <p className="text-sm text-zinc-500">Click rate</p>
                      <p className="mt-2 text-2xl font-bold text-[#18181B]">{content.phishing_program_findings.click_rate ?? "N/A"}%</p>
                    </div>
                    <div className="rounded-xl bg-zinc-50 p-4">
                      <p className="text-sm text-zinc-500">Report rate</p>
                      <p className="mt-2 text-2xl font-bold text-[#18181B]">{content.phishing_program_findings.report_rate ?? "N/A"}%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Awareness Gaps */}
          {content.awareness_gaps && content.awareness_gaps.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="dashboard-card">
                <CardHeader>
                  <CardTitle className="text-[#18181B]  flex items-center gap-2">
                    <BookOpen className="w-5 h-5" />
                    Security Awareness Gaps
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {content.awareness_gaps.map((gap, index) => (
                      <li key={index} className="flex items-start gap-3">
                        <div className="w-2 h-2 bg-[#F39C12] rounded-full mt-2 flex-shrink-0" />
                        <span className="text-zinc-600">{gap}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {content.framework_alignment && content.framework_alignment.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
            >
              <Card className="dashboard-card" data-testid="report-framework-alignment-card">
                <CardHeader>
                  <CardTitle className="text-[#18181B]  flex items-center gap-2">
                    <BookOpen className="w-5 h-5" />
                    Standards Alignment Mapping
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {content.framework_alignment.map((item, index) => (
                      <div key={index} className="rounded-xl border border-zinc-200 p-4" data-testid={`report-framework-alignment-${index}`}>
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-[#18181B]">{item.theme}</p>
                            <p className="mt-1 text-sm text-zinc-500">{item.iso_reference} • {item.nist_reference}</p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${item.status === "Aligned" ? "bg-green-100 text-green-700" : "bg-orange-100 text-orange-700"}`}>
                            {item.status}
                          </span>
                        </div>
                        <p className="mt-3 text-sm text-zinc-600">{item.commentary}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Recommendations */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {(content.recommendations || []).map((rec, index) => (
                    <div key={index} className="relative pl-8">
                      <div className="absolute left-0 top-0 w-6 h-6 bg-[#00A8E8] text-white rounded-full flex items-center justify-center text-sm font-semibold">
                        {rec.priority || index + 1}
                      </div>
                      <div>
                        <h4 className="font-semibold text-[#18181B] mb-1">{rec.title}</h4>
                        <p className="text-zinc-600 text-sm mb-2">{rec.description}</p>
                        {rec.training_type && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-[#00A8E8]/10 text-[#00A8E8] rounded text-xs font-medium">
                            <BookOpen className="w-3 h-3" />
                            {rec.training_type}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Improvement Roadmap */}
          {content.improvement_roadmap && content.improvement_roadmap.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card className="dashboard-card">
                <CardHeader>
                  <CardTitle className="text-[#18181B]  flex items-center gap-2">
                    <Target className="w-5 h-5" />
                    Improvement Roadmap
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {content.improvement_roadmap.map((phase, index) => (
                      <div key={index} className="flex items-start gap-4">
                        <div className="w-8 h-8 bg-zinc-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <span className="text-sm font-semibold text-[#18181B]">
                            {index + 1}
                          </span>
                        </div>
                        <p className="text-zinc-600 pt-1">{phase}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Footer */}
          <div className="text-center py-8 border-t border-zinc-200">
            <Brand size="sm" className="mx-auto mb-2" />
            <p className="text-sm text-zinc-500">
              CultureShield AI - Cybersecurity Culture Assessment Platform
            </p>
            <p className="text-xs text-zinc-400 mt-1">
              Report generated using advanced AI analysis
            </p>
          </div>
        </div>
      </AppShell>
  );
};

export default ReportDetail;

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AppShell } from "@/components/AppShell";
import { toast } from "sonner";
import { useAuth } from "@/App";
import { FileText, Plus, Download, Eye, Loader2, Calendar } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ReportsPage = () => {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await fetch(`${API}/reports`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setReports(data);
      }
    } catch (error) {
      toast.error("Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    setGenerating(true);
    try {
      const response = await fetch(`${API}/reports/generate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setReports((prev) => [data, ...prev]);
        toast.success("Report generated successfully!");
        navigate(`/reports/${data.id}`);
      } else {
        const error = await response.json();
        if (response.status === 403) {
          toast.error(error.detail || "Upgrade required to generate reports");
          navigate("/billing?view=plans");
          return;
        }
        toast.error(error.detail || "Failed to generate report");
      }
    } catch (error) {
      toast.error("Connection error");
    } finally {
      setGenerating(false);
    }
  };

  const downloadPdf = async (reportId) => {
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
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <AppShell current="reports" testId="reports-main">
{/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#18181B] ">
              Audit Reports
            </h1>
            <p className="text-zinc-600 mt-1">
              Generate and download AI-powered cybersecurity culture reports
            </p>
          </div>
          <Button
            onClick={generateReport}
            disabled={generating}
            className="bg-[#00A8E8] hover:bg-[#008dc2] text-white"
            data-testid="generate-new-report-btn"
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Generate New Report
              </>
            )}
          </Button>
        </div>

        {/* Reports List */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-[#00A8E8]" />
          </div>
        ) : reports.length === 0 ? (
          <Card className="dashboard-card">
            <CardContent className="py-16 text-center">
              <FileText className="w-16 h-16 mx-auto mb-4 text-zinc-300" />
              <h3 className="text-xl font-semibold text-[#18181B] mb-2">No Reports Yet</h3>
              <p className="text-zinc-500 mb-6 max-w-md mx-auto">
                Generate your first cybersecurity culture audit report to get AI-powered insights
                and recommendations.
              </p>
              <Button
                onClick={generateReport}
                disabled={generating}
                className="bg-[#18181B] hover:bg-[#000000]"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Generate First Report
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {reports.map((report, index) => (
              <motion.div
                key={report.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="dashboard-card h-full">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="w-12 h-12 bg-[#18181B]/10 rounded-lg flex items-center justify-center">
                        <FileText className="w-6 h-6 text-[#18181B]" />
                      </div>
                      <div className="flex items-center gap-1 text-sm text-zinc-500">
                        <Calendar className="w-4 h-4" />
                        {formatDate(report.generated_at)}
                      </div>
                    </div>

                    <h3 className="font-semibold text-[#18181B] mb-2">
                      Cybersecurity Culture Audit
                    </h3>

                    {report.report_content?.executive_summary && (
                      <p className="text-sm text-zinc-600 mb-4 line-clamp-3">
                        {report.report_content.executive_summary}
                      </p>
                    )}

                    <div className="flex gap-2 mt-auto pt-4 border-t border-zinc-100">
                      <Link to={`/reports/${report.id}`} className="flex-1">
                        <Button
                          variant="outline"
                          className="w-full border-zinc-200 hover:border-[#00A8E8] hover:text-[#00A8E8]"
                          data-testid={`view-report-${report.id}`}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          View
                        </Button>
                      </Link>
                      <Button
                        variant="outline"
                        onClick={() => downloadPdf(report.id)}
                        className="border-zinc-200 hover:border-[#2ECC71] hover:text-[#2ECC71]"
                        data-testid={`download-report-${report.id}`}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </AppShell>
  );
};

export default ReportsPage;

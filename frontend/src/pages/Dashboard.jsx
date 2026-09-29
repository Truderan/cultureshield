import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { AppShell } from "@/components/AppShell";
import { toast } from "sonner";
import { useAuth } from "@/App";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { Shield, Users, FileText, BarChart3, AlertTriangle, Eye, Mail, UserPlus, CreditCard, ShieldAlert, BookOpen } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RISK_COLORS = {
  Critical: "#9B1C31",
  High: "#E74C3C",
  "Medium-High": "#E67E22",
  Medium: "#F39C12",
  "Low-Medium": "#F1C40F",
  Low: "#2ECC71",
};

const Dashboard = () => {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await fetch(`${API}/dashboard/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        toast.error("Failed to load dashboard");
      }
    } catch (error) {
      toast.error("Connection error");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/");
    toast.success("Logged out successfully");
  };

  const getRiskColor = (risk) => RISK_COLORS[risk] || "#64748B";

  const getScoreColor = (score) => {
    if (score >= 75) return "#2ECC71";
    if (score >= 50) return "#F39C12";
    return "#E74C3C";
  };

  // Prepare chart data
  const departmentData = stats?.department_risks
    ? Object.entries(stats.department_risks).map(([name, data]) => ({
        name,
        score: data.avg_score || 0,
        employees: data.employees,
        risk: data.risk,
      }))
    : [];

  const heatmapData = stats?.risk_heatmap
    ? Object.entries(stats.risk_heatmap).map(([key, value]) => ({
        name: key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
        value,
        fullMark: 100,
      }))
    : [];

  const scoreBreakdown = stats
    ? [
        { name: "Awareness", value: stats.awareness_score, color: "#00A8E8" },
        { name: "Behavior", value: stats.behavior_score, color: "#18181B" },
        { name: "Reporting", value: stats.reporting_score, color: "#2ECC71" },
      ]
    : [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-[#18181B] border-t-transparent"></div>
      </div>
    );
  }

  return (
    <AppShell current="dashboard" testId="dashboard-main">
{/* Header */}
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-[#18181B] ">
              Security Culture Dashboard
            </h1>
            <p className="text-zinc-600 mt-1">
              Welcome back, {user?.company_name}
            </p>
          </div>
          <div className="flex w-full flex-wrap items-center gap-3 sm:w-auto">
            <Link to="/settings/security">
              <Button variant="outline" className="w-full border-zinc-300 text-[#18181B] hover:bg-zinc-100 sm:w-auto" data-testid="manage-security-btn">
                <Shield className="w-4 h-4 mr-2" />
                Security
              </Button>
            </Link>
            <Link to="/billing">
              <Button variant="outline" className="w-full border-zinc-300 text-[#18181B] hover:bg-zinc-100 sm:w-auto" data-testid="manage-billing-btn">
                <CreditCard className="w-4 h-4 mr-2" />
                Billing
              </Button>
            </Link>
            <Link to="/phishing">
              <Button variant="outline" className="w-full border-zinc-300 text-[#18181B] hover:bg-zinc-100 sm:w-auto" data-testid="manage-phishing-btn">
                <ShieldAlert className="w-4 h-4 mr-2" />
                Phishing
              </Button>
            </Link>
            <Link to="/standards-summary">
              <Button variant="outline" className="w-full border-zinc-300 text-[#18181B] hover:bg-zinc-100 sm:w-auto" data-testid="open-board-summary-btn">
                <BookOpen className="w-4 h-4 mr-2" />
                Board Summary
              </Button>
            </Link>
            <Link to="/reports">
              <Button className="w-full bg-[#00A8E8] text-white hover:bg-[#008dc2] sm:w-auto" data-testid="generate-report-btn">
                <FileText className="w-4 h-4 mr-2" />
                Generate Report
              </Button>
            </Link>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {/* Main Score Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="md:col-span-2"
          >
            <Card className="border-0 shadow-lg overflow-hidden">
              <CardContent className="p-0">
                <div className="bg-gradient-to-br from-[#18181B] to-[#2d4a73] p-8 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/70 text-sm font-medium mb-1">CultureShield Score</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-5xl font-bold ">
                          {stats?.overall_score || 0}
                        </span>
                        <span className="text-xl text-white/70">/ 100</span>
                      </div>
                    </div>
                    <div className="relative w-28 h-28">
                      <svg className="w-28 h-28 transform -rotate-90">
                        <circle
                          cx="56"
                          cy="56"
                          r="48"
                          stroke="rgba(255,255,255,0.2)"
                          strokeWidth="10"
                          fill="none"
                        />
                        <circle
                          cx="56"
                          cy="56"
                          r="48"
                          stroke="#00A8E8"
                          strokeWidth="10"
                          fill="none"
                          strokeLinecap="round"
                          strokeDasharray={`${(stats?.overall_score || 0) * 3.02} 302`}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Shield className="w-10 h-10 text-[#00A8E8]" />
                      </div>
                    </div>
                  </div>
                  <div className="mt-6 flex flex-wrap items-center gap-3">
                    <span
                      className={`px-4 py-1.5 rounded-full text-sm font-semibold ${
                        stats?.risk_level === "Low"
                          ? "bg-[#2ECC71]/20 text-[#2ECC71]"
                          : stats?.risk_level === "Medium"
                          ? "bg-[#F39C12]/20 text-[#F39C12]"
                          : "bg-[#E74C3C]/20 text-[#E74C3C]"
                      }`}
                      data-testid="risk-level-badge"
                    >
                      {stats?.risk_level || "Unknown"} Risk
                    </span>
                    <span
                      className="px-4 py-1.5 rounded-full text-sm font-semibold bg-white/10 text-white"
                      data-testid="maturity-level-badge"
                    >
                      {stats?.maturity_level || "Initial"} Maturity
                    </span>
                    <span className="text-white/60 text-sm">
                      Based on {stats?.completed_surveys || 0} responses
                    </span>
                  </div>
                  {stats?.maturity_summary && (
                    <p className="mt-4 max-w-2xl text-sm leading-relaxed text-white/75" data-testid="maturity-summary-text">
                      {stats.maturity_summary}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Participation */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="h-full dashboard-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <Users className="w-8 h-8 text-[#00A8E8]" />
                  <span className="text-xs font-medium text-zinc-500 bg-zinc-100 px-2 py-1 rounded">
                    PARTICIPATION
                  </span>
                </div>
                <p className="text-3xl font-bold text-[#18181B] ">
                  {stats?.participation_rate || 0}%
                </p>
                <p className="text-zinc-500 text-sm mt-1">
                  {stats?.completed_surveys || 0} of {stats?.total_employees || 0} employees
                </p>
                <Progress
                  value={stats?.participation_rate || 0}
                  className="h-2 mt-4"
                />
              </CardContent>
            </Card>
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="h-full dashboard-card">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-zinc-500 mb-4">QUICK ACTIONS</p>
                <div className="space-y-3">
                  <Link to="/employees">
                    <Button
                      variant="outline"
                      className="w-full justify-start border-zinc-200 hover:border-[#00A8E8] hover:text-[#00A8E8]"
                      data-testid="invite-employees-btn"
                    >
                      <UserPlus className="w-4 h-4 mr-2" />
                      Invite Employees
                    </Button>
                  </Link>
                  <Link to="/reports">
                    <Button
                      variant="outline"
                      className="w-full justify-start border-zinc-200 hover:border-[#00A8E8] hover:text-[#00A8E8]"
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      View Reports
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Score Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {scoreBreakdown.map((item, index) => (
            <motion.div
              key={item.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * index }}
            >
              <Card className="dashboard-card">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm font-medium text-zinc-500">{item.name.toUpperCase()} SCORE</p>
                    {item.name === "Awareness" && <Eye className="w-5 h-5 text-zinc-400" />}
                    {item.name === "Behavior" && <Shield className="w-5 h-5 text-zinc-400" />}
                    {item.name === "Reporting" && <Mail className="w-5 h-5 text-zinc-400" />}
                  </div>
                  <p
                    className="text-4xl font-bold "
                    style={{ color: getScoreColor(item.value) }}
                  >
                    {item.value}%
                  </p>
                  <Progress
                    value={item.value}
                    className="h-2 mt-4"
                    style={{ "--progress-color": item.color }}
                  />
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Department Risk Breakdown */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Department Risk Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                {departmentData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={departmentData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis type="number" domain={[0, 100]} stroke="#64748b" />
                      <YAxis dataKey="name" type="category" width={100} stroke="#64748b" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#fff",
                          border: "1px solid #e2e8f0",
                          borderRadius: "8px",
                        }}
                        formatter={(value, name, props) => [
                          `${value}% (${props.payload.risk} Risk)`,
                          "Score",
                        ]}
                      />
                      <Bar
                        dataKey="score"
                        radius={[0, 4, 4, 0]}
                        fill="#00A8E8"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-zinc-500">
                    <div className="text-center">
                      <Users className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
                      <p>No department data yet</p>
                      <p className="text-sm">Invite employees to see breakdown</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Risk Heatmap */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Human Risk Heatmap
                </CardTitle>
              </CardHeader>
              <CardContent>
                {heatmapData.length > 0 && stats?.completed_surveys > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <RadarChart data={heatmapData}>
                      <PolarGrid stroke="#e2e8f0" />
                      <PolarAngleAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} />
                      <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "#64748b" }} />
                      <Radar
                        name="Risk Level"
                        dataKey="value"
                        stroke="#00A8E8"
                        fill="#00A8E8"
                        fillOpacity={0.3}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#fff",
                          border: "1px solid #e2e8f0",
                          borderRadius: "8px",
                        }}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-zinc-500">
                    <div className="text-center">
                      <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
                      <p>No risk data yet</p>
                      <p className="text-sm">Complete surveys to see heatmap</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Risk Indicators Grid */}
        {stats?.risk_heatmap && stats?.completed_surveys > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B] ">
                  Risk Indicators
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                  {Object.entries(stats.risk_heatmap).map(([key, value]) => {
                    const label = key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
                    // Inverted: higher value = more risk
                    const riskLevel = value <= 30 ? "Low" : value <= 60 ? "Medium" : "High";
                    return (
                      <div
                        key={key}
                        className={`p-4 rounded-lg border ${
                          riskLevel === "Low"
                            ? "bg-green-50 border-green-200"
                            : riskLevel === "Medium"
                            ? "bg-orange-50 border-orange-200"
                            : "bg-red-50 border-red-200"
                        }`}
                      >
                        <p className="text-xs font-medium text-zinc-500 mb-1">{label}</p>
                        <p
                          className="text-2xl font-bold"
                          style={{ color: riskLevel === "Low" ? "#2ECC71" : riskLevel === "Medium" ? "#F39C12" : "#E74C3C" }}
                        >
                          {value}%
                        </p>
                        <span
                          className={`text-xs font-medium ${
                            riskLevel === "Low"
                              ? "text-green-600"
                              : riskLevel === "Medium"
                              ? "text-orange-600"
                              : "text-red-600"
                          }`}
                        >
                          {riskLevel} Risk
                        </span>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Behavioral Red Flags */}
        {stats?.behavioral_red_flags && stats.behavioral_red_flags.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <Card className="dashboard-card border-l-4 border-l-red-500">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                  Behavioral Red Flags Detected
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {stats.behavioral_red_flags.slice(0, 5).map((flag, index) => (
                    <div
                      key={flag.flag_id}
                      className={`p-4 rounded-lg border ${
                        flag.severity === "critical"
                          ? "bg-red-50 border-red-300"
                          : "bg-orange-50 border-orange-300"
                      }`}
                      data-testid={`red-flag-${index}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                                flag.severity === "critical"
                                  ? "bg-red-200 text-red-800"
                                  : "bg-orange-200 text-orange-800"
                              }`}
                            >
                              {flag.severity}
                            </span>
                            <h4 className="font-semibold text-[#18181B]">{flag.title}</h4>
                          </div>
                          <p className="text-sm text-zinc-600 mb-2">{flag.description}</p>
                          <p className="text-sm text-zinc-500">
                            <strong>Recommendation:</strong> {flag.recommendation}
                          </p>
                        </div>
                        <div className="text-right ml-4">
                          <p className="text-2xl font-bold text-red-600">{flag.affected_count}</p>
                          <p className="text-xs text-zinc-500">employees</p>
                          <p className="text-sm font-medium text-red-600">({flag.percentage}%)</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* High Risk Employees */}
        {stats?.high_risk_employees && stats.high_risk_employees.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  High Risk Employees
                  <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                    {stats.high_risk_employees.length} identified
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-zinc-200">
                        <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Employee</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Department</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Risk Profile</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Score</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Flags</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Top Risks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.high_risk_employees.map((emp) => (
                        <tr key={emp.employee_id} className="border-b border-zinc-100 hover:bg-zinc-50" data-testid={`high-risk-row-${emp.employee_id}`}>
                          <td className="py-3 px-4">
                            <span className="font-medium text-[#18181B]">{emp.name}</span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-1 bg-zinc-100 rounded text-sm">{emp.department}</span>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                emp.risk_persona === "Critical Risk"
                                  ? "bg-red-100 text-red-700"
                                  : emp.risk_persona === "High Risk"
                                  ? "bg-orange-100 text-orange-700"
                                  : "bg-yellow-100 text-yellow-700"
                              }`}
                            >
                              {emp.risk_persona}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className="font-bold"
                              style={{ color: getScoreColor(emp.overall_score) }}
                            >
                              {emp.overall_score}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              {emp.critical_flags > 0 && (
                                <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">
                                  {emp.critical_flags} Critical
                                </span>
                              )}
                              {emp.high_flags > 0 && (
                                <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs">
                                  {emp.high_flags} High
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex flex-wrap gap-1">
                              {emp.top_risks.slice(0, 2).map((risk, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded text-xs">
                                  {risk}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Vulnerability Index */}
        {stats?.completed_surveys > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
          >
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  Organization Vulnerability Index
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-8">
                  <div className="flex-1">
                    <div className="flex items-end gap-2 mb-2">
                      <span
                        className="text-5xl font-bold "
                        style={{
                          color:
                            stats.vulnerability_index <= 30
                              ? "#2ECC71"
                              : stats.vulnerability_index <= 60
                              ? "#F39C12"
                              : "#E74C3C",
                        }}
                      >
                        {stats.vulnerability_index}
                      </span>
                      <span className="text-zinc-500 text-lg mb-1">/ 100</span>
                    </div>
                    <p className="text-zinc-600 text-sm">
                      {stats.vulnerability_index <= 30
                        ? "Your organization has strong security practices. Continue monitoring and training."
                        : stats.vulnerability_index <= 60
                        ? "Moderate vulnerabilities detected. Targeted training recommended for high-risk areas."
                        : "Significant security vulnerabilities present. Immediate intervention required."}
                    </p>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <p className="text-2xl font-bold text-green-600">
                        {stats.risk_distribution?.Low || 0}
                      </p>
                      <p className="text-xs text-zinc-500">Low Risk</p>
                    </div>
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <p className="text-2xl font-bold text-orange-600">
                        {(stats.risk_distribution?.Medium || 0) + (stats.risk_distribution?.["Low-Medium"] || 0) + (stats.risk_distribution?.["Medium-High"] || 0)}
                      </p>
                      <p className="text-xs text-zinc-500">Medium Risk</p>
                    </div>
                    <div className="text-center p-4 bg-red-50 rounded-lg">
                      <p className="text-2xl font-bold text-red-600">
                        {(stats.risk_distribution?.High || 0) + (stats.risk_distribution?.Critical || 0)}
                      </p>
                      <p className="text-xs text-zinc-500">High/Critical</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AppShell>
  );
};

export default Dashboard;

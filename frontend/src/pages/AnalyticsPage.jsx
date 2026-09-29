import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AppShell } from "@/components/AppShell";
import { toast } from "sonner";
import { useAuth } from "@/App";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from "recharts";
import { TrendingUp, TrendingDown, Minus, Calendar, Loader2, Lightbulb, ArrowUpRight, ArrowDownRight } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AnalyticsPage = () => {
  const { user, token, logout } = useAuth();
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("weekly");

  useEffect(() => {
    fetchTrends();
  }, []);

  const fetchTrends = async () => {
    try {
      const response = await fetch(`${API}/analytics/trends`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTrends(data);
      } else {
        toast.error("Failed to load analytics");
      }
    } catch (error) {
      toast.error("Connection error");
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (direction) => {
    switch (direction) {
      case "improving":
        return <TrendingUp className="w-5 h-5 text-green-500" />;
      case "declining":
        return <TrendingDown className="w-5 h-5 text-red-500" />;
      default:
        return <Minus className="w-5 h-5 text-zinc-500" />;
    }
  };

  const getChangeColor = (change) => {
    if (change > 0) return "text-green-600";
    if (change < 0) return "text-red-600";
    return "text-zinc-600";
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-[#00A8E8]" />
      </div>
    );
  }

  const weeklyData = trends?.weekly_trends || [];
  const monthlyData = trends?.monthly_trends || [];

  return (
    <AppShell current="analytics" testId="analytics-main">
{/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#18181B] ">
              Trend Analytics
            </h1>
            <p className="text-zinc-600 mt-1">
              Track your cybersecurity culture progress over time
            </p>
          </div>
          <div className="flex items-center gap-2">
            {getTrendIcon(trends?.trend_direction)}
            <span className="text-sm font-medium capitalize text-zinc-700">
              {trends?.trend_direction || "No data"}
            </span>
          </div>
        </div>

        {/* Score Change Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card className="dashboard-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-zinc-500">Weekly Change</p>
                  {trends?.score_change_weekly > 0 ? (
                    <ArrowUpRight className="w-5 h-5 text-green-500" />
                  ) : trends?.score_change_weekly < 0 ? (
                    <ArrowDownRight className="w-5 h-5 text-red-500" />
                  ) : (
                    <Minus className="w-5 h-5 text-zinc-400" />
                  )}
                </div>
                <p className={`text-3xl font-bold  ${getChangeColor(trends?.score_change_weekly)}`}>
                  {trends?.score_change_weekly > 0 ? "+" : ""}
                  {trends?.score_change_weekly || 0} pts
                </p>
                <p className="text-xs text-zinc-500 mt-1">vs last week</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="dashboard-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-zinc-500">Monthly Change</p>
                  {trends?.score_change_monthly > 0 ? (
                    <ArrowUpRight className="w-5 h-5 text-green-500" />
                  ) : trends?.score_change_monthly < 0 ? (
                    <ArrowDownRight className="w-5 h-5 text-red-500" />
                  ) : (
                    <Minus className="w-5 h-5 text-zinc-400" />
                  )}
                </div>
                <p className={`text-3xl font-bold  ${getChangeColor(trends?.score_change_monthly)}`}>
                  {trends?.score_change_monthly > 0 ? "+" : ""}
                  {trends?.score_change_monthly || 0} pts
                </p>
                <p className="text-xs text-zinc-500 mt-1">vs last month</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="dashboard-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-zinc-500">Trend Direction</p>
                  {getTrendIcon(trends?.trend_direction)}
                </div>
                <p className="text-3xl font-bold  text-[#18181B] capitalize">
                  {trends?.trend_direction || "No data"}
                </p>
                <p className="text-xs text-zinc-500 mt-1">based on historical data</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Trend Charts */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="dashboard-card mb-8">
            <CardHeader>
              <CardTitle className="text-[#18181B] ">
                Score Trends
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="mb-6">
                  <TabsTrigger value="weekly" data-testid="weekly-tab">
                    <Calendar className="w-4 h-4 mr-2" />
                    Weekly (Last 4 weeks)
                  </TabsTrigger>
                  <TabsTrigger value="monthly" data-testid="monthly-tab">
                    <Calendar className="w-4 h-4 mr-2" />
                    Monthly (Last 6 months)
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="weekly">
                  {weeklyData.length > 0 && weeklyData.some(d => d.responses_count > 0) ? (
                    <ResponsiveContainer width="100%" height={400}>
                      <AreaChart data={weeklyData}>
                        <defs>
                          <linearGradient id="colorOverall" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#18181B" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#18181B" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="period" stroke="#64748b" />
                        <YAxis domain={[0, 100]} stroke="#64748b" />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#fff",
                            border: "1px solid #e2e8f0",
                            borderRadius: "8px",
                          }}
                        />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="overall_score"
                          name="Overall Score"
                          stroke="#18181B"
                          fillOpacity={1}
                          fill="url(#colorOverall)"
                          strokeWidth={3}
                        />
                        <Line
                          type="monotone"
                          dataKey="awareness_score"
                          name="Awareness"
                          stroke="#00A8E8"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="behavior_score"
                          name="Behavior"
                          stroke="#2ECC71"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="reporting_score"
                          name="Reporting"
                          stroke="#F39C12"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[400px] flex items-center justify-center text-zinc-500">
                      <div className="text-center">
                        <Calendar className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
                        <p>No weekly data available yet</p>
                        <p className="text-sm">Complete surveys to see trends</p>
                      </div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="monthly">
                  {monthlyData.length > 0 && monthlyData.some(d => d.responses_count > 0) ? (
                    <ResponsiveContainer width="100%" height={400}>
                      <AreaChart data={monthlyData}>
                        <defs>
                          <linearGradient id="colorOverallMonthly" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#18181B" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#18181B" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="period" stroke="#64748b" />
                        <YAxis domain={[0, 100]} stroke="#64748b" />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#fff",
                            border: "1px solid #e2e8f0",
                            borderRadius: "8px",
                          }}
                        />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="overall_score"
                          name="Overall Score"
                          stroke="#18181B"
                          fillOpacity={1}
                          fill="url(#colorOverallMonthly)"
                          strokeWidth={3}
                        />
                        <Line
                          type="monotone"
                          dataKey="awareness_score"
                          name="Awareness"
                          stroke="#00A8E8"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="behavior_score"
                          name="Behavior"
                          stroke="#2ECC71"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="reporting_score"
                          name="Reporting"
                          stroke="#F39C12"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[400px] flex items-center justify-center text-zinc-500">
                      <div className="text-center">
                        <Calendar className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
                        <p>No monthly data available yet</p>
                        <p className="text-sm">Complete surveys to see trends</p>
                      </div>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>

        {/* Participation Trend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="dashboard-card mb-8">
            <CardHeader>
              <CardTitle className="text-[#18181B] ">
                Survey Participation Over Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(activeTab === "weekly" ? weeklyData : monthlyData).some(d => d.responses_count > 0) ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={activeTab === "weekly" ? weeklyData : monthlyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="period" stroke="#64748b" />
                    <YAxis stroke="#64748b" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#fff",
                        border: "1px solid #e2e8f0",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar
                      dataKey="responses_count"
                      name="Responses"
                      fill="#00A8E8"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-zinc-500">
                  <p>No participation data available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* AI Insights */}
        {trends?.insights && trends.insights.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card className="dashboard-card border-l-4 border-l-[#00A8E8]">
              <CardHeader>
                <CardTitle className="text-[#18181B]  flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-[#00A8E8]" />
                  Insights & Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {trends.insights.map((insight, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg"
                    >
                      <div className="w-6 h-6 bg-[#00A8E8]/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-xs font-semibold text-[#00A8E8]">{index + 1}</span>
                      </div>
                      <p className="text-zinc-700">{insight}</p>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AppShell>
  );
};

export default AnalyticsPage;

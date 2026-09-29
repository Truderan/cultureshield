import { useState, useEffect } from "react";
import { Brand } from "@/components/Brand";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Shield, ChevronLeft, ChevronRight, CheckCircle, AlertTriangle, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EmployeeSurvey = () => {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState(null);
  const [companyName, setCompanyName] = useState("");
  const [questions, setQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [responses, setResponses] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchSurveyData();
  }, [employeeId]);

  const fetchSurveyData = async () => {
    try {
      // Fetch employee info
      const empResponse = await fetch(`${API}/survey/employee/${employeeId}`);
      if (!empResponse.ok) {
        if (empResponse.status === 404) {
          toast.error("Survey link not found or invalid");
          return;
        }
        throw new Error("Failed to load survey");
      }
      const empData = await empResponse.json();
      
      if (empData.employee.survey_completed) {
        setCompleted(true);
        setLoading(false);
        return;
      }
      
      setEmployee(empData.employee);
      setCompanyName(empData.company_name);

      // Fetch questions
      const qResponse = await fetch(`${API}/survey/questions`);
      if (qResponse.ok) {
        const qData = await qResponse.json();
        setQuestions(qData);
      }
    } catch (error) {
      toast.error("Failed to load survey");
    } finally {
      setLoading(false);
    }
  };

  const handleResponse = (questionId, optionIndex) => {
    setResponses((prev) => ({
      ...prev,
      [questionId]: optionIndex,
    }));
  };

  const nextQuestion = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion((prev) => prev + 1);
    }
  };

  const prevQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion((prev) => prev - 1);
    }
  };

  const submitSurvey = async () => {
    // Check if all questions are answered
    const unanswered = questions.filter((q) => responses[q.id] === undefined);
    if (unanswered.length > 0) {
      toast.error(`Please answer all questions. ${unanswered.length} remaining.`);
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(`${API}/survey/submit/${employeeId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ responses }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
        setCompleted(true);
        toast.success("Survey submitted successfully!");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to submit survey");
      }
    } catch (error) {
      toast.error("Connection error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const progress = questions.length > 0 ? ((currentQuestion + 1) / questions.length) * 100 : 0;
  const answeredCount = Object.keys(responses).length;
  const currentQ = questions[currentQuestion];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-[#18181B] border-t-transparent"></div>
      </div>
    );
  }

  // Already completed
  if (completed && !result) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center max-w-md"
        >
          <div className="w-20 h-20 bg-[#2ECC71]/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-[#2ECC71]" />
          </div>
          <h1 className="text-2xl font-bold text-[#18181B]  mb-2">
            Survey Already Completed
          </h1>
          <p className="text-zinc-600">
            You have already submitted your cybersecurity culture assessment. Thank you for your participation!
          </p>
        </motion.div>
      </div>
    );
  }

  // Show result after submission
  if (completed && result) {
    const riskProfile = result.risk_profile || {};
    const riskFlags = result.risk_flags || [];
    
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center max-w-2xl w-full"
        >
          <div className="w-20 h-20 bg-[#2ECC71]/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-[#2ECC71]" />
          </div>
          <h1 className="text-2xl font-bold text-[#18181B]  mb-2">
            Thank You!
          </h1>
          <p className="text-zinc-600 mb-8">
            Your cybersecurity culture assessment has been submitted successfully.
          </p>

          {/* Main Score Card */}
          <Card className="text-left mb-6">
            <CardContent className="p-6">
              <h3 className="font-semibold text-[#18181B] mb-4">Your Security Score</h3>
              <div className="flex items-center justify-between mb-6">
                <div>
                  <span
                    className="text-5xl font-bold"
                    style={{
                      color:
                        result.overall_score >= 75
                          ? "#2ECC71"
                          : result.overall_score >= 50
                          ? "#F39C12"
                          : "#E74C3C",
                    }}
                  >
                    {result.overall_score}
                  </span>
                  <span className="text-zinc-400 text-xl">/100</span>
                </div>
                <span
                  className={`px-4 py-2 rounded-full text-sm font-semibold ${
                    result.risk_level === "Low" || result.risk_level === "Low-Medium"
                      ? "bg-green-100 text-green-700"
                      : result.risk_level === "Medium"
                      ? "bg-orange-100 text-orange-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {result.risk_level} Risk
                </span>
              </div>
              
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center p-3 bg-zinc-50 rounded-lg">
                  <div className="text-2xl font-bold text-[#00A8E8]">{result.scores.awareness}%</div>
                  <div className="text-xs text-zinc-500">Awareness</div>
                </div>
                <div className="text-center p-3 bg-zinc-50 rounded-lg">
                  <div className="text-2xl font-bold text-[#18181B]">{result.scores.behavior}%</div>
                  <div className="text-xs text-zinc-500">Behavior</div>
                </div>
                <div className="text-center p-3 bg-zinc-50 rounded-lg">
                  <div className="text-2xl font-bold text-[#2ECC71]">{result.scores.reporting}%</div>
                  <div className="text-xs text-zinc-500">Reporting</div>
                </div>
              </div>

              {/* Risk Profile */}
              {riskProfile.risk_persona && (
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-zinc-600">Your Risk Profile:</span>
                    <span
                      className={`px-3 py-1 rounded text-sm font-semibold ${
                        riskProfile.risk_persona === "Security Aware"
                          ? "bg-green-100 text-green-700"
                          : riskProfile.risk_persona.includes("Critical") || riskProfile.risk_persona.includes("High")
                          ? "bg-red-100 text-red-700"
                          : "bg-orange-100 text-orange-700"
                      }`}
                    >
                      {riskProfile.risk_persona}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-500">{riskProfile.persona_description}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Risk Flags Warning */}
          {riskFlags.length > 0 && (
            <Card className="text-left mb-6 border-l-4 border-l-orange-500">
              <CardContent className="p-6">
                <h3 className="font-semibold text-[#18181B] mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  Areas for Improvement
                </h3>
                <div className="space-y-3">
                  {riskFlags.slice(0, 3).map((flag, index) => (
                    <div
                      key={flag.flag_id}
                      className={`p-3 rounded-lg ${
                        flag.severity === "critical"
                          ? "bg-red-50 border border-red-200"
                          : "bg-orange-50 border border-orange-200"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            flag.severity === "critical"
                              ? "bg-red-200 text-red-800"
                              : "bg-orange-200 text-orange-800"
                          }`}
                        >
                          {flag.severity}
                        </span>
                        <span className="font-medium text-sm text-zinc-700">{flag.title}</span>
                      </div>
                      <p className="text-xs text-zinc-600">{flag.recommendation}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <p className="text-sm text-zinc-500">
            Your responses help {companyName} improve cybersecurity culture.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-white border-b border-zinc-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Brand size="md" />
              <div>
                <p className="text-xs text-zinc-500">{companyName}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-zinc-500">Welcome,</p>
              <p className="font-medium text-[#18181B]">{employee?.name}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Progress */}
      <div className="bg-white border-b border-zinc-200">
        <div className="max-w-3xl mx-auto px-6 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-600">
              Question {currentQuestion + 1} of {questions.length}
            </span>
            <span className="text-sm text-zinc-600">
              {answeredCount} answered
            </span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </div>

      {/* Survey Content */}
      <main className="max-w-3xl mx-auto px-6 py-8">
        {currentQ && (
          <motion.div
            key={currentQ.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-0 shadow-lg">
              <CardContent className="p-8">
                {/* Category Badge */}
                <div className="flex items-center gap-2 mb-4">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${
                      currentQ.category === "awareness"
                        ? "bg-blue-100 text-blue-700"
                        : currentQ.category === "behavior"
                        ? "bg-purple-100 text-purple-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {currentQ.category}
                  </span>
                  {currentQ.risk_weight >= 4 && (
                    <span className="flex items-center gap-1 text-xs text-orange-600">
                      <AlertTriangle className="w-3 h-3" />
                      High Impact
                    </span>
                  )}
                </div>

                {/* Question */}
                <h2 className="text-xl font-semibold text-[#18181B]  mb-6">
                  {currentQ.question}
                </h2>

                {/* Options */}
                <RadioGroup
                  value={responses[currentQ.id]?.toString()}
                  onValueChange={(value) => handleResponse(currentQ.id, parseInt(value))}
                  className="space-y-3"
                >
                  {currentQ.options.map((option, index) => (
                    <div
                      key={index}
                      className={`question-option ${
                        responses[currentQ.id] === index ? "selected" : ""
                      }`}
                      onClick={() => handleResponse(currentQ.id, index)}
                    >
                      <RadioGroupItem
                        value={index.toString()}
                        id={`option-${index}`}
                        className="mr-3"
                      />
                      <Label
                        htmlFor={`option-${index}`}
                        className="flex-1 cursor-pointer text-zinc-700"
                      >
                        {option}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8">
          <Button
            variant="outline"
            onClick={prevQuestion}
            disabled={currentQuestion === 0}
            className="gap-2"
            data-testid="survey-prev-btn"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </Button>

          {currentQuestion < questions.length - 1 ? (
            <Button
              onClick={nextQuestion}
              className="gap-2 bg-[#18181B] hover:bg-[#000000]"
              disabled={responses[currentQ?.id] === undefined}
              data-testid="survey-next-btn"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              onClick={submitSurvey}
              className="gap-2 bg-[#2ECC71] hover:bg-[#27ae60]"
              disabled={submitting || answeredCount < questions.length}
              data-testid="survey-submit-btn"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Submit Survey
                </>
              )}
            </Button>
          )}
        </div>

        {/* Question Navigation Dots */}
        <div className="flex justify-center gap-2 mt-8 flex-wrap">
          {questions.map((q, index) => (
            <button
              key={q.id}
              onClick={() => setCurrentQuestion(index)}
              className={`w-3 h-3 rounded-full transition-all ${
                index === currentQuestion
                  ? "bg-[#00A8E8] scale-125"
                  : responses[q.id] !== undefined
                  ? "bg-[#2ECC71]"
                  : "bg-zinc-300"
              }`}
              title={`Question ${index + 1}`}
            />
          ))}
        </div>
      </main>
    </div>
  );
};

export default EmployeeSurvey;

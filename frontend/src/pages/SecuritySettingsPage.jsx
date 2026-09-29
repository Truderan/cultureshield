import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowLeft, KeyRound, Laptop, Loader2, ShieldCheck, Smartphone } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchWithRetry } from "@/lib/api";
import { useAuth } from "@/App";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function SecuritySettingsPage() {
  const { token, user } = useAuth();
  const location = useLocation();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [setupData, setSetupData] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [working, setWorking] = useState(false);

  const fetchStatus = async () => {
    const { response, data } = await fetchWithRetry(`${API}/auth/mfa/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(data.detail || "Unable to load MFA settings.");
    }
    setStatus(data);
  };

  const fetchSessions = async () => {
    const { response, data } = await fetchWithRetry(`${API}/auth/sessions`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(data.detail || "Unable to load active sessions.");
    }
    setSessions(data.items || []);
    setCurrentSessionId(data.current_session_id || "");
  };

  useEffect(() => {
    const load = async () => {
      try {
        await fetchStatus();
        await fetchSessions();
      } catch (error) {
        toast.error(error.message || "Unable to load security settings.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token]);

  const startSetup = async () => {
    setWorking(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/mfa/setup/init`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(data.detail || "Unable to start MFA setup.");
      }
      setSetupData(data);
      toast.success("Scan the QR code and confirm with a 6-digit code.");
    } catch (error) {
      toast.error(error.message || "Unable to start MFA setup.");
    } finally {
      setWorking(false);
    }
  };

  const confirmSetup = async () => {
    setWorking(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/mfa/setup/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ code: verificationCode }),
      });
      if (!response.ok) {
        throw new Error(data.detail || "Unable to confirm MFA.");
      }
      setSetupData(null);
      setVerificationCode("");
      setStatus(data);
      await fetchSessions();
      toast.success("MFA has been enabled for your account.");
    } catch (error) {
      toast.error(error.message || "Unable to confirm MFA.");
    } finally {
      setWorking(false);
    }
  };

  const disableMfa = async () => {
    setWorking(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/mfa/disable`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ password: disablePassword, code: disableCode }),
      });
      if (!response.ok) {
        throw new Error(data.detail || "Unable to disable MFA.");
      }
      setDisablePassword("");
      setDisableCode("");
      setStatus(data);
      await fetchSessions();
      toast.success("MFA disabled successfully.");
    } catch (error) {
      toast.error(error.message || "Unable to disable MFA.");
    } finally {
      setWorking(false);
    }
  };

  const revokeSession = async (sessionId) => {
    setWorking(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/sessions/${sessionId}/revoke`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(data.detail || "Unable to revoke that session.");
      }
      await fetchSessions();
      toast.success(data.message || "Session revoked.");
    } catch (error) {
      toast.error(error.message || "Unable to revoke that session.");
    } finally {
      setWorking(false);
    }
  };

  const revokeAllOtherSessions = async () => {
    setWorking(true);
    try {
      const { response, data } = await fetchWithRetry(`${API}/auth/sessions/revoke-all`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(data.detail || "Unable to revoke other sessions.");
      }
      await fetchSessions();
      toast.success(data.message || "Other sessions revoked.");
    } catch (error) {
      toast.error(error.message || "Unable to revoke other sessions.");
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-background" data-testid="security-settings-loading"><Loader2 className="h-8 w-8 animate-spin text-[#00A8E8]" /></div>;
  }

  return (
    <div className="min-h-screen bg-background p-6" data-testid="security-settings-page">
      <div className="mx-auto max-w-5xl space-y-6">
        <Link to="/dashboard" className="inline-flex items-center gap-2 text-zinc-600 hover:text-[#18181B]" data-testid="security-settings-back-link">
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <Card className="rounded-[28px] border-zinc-200">
            <CardHeader>
              <CardTitle className=" text-3xl text-[#18181B]">Security settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 text-zinc-600">
              <div className="rounded-2xl bg-zinc-50 p-5" data-testid="security-account-summary">
                <p className="text-sm uppercase tracking-[0.18em] text-zinc-400">Admin account</p>
                <p className="mt-2  text-2xl font-bold text-[#18181B]">{user?.company_name}</p>
                <p className="mt-1 text-sm">{user?.email}</p>
              </div>

              {location.state?.enforceSetup && !status?.enabled && (
                <div className="rounded-2xl border border-[#00A8E8]/30 bg-[#00A8E8]/10 p-4 text-sm text-[#18181B]" data-testid="security-mfa-enforced-banner">
                  MFA is recommended for all admin accounts. Complete setup now to harden your account.
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-zinc-200 p-4" data-testid="security-mfa-status-card">
                  <p className="text-sm text-zinc-500">MFA status</p>
                  <p className="mt-2  text-2xl font-bold text-[#18181B]">{status?.enabled ? "Enabled" : "Not enabled"}</p>
                </div>
                <div className="rounded-2xl border border-zinc-200 p-4" data-testid="security-backup-codes-card">
                  <p className="text-sm text-zinc-500">Backup codes left</p>
                  <p className="mt-2  text-2xl font-bold text-[#18181B]">{status?.backup_codes_remaining ?? 0}</p>
                </div>
              </div>

              {!status?.enabled ? (
                <Button className="bg-[#18181B] text-white hover:bg-[#000000]" onClick={startSetup} disabled={working} data-testid="security-start-mfa-button">
                  <Smartphone className="mr-2 h-4 w-4" /> Enable MFA
                </Button>
              ) : (
                <div className="space-y-4 rounded-2xl border border-zinc-200 p-5" data-testid="security-disable-mfa-panel">
                  <p className="font-medium text-[#18181B]">Disable MFA</p>
                  <div className="space-y-2">
                    <Label>Password</Label>
                    <Input type="password" value={disablePassword} onChange={(event) => setDisablePassword(event.target.value)} data-testid="security-disable-password-input" />
                  </div>
                  <div className="space-y-2">
                    <Label>Authenticator or backup code</Label>
                    <Input value={disableCode} onChange={(event) => setDisableCode(event.target.value)} data-testid="security-disable-code-input" />
                  </div>
                  <Button variant="outline" className="border-red-300 text-red-600 hover:bg-red-50" onClick={disableMfa} disabled={working} data-testid="security-disable-mfa-button">
                    Disable MFA
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-[28px] border-zinc-200">
            <CardHeader>
              <CardTitle className=" text-3xl text-[#18181B]">Authenticator setup</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {setupData ? (
                <div className="space-y-5" data-testid="security-mfa-setup-panel">
                  <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-600">
                    Scan the QR code with Google Authenticator or any TOTP-compatible app, then enter the 6-digit code to finish setup.
                  </div>
                  <div className="flex justify-center rounded-2xl border border-zinc-200 p-5">
                    <img src={setupData.qr_code_data_url} alt="MFA QR code" className="h-56 w-56" data-testid="security-mfa-qr-image" />
                  </div>
                  <div className="rounded-2xl border border-dashed border-zinc-300 p-4" data-testid="security-mfa-manual-key">
                    <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">Manual entry key</p>
                    <p className="mt-2 break-all font-mono text-sm text-[#18181B]">{setupData.manual_entry_key}</p>
                  </div>
                  <div className="rounded-2xl bg-amber-50 p-4" data-testid="security-mfa-backup-codes-list">
                    <p className="font-medium text-amber-800">Save these backup codes now</p>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {setupData.backup_codes.map((code) => (
                        <div key={code} className="rounded-lg bg-white px-3 py-2 font-mono text-sm text-[#18181B]">{code}</div>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Authenticator code</Label>
                    <Input value={verificationCode} onChange={(event) => setVerificationCode(event.target.value)} placeholder="123456" data-testid="security-mfa-confirm-code-input" />
                  </div>
                  <Button className="w-full bg-[#18181B] text-white hover:bg-[#000000]" onClick={confirmSetup} disabled={working} data-testid="security-mfa-confirm-button">
                    {working ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Confirming...</> : <><ShieldCheck className="mr-2 h-4 w-4" /> Confirm & enable MFA</>}
                  </Button>
                </div>
              ) : (
                <div className="rounded-2xl bg-zinc-50 p-5 text-sm text-zinc-600" data-testid="security-mfa-setup-empty-state">
                  Start MFA setup to generate a QR code, backup codes, and authenticator instructions for your admin account.
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <Card className="rounded-[28px] border-zinc-200" data-testid="trusted-devices-panel">
          <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className=" text-3xl text-[#18181B]">Trusted devices & active sessions</CardTitle>
              <p className="mt-2 text-sm text-zinc-500">Monitor recent logins, spot unusual access, and revoke sessions you no longer trust.</p>
            </div>
            <Button variant="outline" className="border-zinc-300" onClick={revokeAllOtherSessions} disabled={working} data-testid="revoke-all-other-sessions-button">
              Revoke all other sessions
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {sessions.length ? sessions.map((session) => (
              <div key={session.id} className="rounded-2xl border border-zinc-200 p-4" data-testid={`session-row-${session.id}`}>
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[#18181B]">
                      <Laptop className="h-4 w-4" />
                      <p className="font-semibold" data-testid={`session-device-name-${session.id}`}>{session.device_name}</p>
                      {session.is_current && <span className="rounded-full bg-[#18181B]/10 px-2 py-1 text-xs font-semibold text-[#18181B]" data-testid={`session-current-badge-${session.id}`}>Current</span>}
                    </div>
                    <p className="text-sm text-zinc-500" data-testid={`session-ip-${session.id}`}>{session.ip_address} • {session.browser} • {session.os}</p>
                    <p className="text-xs text-zinc-400">Started {new Date(session.created_at).toLocaleString()} • Last active {new Date(session.last_active_at).toLocaleString()}</p>
                    <div className="flex flex-wrap gap-2">
                      {session.mfa_verified ? (
                        <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700" data-testid={`session-mfa-badge-${session.id}`}>MFA verified</span>
                      ) : (
                        <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700" data-testid={`session-password-only-badge-${session.id}`}>Password only</span>
                      )}
                      {session.risk_flags.map((flag) => (
                        <span key={flag} className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-700" data-testid={`session-risk-${session.id}-${flag}`}>
                          <AlertTriangle className="h-3 w-3" /> {flag}
                        </span>
                      ))}
                    </div>
                  </div>
                  {!session.is_current && (
                    <Button variant="outline" className="border-red-300 text-red-600 hover:bg-red-50" onClick={() => revokeSession(session.id)} disabled={working} data-testid={`revoke-session-button-${session.id}`}>
                      Revoke session
                    </Button>
                  )}
                </div>
              </div>
            )) : (
              <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500" data-testid="trusted-devices-empty-state">
                No active sessions found yet.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
import { AlertTriangle, CheckCircle2, Download, Mail, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const statusStyles = {
  sent: "bg-emerald-50 text-emerald-700 border-emerald-200",
  failed: "bg-red-50 text-red-700 border-red-200",
  skipped: "bg-amber-50 text-amber-700 border-amber-200",
};

export const EmailActivityPanel = ({ activity, onDownload, downloading }) => {
  const summary = activity?.summary || { total: 0, sent: 0, failed: 0, skipped: 0 };
  const items = activity?.items || [];

  return (
    <Card className="rounded-[28px] border-zinc-200" data-testid="email-activity-panel">
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle className=" text-2xl text-[#18181B]">Email activity & history</CardTitle>
          <p className="mt-2 text-sm text-zinc-500">Track invites, billing emails, report notices, and delivery outcomes for your company.</p>
        </div>
        <Button variant="outline" className="border-zinc-300" onClick={onDownload} data-testid="download-email-history-button">
          <Download className="mr-2 h-4 w-4" />
          {downloading ? "Preparing CSV..." : "Download CSV"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl bg-zinc-50 p-4" data-testid="email-activity-total-card">
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">Total</p>
            <p className="mt-2  text-3xl font-bold text-[#18181B]">{summary.total}</p>
          </div>
          <div className="rounded-2xl bg-emerald-50 p-4" data-testid="email-activity-sent-card">
            <p className="text-xs uppercase tracking-[0.18em] text-emerald-600">Sent</p>
            <p className="mt-2  text-3xl font-bold text-emerald-700">{summary.sent}</p>
          </div>
          <div className="rounded-2xl bg-red-50 p-4" data-testid="email-activity-failed-card">
            <p className="text-xs uppercase tracking-[0.18em] text-red-600">Failed</p>
            <p className="mt-2  text-3xl font-bold text-red-700">{summary.failed}</p>
          </div>
          <div className="rounded-2xl bg-amber-50 p-4" data-testid="email-activity-skipped-card">
            <p className="text-xs uppercase tracking-[0.18em] text-amber-600">Skipped</p>
            <p className="mt-2  text-3xl font-bold text-amber-700">{summary.skipped}</p>
          </div>
        </div>

        {items.length ? (
          <div className="space-y-3">
            {items.map((item) => {
              const icon = item.status === "sent" ? CheckCircle2 : item.status === "failed" ? XCircle : AlertTriangle;
              const StatusIcon = icon;
              return (
                <div key={item.id} className="grid gap-4 rounded-2xl border border-zinc-200 p-4 md:grid-cols-[1.2fr_0.8fr_0.7fr_1fr] md:items-center" data-testid={`email-activity-row-${item.id}`}>
                  <div>
                    <div className="flex items-center gap-2 text-[#18181B]">
                      <Mail className="h-4 w-4" />
                      <p className="font-semibold">{item.subject}</p>
                    </div>
                    <p className="mt-1 text-sm text-zinc-500">{item.recipient_email}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-zinc-700">{item.email_type.replace(/_/g, " ")}</p>
                    <p className="text-xs text-zinc-400">{new Date(item.created_at).toLocaleString()}</p>
                  </div>
                  <div>
                    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold capitalize ${statusStyles[item.status] || statusStyles.skipped}`} data-testid={`email-activity-status-${item.id}`}>
                      <StatusIcon className="h-3.5 w-3.5" />
                      {item.status}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-500" data-testid={`email-activity-message-${item.id}`}>
                    {item.provider_message || "Delivered via Resend"}
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500" data-testid="email-activity-empty-state">
            Email events will appear here after welcomes, invites, billing updates, and report notifications are triggered.
          </div>
        )}
      </CardContent>
    </Card>
  );
};
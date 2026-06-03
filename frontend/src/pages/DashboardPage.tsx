import { useEffect, useState } from "react";
import { getHealth } from "../lib/api/health";
import { downloadInvestigationReport } from "../lib/api/report";
import { getInvestigation, runInvestigation } from "../lib/api/investigation";
import { InvestigationChat } from "../components/chat/InvestigationChat";
import { SensorLogUpload } from "../components/upload/SensorLogUpload";
import type { InvestigationRun } from "../types/investigation";
import type { ReportFormat } from "../lib/api/report";

function StatusIndicator({ status }: { status: string }) {
  const isOnline = status === "ok";
  return (
    <div className="flex items-center gap-2">
      <span
        className={`h-2 w-2 rounded-full ${
          isOnline ? "bg-[hsl(var(--primary))] shadow-[0_0_8px_hsl(var(--primary))]" : "bg-amber-500"
        }`}
      />
      <span className="text-sm capitalize text-[hsl(var(--muted-foreground))]">
        {status === "loading" ? "Checking..." : status}
      </span>
    </div>
  );
}

export function DashboardPage() {
  const [backendHealth, setBackendHealth] = useState("loading");
  const [sessionId, setSessionId] = useState("");
  const [uploadId, setUploadId] = useState("");
  const [investigationId, setInvestigationId] = useState<number | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationRun | null>(null);
  const [reportFormat, setReportFormat] = useState<ReportFormat>("pdf");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    async function bootstrap() {
      try {
        const health = await getHealth();
        setBackendHealth(health.status);
      } catch {
        setBackendHealth("offline");
      }

      if (typeof window !== "undefined") {
        let sid = window.localStorage.getItem("investigation_copilot_session_id");
        if (!sid) {
          sid = crypto.randomUUID();
          window.localStorage.setItem("investigation_copilot_session_id", sid);
        }
        setSessionId(sid);

        const savedUploadId = window.localStorage.getItem("investigation_copilot_last_upload_id");
        if (savedUploadId) setUploadId(savedUploadId);

        const savedInvestigationId = window.localStorage.getItem("investigation_copilot_last_investigation_id");
        if (savedInvestigationId) {
          const id = Number(savedInvestigationId);
          setInvestigationId(id);
          try {
            const loaded = await getInvestigation(id);
            setInvestigation(loaded);
          } catch {
            // ignore load errors on initial restore
          }
        }
      }
    }

    bootstrap();
  }, []);

  const clearNotifications = () => {
    setMessage(null);
    setError(null);
  };

  const runInvestigationFromUpload = async (upload: string) => {
    clearNotifications();
    if (!upload.trim()) {
      setError("Upload ID is required to run an investigation.");
      return;
    }

    setWorking(true);
    try {
      const result = await runInvestigation(upload.trim());
      setInvestigation(result);
      setInvestigationId(result.investigation_id);
      setMessage("Investigation completed.");
      if (typeof window !== "undefined") {
        window.localStorage.setItem("investigation_copilot_last_investigation_id", String(result.investigation_id));
      }
    } catch (err: unknown) {
      setError(
        err && typeof err === "object" && "response" in err && err.response && typeof err.response === "object" && "data" in err.response && err.response.data && typeof err.response.data === "object" && "detail" in err.response.data
          ? String(err.response.data.detail)
          : "Failed to run investigation. Check backend logs."
      );
    } finally {
      setWorking(false);
    }
  };

  const handleUploadComplete = async (result: { upload_id: string; records: number }) => {
    setUploadId(result.upload_id);
    setUploadMessage(`Uploaded ${result.records} records — investigation starting automatically.`);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("investigation_copilot_last_upload_id", result.upload_id);
    }
    await runInvestigationFromUpload(result.upload_id);
  };

  const handleDownloadReport = async () => {
    clearNotifications();
    if (!investigationId || investigationId <= 0) {
      setError("Run an investigation before downloading a report.");
      return;
    }

    try {
      const blob = await downloadInvestigationReport(investigationId, reportFormat);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = reportFormat === "pptx" ? "investigation-report.pptx" : "investigation-report.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage(`Report downloaded as ${reportFormat.toUpperCase()}.`);
    } catch (err: unknown) {
      setError(
        err && typeof err === "object" && "response" in err && err.response && typeof err.response === "object" && "data" in err.response && err.response.data && typeof err.response.data === "object" && "detail" in err.response.data
          ? String(err.response.data.detail)
          : "Failed to generate report."
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[hsl(var(--foreground))]">Dashboard</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Upload sensor data, run investigations, and chat with your findings.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <StatusIndicator status={backendHealth} />
          <div className="h-4 w-px bg-[hsl(var(--border))]" />
          <span className="max-w-[140px] truncate text-xs text-[hsl(var(--muted-foreground))]" title={sessionId}>
            Session: {sessionId.slice(0, 8)}...
          </span>
        </div>
      </div>

      {/* Notification Alerts */}
      {message && (
        <div className="flex items-center gap-3 rounded-lg border border-[hsl(var(--primary))/0.3] bg-[hsl(var(--primary))/0.1] px-4 py-3">
          <svg className="h-4 w-4 text-[hsl(var(--primary))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-sm text-[hsl(var(--primary))]">{message}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-[hsl(var(--destructive))/0.3] bg-[hsl(var(--destructive))/0.1] px-4 py-3">
          <svg className="h-4 w-4 text-[hsl(var(--destructive))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm text-[hsl(var(--destructive))]">{error}</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Upload Card */}
          <div className="overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
            <div className="border-b border-[hsl(var(--border))] px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[hsl(var(--secondary))]">
                  <svg className="h-4 w-4 text-[hsl(var(--foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-sm font-medium text-[hsl(var(--foreground))]">Upload & Investigate</h2>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Upload sensor logs to start analysis</p>
                </div>
              </div>
            </div>
            <div className="p-5">
              <div className="grid gap-5 md:grid-cols-2">
                <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                  <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    Sensor Log Upload
                  </p>
                  <SensorLogUpload onUploadComplete={handleUploadComplete} />
                  {uploadMessage && (
                    <p className="mt-3 text-xs text-[hsl(var(--primary))]">{uploadMessage}</p>
                  )}
                </div>
                <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                  <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    Investigation Progress
                  </p>
                  <div className="flex items-center gap-3">
                    {working ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent" />
                        <span className="text-sm text-[hsl(var(--foreground))]">Running...</span>
                      </>
                    ) : (
                      <>
                        <div className="h-2 w-2 rounded-full bg-[hsl(var(--muted-foreground))]" />
                        <span className="text-sm text-[hsl(var(--muted-foreground))]">Ready</span>
                      </>
                    )}
                  </div>
                  {investigationId && (
                    <p className="mt-3 text-xs text-[hsl(var(--muted-foreground))]">
                      Investigation #{investigationId}
                    </p>
                  )}
                  {uploadId && (
                    <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                      Upload: {uploadId.slice(0, 12)}...
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Report Card */}
          <div className="overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
            <div className="border-b border-[hsl(var(--border))] px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[hsl(var(--secondary))]">
                  <svg className="h-4 w-4 text-[hsl(var(--foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-sm font-medium text-[hsl(var(--foreground))]">Report Download</h2>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Generate PDF or PPTX reports</p>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between p-5">
              <div className="flex gap-2">
                {(["pdf", "pptx"] as ReportFormat[]).map((format) => (
                  <button
                    key={format}
                    type="button"
                    onClick={() => setReportFormat(format)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium uppercase tracking-wide transition-colors ${
                      reportFormat === format
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                        : "border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))]"
                    }`}
                  >
                    {format}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={handleDownloadReport}
                className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--foreground))] px-4 py-2 text-sm font-medium text-[hsl(var(--background))] transition-opacity hover:opacity-90"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download
              </button>
            </div>
          </div>

          {/* Findings Card */}
          <div className="overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
            <div className="border-b border-[hsl(var(--border))] px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[hsl(var(--secondary))]">
                  <svg className="h-4 w-4 text-[hsl(var(--foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-sm font-medium text-[hsl(var(--foreground))]">Investigation Findings</h2>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Current investigation summary</p>
                </div>
              </div>
            </div>
            <div className="p-5">
              {investigation ? (
                <div className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                      <p className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                        Status
                      </p>
                      <p className="mt-2 text-lg font-semibold capitalize text-[hsl(var(--foreground))]">
                        {investigation.status}
                      </p>
                    </div>
                    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                      <p className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                        Upload ID
                      </p>
                      <p className="mt-2 truncate text-lg font-semibold text-[hsl(var(--foreground))]">
                        {investigation.upload_id}
                      </p>
                    </div>
                  </div>
                  <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                    <p className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Summary
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-[hsl(var(--foreground))]">
                      {investigation.state.summary || "No summary available yet."}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[hsl(var(--secondary))]">
                    <svg className="h-6 w-6 text-[hsl(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                  </div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    No investigation loaded yet
                  </p>
                  <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                    Upload a CSV file to start
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Chat */}
        <div className="lg:sticky lg:top-20 lg:h-[calc(100vh-112px)]">
          <div className="flex h-full flex-col overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
            <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[hsl(var(--primary))]">
                  <svg className="h-4 w-4 text-[hsl(var(--primary-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-sm font-medium text-[hsl(var(--foreground))]">Engineering Chat</h2>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Ask questions about findings</p>
                </div>
              </div>
              <span className="rounded-full bg-[hsl(var(--secondary))] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                AI
              </span>
            </div>
            <div className="flex-1 overflow-hidden">
              <InvestigationChat investigationId={investigationId ?? 0} sessionId={sessionId} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

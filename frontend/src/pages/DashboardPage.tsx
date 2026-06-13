import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getHealth } from "../lib/api/health";
import { downloadInvestigationReport, previewInvestigationReport } from "../lib/api/report";
import { getInvestigation, runInvestigation } from "../lib/api/investigation";
import { InvestigationChat } from "../components/chat/InvestigationChat";
import { SensorLogUpload } from "../components/upload/SensorLogUpload";
import type { InvestigationRun, StructuredSummary } from "../types/investigation";
import type { ReportFormat } from "../lib/api/report";

type TelemetryMeasurements = {
  temperature?: number;
  pressure?: number;
  vibration?: number;
  rpm?: number;
};

type TelemetryAnomaly = {
  temperature_spike?: boolean;
  pressure_drop?: boolean;
  vibration_spike?: boolean;
  rpm_drop?: boolean;
  risk?: string;
  latest_measurements?: TelemetryMeasurements;
  signals?: TelemetryMeasurements;
};

type HistoricalIncident = {
  incident_id?: number;
  similarity?: number;
  failure?: string;
  root_cause?: string;
  issue_url?: string;
  source_type?: string;
};

type InvestigationStateView = {
  investigation_id?: number | null;
  sensor_rows?: Array<{
    timestamp?: string | null;
    temperature?: number | null;
    pressure?: number | null;
    vibration?: number | null;
    rpm?: number | null;
  }>;
  risk_level?: string;
  anomalies?: TelemetryAnomaly[];
  incidents?: HistoricalIncident[];
  github_matches?: HistoricalIncident[];
  github_match_status?: string;
  summary?: string;
  summary_text?: string;
  summary_sections?: StructuredSummary;
  github_issue_status?: string;
  github_issue_id?: number | null;
  github_issue_url?: string;
  github_issue_detail?: string;
  technical_report_status?: string;
  technical_report_filename?: string;
  technical_report_path?: string;
  technical_report_preview?: string;
};

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

function PanelSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">{title}</p>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export function DashboardPage() {
  const [backendHealth, setBackendHealth] = useState("loading");
  const [sessionId, setSessionId] = useState("");
  const [uploadId, setUploadId] = useState("");
  const [investigationId, setInvestigationId] = useState<number | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationRun | null>(null);
  const [chatHistoryOpen, setChatHistoryOpen] = useState(false);
  const [reportFormat, setReportFormat] = useState<ReportFormat>("pdf");
  const [reportPreview, setReportPreview] = useState<string | null>(null);
  const [reportPreviewLoading, setReportPreviewLoading] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [insightsOpen, setInsightsOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const cacheKeys = {
    lastUploadId: "investigation_copilot_last_upload_id",
    lastInvestigationId: "investigation_copilot_last_investigation_id",
    lastInvestigation: "investigation_copilot_last_investigation",
    investigation: (id: number) => `investigation_copilot_investigation_${id}`,
  };

  const investigationState = investigation?.state as InvestigationStateView | undefined;
  const latestAnomaly = investigationState?.anomalies?.[0];
  const topIncident = investigationState?.incidents?.[0];
  const topSimilarity = topIncident?.similarity ?? 0;
  const telemetryRows = Array.isArray(investigationState?.sensor_rows) ? investigationState.sensor_rows : [];
  const telemetryChartData = telemetryRows.map((row, index) => ({
    t: row.timestamp ? row.timestamp.slice(11, 19) || String(index + 1) : String(index + 1),
    temperature: Number(row.temperature ?? 0),
    pressure: Number(row.pressure ?? 0),
    vibration: Number(row.vibration ?? 0),
    rpm: Number(row.rpm ?? 0),
  }));
  const structuredSummary = investigationState?.summary_sections;
  const riskLevel =
    investigationState?.risk_level ||
    latestAnomaly?.risk ||
    "Unknown";
  const summaryText =
    investigationState?.summary_text ||
    (typeof investigationState?.summary === "string" ? investigationState.summary : "") ||
    "No summary available yet.";
  const githubMatches = investigationState?.github_matches ?? [];
  const githubMatchStatus = investigationState?.github_match_status || "unknown";

  const clearNotifications = () => {
    setMessage(null);
    setError(null);
  };

  const persistInvestigation = (payload: InvestigationRun) => {
    setInvestigation(payload);
    setInvestigationId(payload.investigation_id);
    setUploadId(payload.upload_id);
    if (typeof window === "undefined") return;

    window.localStorage.removeItem(cacheKeys.lastInvestigationId);
    window.localStorage.removeItem(cacheKeys.lastInvestigation);
    window.localStorage.removeItem(cacheKeys.investigation(payload.investigation_id));
    window.localStorage.removeItem(cacheKeys.lastUploadId);
  };

  const loadInvestigationById = async (id: number) => {
    if (!Number.isFinite(id) || id <= 0) return;
    clearNotifications();
    setInvestigationId(id);

    try {
      const loaded = await getInvestigation(id);
      persistInvestigation(loaded);
    } catch {
      // keep cached view if backend is offline
    }
  };

  useEffect(() => {
    async function bootstrap() {
      try {
        const health = await getHealth();
        setBackendHealth(health.status);
      } catch {
        setBackendHealth("offline");
      }

      if (typeof window === "undefined") return;

      let sid = window.localStorage.getItem("investigation_copilot_session_id");
      if (!sid) {
        sid = crypto.randomUUID();
        window.localStorage.setItem("investigation_copilot_session_id", sid);
      }
      setSessionId(sid);

      setInvestigation(null);
      setInvestigationId(null);
      setUploadId("");
    }

    bootstrap();
  }, []);

  const runInvestigationFromUpload = async (upload: string) => {
    clearNotifications();
    if (!upload.trim()) {
      setError("Upload ID is required to run an investigation.");
      return;
    }

    setWorking(true);
    try {
      const result = await runInvestigation(upload.trim());
      persistInvestigation(result);
      setInsightsOpen(true);
      setMessage(
        result.status === "no_relevant_historical_match"
          ? "Investigation stopped: no sufficiently similar historical match was found for this upload."
          : "Investigation completed."
      );
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
    setUploadMessage(`Uploaded ${result.records} records - investigation starting automatically.`);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(cacheKeys.lastUploadId, result.upload_id);
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
      link.download =
        reportFormat === "pptx"
          ? "investigation-report.pptx"
          : reportFormat === "md"
            ? "investigation-report.md"
            : "investigation-report.pdf";
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

  const handlePreviewReport = async () => {
    clearNotifications();
    if (!investigationId || investigationId <= 0) {
      setError("Run an investigation before previewing a report.");
      return;
    }

    setPreviewModalOpen(true);
    const cachedPreview = investigationState?.technical_report_preview?.trim();
    if (cachedPreview) {
      setReportPreview(cachedPreview);
      setReportPreviewLoading(false);
      return;
    }

    setReportPreviewLoading(true);
    setReportPreview(null);
    try {
      const preview = await previewInvestigationReport(investigationId);
      setReportPreview(preview.markdown);
      setMessage(`Loaded report preview for investigation #${preview.investigation_id}.`);
    } catch (err: unknown) {
      setError(
        err && typeof err === "object" && "response" in err && err.response && typeof err.response === "object" && "data" in err.response && err.response.data && typeof err.response.data === "object" && "detail" in err.response.data
          ? String(err.response.data.detail)
          : "Failed to preview report."
      );
    } finally {
      setReportPreviewLoading(false);
    }
  };

  const closePreviewModal = () => {
    setPreviewModalOpen(false);
    setReportPreview(null);
    setReportPreviewLoading(false);
  };

  const renderSummaryList = (items: string[] | undefined, emptyLabel: string) => {
    const list = items?.length ? items : [emptyLabel];
    return (
      <ul className="space-y-2 text-sm text-[hsl(var(--foreground))]">
        {list.map((item) => (
          <li key={item} className="rounded-lg bg-[hsl(var(--background))] px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="relative space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[hsl(var(--foreground))]">Dashboard</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Upload sensor data, run investigations, and chat with your findings.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <StatusIndicator status={backendHealth} />
          <span className="max-w-[160px] truncate text-xs text-[hsl(var(--muted-foreground))]" title={sessionId}>
            Session: {sessionId.slice(0, 8)}...
          </span>
        </div>
      </div>

      {message && (
        <div
          className={`flex items-center gap-3 rounded-lg px-4 py-3 ${
            message.toLowerCase().includes("stopped")
              ? "border border-amber-500/30 bg-amber-500/10"
              : "border border-[hsl(var(--primary))/0.3] bg-[hsl(var(--primary))/0.1]"
          }`}
        >
          <span className={`text-sm ${message.toLowerCase().includes("stopped") ? "text-amber-700" : "text-[hsl(var(--primary))]"}`}>
            {message}
          </span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-[hsl(var(--destructive))/0.3] bg-[hsl(var(--destructive))/0.1] px-4 py-3">
          <span className="text-sm text-[hsl(var(--destructive))]">{error}</span>
        </div>
      )}

      {previewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-6 backdrop-blur-sm">
          <div className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] shadow-2xl">
            <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-5 py-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                  Technical Report Preview
                </p>
                <p className="text-sm text-[hsl(var(--foreground))]">
                  Markdown output for investigation #{investigationId}
                </p>
              </div>
              <button
                type="button"
                onClick={closePreviewModal}
                className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-1.5 text-xs font-medium text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--secondary))]"
              >
                Close
              </button>
            </div>
            <div className="flex-1 overflow-hidden p-5">
              {reportPreviewLoading && !reportPreview ? (
                <div className="flex h-full items-center justify-center rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))]">
                  <div className="flex items-center gap-3 text-sm text-[hsl(var(--muted-foreground))]">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent" />
                    Loading report preview...
                  </div>
                </div>
              ) : (
                <pre className="h-full overflow-auto whitespace-pre-wrap rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4 text-xs leading-relaxed text-[hsl(var(--foreground))]">
                  {reportPreview || "No preview content available."}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {!insightsOpen && (
        <button
          type="button"
          onClick={() => setInsightsOpen(true)}
          className="fixed left-0 top-20 z-30 flex items-center justify-center rounded-r-2xl border border-l-0 border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-4 shadow-2xl transition-colors hover:bg-[hsl(var(--secondary))]"
          aria-label="Open investigation panel"
          title="Open investigation panel"
        >
          <svg className="h-5 w-5 text-[hsl(var(--foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <div className="overflow-hidden rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
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
                <PanelSection title="Sensor Log Upload">
                  <p className="mb-3 text-xs text-[hsl(var(--muted-foreground))]">
                    Last upload: <span className="font-mono text-[hsl(var(--foreground))]">{uploadId || "none"}</span>
                  </p>
                  <div className="mb-3 rounded-lg border border-amber-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-700">
                    This MVP is tuned for NASA C-MAPSS-style turbofan telemetry. If the upload is outside that domain and no strong historical match is found, the investigation will stop instead of guessing.
                  </div>
                  <SensorLogUpload onUploadComplete={handleUploadComplete} />
                  {uploadMessage && <p className="mt-3 text-xs text-[hsl(var(--primary))]">{uploadMessage}</p>}
                  {investigation?.status === "no_relevant_historical_match" && (
                    <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700">
                      Investigation stopped because the upload did not match the current NASA-based historical knowledge base closely enough. Please upload a turbofan-style sensor log or expand the knowledge base for other equipment.
                    </div>
                  )}
                </PanelSection>

                <PanelSection title="Investigation Progress">
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
                  {investigation && (
                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-3">
                        <p className="text-[11px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Status</p>
                        <p className="mt-1 text-sm font-semibold capitalize">{investigation.status}</p>
                      </div>
                      <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-3">
                        <p className="text-[11px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Risk</p>
                        <p className="mt-1 text-sm font-semibold capitalize">{riskLevel}</p>
                      </div>
                      <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-3">
                        <p className="text-[11px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Investigation</p>
                        <p className="mt-1 text-sm font-semibold">{investigation.investigation_id}</p>
                      </div>
                    </div>
                  )}
                </PanelSection>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:sticky lg:top-20 lg:h-[calc(100vh-112px)]">
          <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
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
              <button
                type="button"
                onClick={() => setChatHistoryOpen(true)}
                className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))]"
                title="Chat history"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <InvestigationChat
                investigationId={investigationId ?? 0}
                sessionId={sessionId}
                onSelectInvestigationId={loadInvestigationById}
                historyOpen={chatHistoryOpen}
                onCloseHistory={() => setChatHistoryOpen(false)}
              />
            </div>
          </div>
        </div>
      </div>

      <aside
        className={`fixed left-0 top-[2rem] z-20 h-[calc(100vh-2rem)] w-[min(42rem,calc(100vw-2rem))] overflow-hidden border-r border-[hsl(var(--border))] bg-[hsl(var(--card))] shadow-2xl transition-transform duration-300 ${
          insightsOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-5 py-4">
            <div>
              <h2 className="text-sm font-medium text-[hsl(var(--foreground))]">Investigation Panel</h2>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Report, findings, and telemetry</p>
            </div>
            <button
              type="button"
              onClick={() => setInsightsOpen(false)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--secondary))]"
              aria-label="Hide investigation panel"
              title="Hide investigation panel"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            <div className="overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Report Download</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Generate PDF or markdown previews</p>
                </div>
                <div className="flex gap-2">
                  {(["pdf", "pptx", "md"] as ReportFormat[]).map((format) => (
                    <button
                      key={format}
                      type="button"
                      onClick={() => setReportFormat(format)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium uppercase tracking-wide ${
                        reportFormat === format
                          ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                          : "border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))]"
                      }`}
                    >
                      {format}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handlePreviewReport}
                  className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 text-sm font-medium text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--secondary))]"
                >
                  {reportPreviewLoading ? "Loading..." : "Preview"}
                </button>
                <button
                  type="button"
                  onClick={handleDownloadReport}
                  className="rounded-lg bg-[hsl(var(--foreground))] px-4 py-2 text-sm font-medium text-[hsl(var(--background))] transition-opacity hover:opacity-90"
                >
                  Download
                </button>
              </div>
            </div>

            {/* {investigationState?.technical_report_status === "generated" && (
              <PanelSection title="Technical Report Ready">
                <p className="text-sm text-[hsl(var(--foreground))]">
                  {investigationState.technical_report_filename || "technical_report"}
                </p>
                {investigationState.technical_report_path && (
                  <p className="mt-1 break-all text-xs text-[hsl(var(--muted-foreground))]">
                    Saved at: {investigationState.technical_report_path}
                  </p>
                )}
                <div className="mt-3">
                  <button
                    type="button"
                    onClick={() => {
                      setReportFormat("md");
                      void handleDownloadReport();
                    }}
                    className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-xs font-medium text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--secondary))]"
                  >
                    Download Markdown
                  </button>
                </div>
              </PanelSection>
            )} */}

            <PanelSection title="Summary Report">
              {working ? (
                <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                  <div className="space-y-4">
                    <div className="h-4 w-44 animate-pulse rounded bg-[hsl(var(--secondary))]" />
                    <div className="h-24 animate-pulse rounded-xl bg-[hsl(var(--secondary))]" />
                    <div className="grid gap-3">
                      <div className="h-20 animate-pulse rounded-xl bg-[hsl(var(--secondary))]" />
                      <div className="h-20 animate-pulse rounded-xl bg-[hsl(var(--secondary))]" />
                      <div className="h-20 animate-pulse rounded-xl bg-[hsl(var(--secondary))]" />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid gap-3">
                  <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Overview
                    </p>
                    <p className="mt-2 text-sm leading-relaxed">{structuredSummary?.overview || summaryText}</p>
                  </div>

                  <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Anomalies
                    </p>
                    <div className="mt-3">{renderSummaryList(structuredSummary?.anomalies, "No major anomaly pattern identified")}</div>
                  </div>

                  <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Root Causes
                    </p>
                    <div className="mt-3">
                      <ul className="space-y-2 text-sm text-[hsl(var(--foreground))]">
                        {(structuredSummary?.root_causes?.length ? structuredSummary.root_causes : []).map((item) => (
                          <li key={`${item.cause}-${item.confidence}`} className="rounded-lg bg-[hsl(var(--background))] px-3 py-2">
                            <div className="flex items-center justify-between gap-3">
                              <span>{item.cause || "Unknown cause"}</span>
                              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                                {typeof item.confidence === "number" ? `${item.confidence}% confidence` : "confidence n/a"}
                              </span>
                            </div>
                          </li>
                        ))}
                        {!structuredSummary?.root_causes?.length && (
                          <li className="rounded-lg bg-[hsl(var(--background))] px-3 py-2 text-[hsl(var(--muted-foreground))]">
                            No validated root causes were identified.
                          </li>
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </PanelSection>

            <PanelSection title="Institutional Knowledge Search">
              {working ? (
                <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                  <div className="space-y-3">
                    <div className="h-4 w-52 animate-pulse rounded bg-[hsl(var(--secondary))]" />
                    <div className="space-y-2">
                      <div className="h-16 animate-pulse rounded-lg bg-[hsl(var(--secondary))]" />
                      <div className="h-16 animate-pulse rounded-lg bg-[hsl(var(--secondary))]" />
                      <div className="h-16 animate-pulse rounded-lg bg-[hsl(var(--secondary))]" />
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm leading-relaxed text-[hsl(var(--foreground))]">
                    {githubMatchStatus === "matched"
                      ? `Second-stage archived issue search found ${githubMatches.length} similar human investigation record(s).`
                      : githubMatchStatus === "no_match"
                        ? "Second-stage archived issue search completed, but no close human investigation matches were found."
                        : githubMatchStatus === "no_summary"
                          ? "Second-stage archived issue search was skipped because no summary was available."
                          : "Second-stage archived issue search status is not available yet."}
                  </p>
                  <div className="mt-3 space-y-2">
                    {githubMatches.map((item) => (
                      <div key={`${item.incident_id}-${item.similarity}`} className="rounded-lg bg-[hsl(var(--background))] p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium">
                            {item.failure || `Archived Issue ${item.incident_id ?? "?"}`}
                          </span>
                          <span className="text-xs text-[hsl(var(--muted-foreground))]">
                            {typeof item.similarity === "number" ? `${Math.round(item.similarity * 100)}% similarity` : "n/a"}
                          </span>
                        </div>
                        {item.issue_url && (
                          <a
                            href={item.issue_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-2 inline-flex text-xs font-medium text-[hsl(var(--primary))] hover:underline"
                          >
                            Open on GitHub
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </PanelSection>

            <PanelSection title="Telemetry Snapshot">
              {working ? (
                <div className="h-80 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
                  <div className="flex h-full flex-col gap-4">
                    <div className="h-4 w-48 animate-pulse rounded bg-[hsl(var(--secondary))]" />
                    <div className="grid flex-1 gap-3 sm:grid-cols-2">
                      {Array.from({ length: 4 }).map((_, index) => (
                        <div key={index} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-3">
                          <div className="h-3 w-20 animate-pulse rounded bg-[hsl(var(--secondary))]" />
                          <div className="mt-3 h-7 w-16 animate-pulse rounded bg-[hsl(var(--secondary))]" />
                        </div>
                      ))}
                    </div>
                    <div className="h-24 animate-pulse rounded-lg bg-[hsl(var(--secondary))]" />
                  </div>
                </div>
              ) : topIncident ? (
                <div className="space-y-3">
                  <div className="h-72 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-3">
                    {telemetryChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={telemetryChartData} margin={{ top: 8, right: 20, left: -10, bottom: 0 }}>
                          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                          <XAxis dataKey="t" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 11 }} />
                          <YAxis stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 11 }} />
                          <Tooltip
                            contentStyle={{
                              background: "hsl(var(--card))",
                              border: "1px solid hsl(var(--border))",
                              borderRadius: "12px",
                            }}
                            labelStyle={{ color: "hsl(var(--foreground))" }}
                            itemStyle={{ color: "hsl(var(--foreground))" }}
                          />
                          <Line type="monotone" dataKey="temperature" stroke="#f97316" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="pressure" stroke="#38bdf8" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="vibration" stroke="#a78bfa" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="rpm" stroke="#4ade80" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm text-[hsl(var(--muted-foreground))]">
                        No telemetry rows available for charting.
                      </div>
                    )}
                  </div>
                  <div className="rounded-lg bg-[hsl(var(--background))] p-3">
                    <p className="text-xs uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Closest Match</p>
                    <p className="mt-1 text-sm font-medium text-[hsl(var(--primary))]">{topIncident.failure}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {`${(topSimilarity * 100).toFixed(1)}% similarity`}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-[hsl(var(--muted-foreground))]">No telemetry snapshot available yet.</p>
              )}
            </PanelSection>
          </div>
        </div>
      </aside>

    </div>
  );
}

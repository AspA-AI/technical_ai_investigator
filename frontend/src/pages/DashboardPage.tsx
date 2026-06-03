import { useEffect, useState } from "react";
import { getHealth } from "../lib/api/health";
import { downloadInvestigationReport } from "../lib/api/report";
import { getInvestigation, runInvestigation } from "../lib/api/investigation";
import { InvestigationChat } from "../components/chat/InvestigationChat";
import { SensorLogUpload } from "../components/upload/SensorLogUpload";
import type { InvestigationRun } from "../types/investigation";
import type { ReportFormat } from "../lib/api/report";

function statusPill(status: string) {
  if (status === "ok") return "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/25";
  if (status === "warning") return "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/25";
  return "bg-slate-700/70 text-slate-200 ring-1 ring-slate-600/70";
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
    }

    bootstrap();

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
      <section className="rounded-[2rem] border border-slate-800 bg-slate-900/80 p-8 shadow-2xl shadow-slate-950/20 backdrop-blur-xl">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl space-y-4">
            <p className="text-sm uppercase tracking-[0.35em] text-cyan-400">Engineering Investigation Workspace</p>
            <h1 className="text-4xl font-semibold tracking-tight text-white">Upload and investigate from one dashboard.</h1>
            <p className="max-w-2xl text-slate-400">No login required. Your browser session links upload, investigation, and chat history.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className={`rounded-3xl border p-4 text-sm font-medium ${statusPill(backendHealth)}`}>
              <div className="text-slate-300">Backend health</div>
              <div className="mt-2 text-xl text-white">{backendHealth}</div>
            </div>
            <div className="rounded-3xl border border-slate-700/80 bg-slate-950/80 p-4 break-words">
              <div className="text-slate-400">Session ID</div>
              <div className="mt-2 text-sm text-slate-200">{sessionId || "Generating..."}</div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <section className="rounded-[1.75rem] border border-slate-800 bg-slate-900/80 p-6 shadow-xl shadow-slate-950/15">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">Upload & investigate</h2>
                <p className="text-sm text-slate-500">Upload your data and run the investigation automatically.</p>
              </div>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-[0.95fr_0.95fr]">
              <div className="rounded-3xl bg-slate-950/70 p-5 ring-1 ring-slate-700/60">
                <p className="text-sm text-slate-400">Sensor log upload</p>
                <SensorLogUpload onUploadComplete={handleUploadComplete} />
                {uploadMessage && <p className="mt-4 text-sm text-slate-300">{uploadMessage}</p>}
              </div>

              <div className="rounded-3xl bg-slate-950/70 p-5 ring-1 ring-slate-700/60">
                <p className="text-sm text-slate-400">Investigation progress</p>
                <div className="mt-4 rounded-3xl bg-slate-900/80 p-4 text-sm text-slate-200 ring-1 ring-slate-700/60">
                  <p>{working ? "Investigation running..." : "Ready"}</p>
                  {investigationId && <p className="mt-2 text-slate-400">Investigation #{investigationId}</p>}
                  {uploadId && <p className="mt-2 text-slate-400">Upload #{uploadId}</p>}
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-3xl bg-slate-950/70 p-5 ring-1 ring-slate-700/60">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-slate-400">Report download</p>
                  <p className="mt-1 text-xs text-slate-500">Generate PDF or PPTX for the current investigation.</p>
                </div>
                <button
                  type="button"
                  onClick={handleDownloadReport}
                  className="rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500"
                >
                  Download
                </button>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {(["pdf", "pptx"] as ReportFormat[]).map((format) => (
                  <button
                    key={format}
                    type="button"
                    onClick={() => setReportFormat(format)}
                    className={`rounded-2xl px-3 py-2 text-sm font-medium transition ${reportFormat === format ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"}`}
                  >
                    {format.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {message && <div className="mt-5 rounded-3xl bg-emerald-500/10 p-4 text-sm text-emerald-200 ring-1 ring-emerald-500/30">{message}</div>}
            {error && <div className="mt-5 rounded-3xl bg-rose-500/10 p-4 text-sm text-rose-200 ring-1 ring-rose-500/30">{error}</div>}
          </section>

          <section className="rounded-[1.75rem] border border-slate-800 bg-slate-900/80 p-6 shadow-xl shadow-slate-950/15">
            <h2 className="text-xl font-semibold text-white">Investigation findings</h2>
            <p className="mt-2 text-sm text-slate-500">Current investigation summary and key metadata.</p>

            {investigation ? (
              <div className="mt-6 space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-3xl bg-slate-950/70 p-4 ring-1 ring-slate-700/60">
                    <p className="text-sm text-slate-400">Status</p>
                    <p className="mt-2 text-lg font-semibold text-white">{investigation.status}</p>
                  </div>
                  <div className="rounded-3xl bg-slate-950/70 p-4 ring-1 ring-slate-700/60">
                    <p className="text-sm text-slate-400">Upload ID</p>
                    <p className="mt-2 text-lg font-semibold text-white">{investigation.upload_id}</p>
                  </div>
                </div>

                <div className="rounded-3xl bg-slate-950/70 p-4 ring-1 ring-slate-700/60">
                  <p className="text-sm text-slate-400">Summary</p>
                  <p className="mt-3 text-sm leading-6 text-slate-200">{investigation.state.summary || "No summary available yet."}</p>
                </div>
              </div>
            ) : (
              <div className="mt-6 rounded-3xl bg-slate-950/70 p-6 text-sm text-slate-400 ring-1 ring-slate-700/60">
                No investigation loaded yet. Upload a CSV to start.
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <section className="sticky top-6 rounded-[1.75rem] border border-slate-800 bg-slate-900/80 p-6 shadow-xl shadow-slate-950/15 min-h-[calc(100vh-96px)]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-white">Engineering chat</h2>
                <p className="mt-2 text-sm text-slate-500">Ask questions about the investigation and keep your session history.</p>
              </div>
              <div className="rounded-full bg-slate-950/70 px-3 py-2 text-xs uppercase tracking-[0.35em] text-slate-300">Chat</div>
            </div>

            <div className="mt-6">
              <InvestigationChat investigationId={investigationId ?? 0} sessionId={sessionId} />
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

import { useState } from "react";
import type { FormEvent } from "react";
import { uploadSensorLog } from "../../lib/api/upload";
import type { UploadResponse } from "../../types/upload";

interface SensorLogUploadProps {
  onUploadComplete?: (result: UploadResponse) => void;
}

export function SensorLogUpload({ onUploadComplete }: SensorLogUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setMessage(null);
    setError(null);
    setUploading(true);
    try {
      const result = await uploadSensorLog(file);
      setMessage(`${result.status}: ${result.records} records ingested.`);
      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (err: unknown) {
      const detail =
        err &&
        typeof err === "object" &&
        "response" in err &&
        err.response &&
        typeof err.response === "object" &&
        "data" in err.response &&
        err.response.data &&
        typeof err.response.data === "object" &&
        "detail" in err.response.data
          ? String(err.response.data.detail)
          : "Upload failed. Check API logs with make logs-api.";
      setError(detail);
    } finally {
      setUploading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label className="group relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-5 transition-colors hover:border-[hsl(var(--primary))] hover:bg-[hsl(var(--secondary))]">
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="absolute inset-0 cursor-pointer opacity-0"
        />
        <svg className="mb-2 h-6 w-6 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          {file ? file.name : "Choose a CSV file or drag & drop"}
        </span>
      </label>

      <button
        type="submit"
        disabled={!file || uploading}
        className="w-full rounded-lg bg-[hsl(var(--primary))] px-4 py-2.5 text-sm font-medium text-[hsl(var(--primary-foreground))] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {uploading ? (
          <span className="inline-flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Uploading...
          </span>
        ) : (
          "Upload sensor log"
        )}
      </button>

      {message && (
        <p className="flex items-center gap-2 text-xs text-[hsl(var(--primary))]">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          {message}
        </p>
      )}
      {error && (
        <p className="flex items-center gap-2 text-xs text-[hsl(var(--destructive))]">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          {error}
        </p>
      )}
    </form>
  );
}

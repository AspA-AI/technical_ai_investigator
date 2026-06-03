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

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setMessage(null);
    setError(null);
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
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-md space-y-4">
      <input
        type="file"
        accept=".csv"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="block w-full text-sm text-slate-400 file:mr-4 file:rounded file:border-0 file:bg-slate-700 file:px-4 file:py-2 file:text-sm file:text-slate-200"
      />
      <button
        type="submit"
        disabled={!file}
        className="rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        Upload sensor log
      </button>
      {message && <p className="text-sm text-green-400">{message}</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}
    </form>
  );
}

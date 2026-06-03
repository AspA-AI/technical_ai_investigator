import { SensorLogUpload } from "../components/upload/SensorLogUpload";

export function UploadPage() {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Upload Sensor Logs</h1>
      <p className="mb-6 text-sm text-slate-500">Page 1 — CSV upload (e.g. engine_001.csv)</p>
      <SensorLogUpload />
    </div>
  );
}

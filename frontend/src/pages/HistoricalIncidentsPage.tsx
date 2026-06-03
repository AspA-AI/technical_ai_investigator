import { HistoricalIncidentsTable } from "../components/incidents/HistoricalIncidentsTable";

export function HistoricalIncidentsPage() {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Historical Incidents</h1>
      <p className="mb-6 text-sm text-slate-500">Page 5 — similarity table</p>
      <HistoricalIncidentsTable />
    </div>
  );
}

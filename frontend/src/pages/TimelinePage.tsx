import { EngineeringTimelineChart } from "../components/timeline/EngineeringTimelineChart";

export function TimelinePage() {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Engineering Timeline</h1>
      <p className="mb-6 text-sm text-slate-500">Page 3 — Recharts sensor series</p>
      <EngineeringTimelineChart />
    </div>
  );
}

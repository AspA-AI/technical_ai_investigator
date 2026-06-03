import { PlaceholderCard } from "../common/PlaceholderCard";

const widgets = [
  "Risk Level",
  "Anomaly Count",
  "Historical Match Count",
  "Root Cause Ranking",
];

export function InvestigationWidgets() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {widgets.map((title) => (
        <PlaceholderCard
          key={title}
          title={title}
          description="Phase 9 — Investigation Dashboard widget."
        />
      ))}
    </div>
  );
}

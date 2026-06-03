import { SensorContributionChart } from "../components/ranking/SensorContributionChart";

export function SensorRankingPage() {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Sensor Contribution Ranking</h1>
      <p className="mb-6 text-sm text-slate-500">Page 4 — bar chart ranking</p>
      <SensorContributionChart />
    </div>
  );
}

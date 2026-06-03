import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const sampleRanking = [
  { sensor: "Temperature", contribution: 41 },
  { sensor: "Vibration", contribution: 33 },
  { sensor: "Pressure", contribution: 18 },
  { sensor: "RPM", contribution: 8 },
];

export function SensorContributionChart() {
  return (
    <div className="h-80 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sampleRanking} layout="vertical" margin={{ left: 80 }}>
          <CartesianGrid stroke="#334155" />
          <XAxis type="number" stroke="#94a3b8" unit="%" />
          <YAxis type="category" dataKey="sensor" stroke="#94a3b8" />
          <Tooltip />
          <Bar dataKey="contribution" fill="#22d3ee" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

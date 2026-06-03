import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PlaceholderCard } from "../common/PlaceholderCard";

const sampleData = [
  { t: "0", temperature: 70, pressure: 100, vibration: 2, rpm: 3000 },
  { t: "1", temperature: 72, pressure: 98, vibration: 2.1, rpm: 3010 },
  { t: "2", temperature: 85, pressure: 90, vibration: 4.5, rpm: 2980 },
];

export function EngineeringTimelineChart() {
  return (
    <div className="space-y-4">
      <PlaceholderCard
        title="Engineering Timeline"
        description="Recharts: temperature, pressure, vibration, RPM — anomaly highlights in Phase 9."
      />
      <div className="h-80 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={sampleData}>
            <CartesianGrid stroke="#334155" />
            <XAxis dataKey="t" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="temperature" stroke="#f97316" dot={false} />
            <Line type="monotone" dataKey="pressure" stroke="#38bdf8" dot={false} />
            <Line type="monotone" dataKey="vibration" stroke="#a78bfa" dot={false} />
            <Line type="monotone" dataKey="rpm" stroke="#4ade80" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

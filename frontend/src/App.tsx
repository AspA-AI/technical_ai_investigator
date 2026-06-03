import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoricalIncidentsPage } from "./pages/HistoricalIncidentsPage";
import { SensorRankingPage } from "./pages/SensorRankingPage";
import { TimelinePage } from "./pages/TimelinePage";
import { WhiteboardPage } from "./pages/WhiteboardPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="sensor-ranking" element={<SensorRankingPage />} />
        <Route path="incidents" element={<HistoricalIncidentsPage />} />
        <Route path="whiteboard" element={<WhiteboardPage />} />
      </Route>
    </Routes>
  );
}

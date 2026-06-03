import { InvestigationWhiteboard } from "../components/whiteboard/InvestigationWhiteboard";

export function WhiteboardPage() {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Investigation Whiteboard</h1>
      <p className="mb-6 text-sm text-slate-500">Page 6 — React Flow reasoning graph</p>
      <InvestigationWhiteboard />
    </div>
  );
}

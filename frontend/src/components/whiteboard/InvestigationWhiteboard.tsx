import { Background, Controls, MiniMap, ReactFlow } from "reactflow";
import "reactflow/dist/style.css";

const initialNodes = [
  { id: "1", position: { x: 250, y: 0 }, data: { label: "Failure" } },
  { id: "2", position: { x: 250, y: 80 }, data: { label: "Temperature Spike" } },
  { id: "3", position: { x: 250, y: 160 }, data: { label: "Cooling Degradation" } },
  { id: "4", position: { x: 250, y: 240 }, data: { label: "Incident #31" } },
  { id: "5", position: { x: 250, y: 320 }, data: { label: "Recommended Action" } },
];

const initialEdges = [
  { id: "e1-2", source: "1", target: "2" },
  { id: "e2-3", source: "2", target: "3" },
  { id: "e3-4", source: "3", target: "4" },
  { id: "e4-5", source: "4", target: "5" },
];

export function InvestigationWhiteboard() {
  return (
    <div className="h-[480px] rounded-lg border border-slate-800 bg-slate-900">
      <ReactFlow nodes={initialNodes} edges={initialEdges} fitView>
        <Background color="#334155" gap={16} />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

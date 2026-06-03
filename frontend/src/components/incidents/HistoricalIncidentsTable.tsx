const columns = ["Incident ID", "Similarity Score", "Root Cause", "Resolution"];

export function HistoricalIncidentsTable() {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-900 text-slate-400">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-4 py-3 font-medium">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-slate-800 text-slate-500">
            <td colSpan={4} className="px-4 py-6 text-center">
              No incidents loaded — Phase 9 table scaffold.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

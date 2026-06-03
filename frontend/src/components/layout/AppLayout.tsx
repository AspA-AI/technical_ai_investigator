import { Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/95 px-6 py-5">
        <div className="mx-auto flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between max-w-7xl">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-cyan-400">Investigation Copilot</p>
            <h1 className="mt-2 text-2xl font-semibold text-white">Dashboard</h1>
          </div>
          <div className="rounded-3xl bg-slate-950/70 px-4 py-2 text-sm text-slate-300">Upload, investigate, and chat in one place.</div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}

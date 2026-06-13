import { apiClient } from "./client";

export type ReportFormat = "pdf" | "pptx" | "md";

export async function downloadInvestigationReport(
  investigationId: number,
  format: ReportFormat = "pdf"
): Promise<Blob> {
  const { data } = await apiClient.post<Blob>(
    "/api/report",
    { investigation_id: investigationId, format },
    { responseType: "blob" }
  );
  return data;
}

export async function previewInvestigationReport(
  investigationId: number
): Promise<{ investigation_id: number; filename: string; report_path: string; markdown: string }> {
  const { data } = await apiClient.get<{ investigation_id: number; filename: string; report_path: string; markdown: string }>(
    `/api/report/${investigationId}/preview`
  );
  return data;
}

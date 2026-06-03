import { apiClient } from "./client";

export type ReportFormat = "pdf" | "pptx";

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

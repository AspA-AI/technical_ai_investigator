import { apiClient } from "./client";
import type { InvestigationRun } from "../../types/investigation";

export async function runInvestigation(uploadId: string): Promise<InvestigationRun> {
  const { data } = await apiClient.post<InvestigationRun>(
    `/api/investigations/${uploadId}/run`
  );
  return data;
}

export async function getInvestigation(
  investigationId: number
): Promise<InvestigationRun> {
  const { data } = await apiClient.get<InvestigationRun>(
    `/api/investigations/${investigationId}`
  );
  return data;
}

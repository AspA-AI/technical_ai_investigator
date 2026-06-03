import { apiClient } from "./client";

export interface ToolListResponse {
  tools: string[];
}

export async function listMcpTools(): Promise<ToolListResponse> {
  const { data } = await apiClient.get<ToolListResponse>("/api/mcp/tools");
  return data;
}

import { apiClient } from "./client";
import type { ChatRequest, ChatResponse } from "../../types/chat";

export async function sendEngineeringChat(
  investigationId: number,
  body: ChatRequest
): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>(
    `/api/investigations/${investigationId}/chat`,
    body
  );
  return data;
}

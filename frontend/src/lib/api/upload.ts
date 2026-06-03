import { apiClient } from "./client";
import type { UploadResponse } from "../../types/upload";

export async function uploadSensorLog(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<UploadResponse>("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

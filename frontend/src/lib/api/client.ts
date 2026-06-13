import axios, { AxiosHeaders } from "axios";

const baseURL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "";

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const sessionId = window.localStorage.getItem("investigation_copilot_session_id");
    if (sessionId) {
      const headers = (config.headers ?? new AxiosHeaders()) as any;
      if (typeof headers.set === "function") {
        headers.set("X-Session-ID", sessionId);
      } else {
        headers["X-Session-ID"] = sessionId;
      }
      config.headers = headers;
    }
  }
  return config;
});

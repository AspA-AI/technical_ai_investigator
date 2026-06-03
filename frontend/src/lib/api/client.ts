import axios from "axios";

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
      if (!config.headers) {
        config.headers = {};
      }
      (config.headers as Record<string, string>)["X-Session-ID"] = sessionId;
    }
  }
  return config;
});

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const cwd =
  (globalThis as any).process?.cwd?.() ??
  new (globalThis as any).URL(".", (import.meta as any).url).pathname;

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, cwd, "");
  const apiTarget = env.VITE_DEV_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/health": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});

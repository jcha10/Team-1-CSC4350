import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy the API and WebSockets to the backend so the app is
// same-origin exactly like production (where FastAPI serves the build).
const backend = process.env.SMILEY_BACKEND ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
  },
  build: {
    rollupOptions: {
      output: {
        // Vendor libraries change far less often than app code; separate
        // chunks let browsers keep them cached across app deploys.
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "react";
          if (id.includes("framer-motion")) return "motion";
          return "charts"; // recharts and its d3 dependencies
        },
      },
    },
    // recharts + d3 is ~150 KB gzipped on its own; that's expected, not a regression.
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/ws": { target: backend.replace(/^http/, "ws"), ws: true },
    },
  },
});

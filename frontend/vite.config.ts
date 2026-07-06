import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-server proxy mirrors the nginx reverse proxy used in the container
// (see nginx.conf). In production, nginx handles these routes instead:
//   /api/rag/    -> http://rag:8001/
//   /api/ingest/ -> http://ingestion:8002/
// Here we point at localhost so `npm run dev` works against locally
// running services, stripping the /api/* prefix exactly like nginx does.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/rag": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/rag/, ""),
      },
      "/api/ingest": {
        target: "http://localhost:8002",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/ingest/, ""),
      },
    },
  },
});

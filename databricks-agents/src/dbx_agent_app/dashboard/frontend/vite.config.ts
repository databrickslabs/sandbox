import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  server: {
    port: 5175,
    proxy: {
      "/api": "http://127.0.0.1:8502",
      "/health": "http://127.0.0.1:8502",
    },
  },
});

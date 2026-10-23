import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  build: {
    rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } },
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.tsx"],
    restoreMocks: true,
  },
});

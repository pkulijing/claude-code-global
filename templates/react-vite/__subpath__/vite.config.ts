import { fileURLToPath } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 前后端分离时，dev server 把 /api、/ws 代理到后端服务；生产时前端由后端静态托管，无需代理。
// BACKEND 按实际后端监听地址改；纯前端项目可删掉下面的 server.proxy 段。
const BACKEND = "http://127.0.0.1:8080";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    // 产出到 dist，供后端静态托管（如 FastAPI StaticFiles / nginx）。
    outDir: "dist",
  },
  server: {
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/ws": { target: BACKEND, ws: true, changeOrigin: true },
    },
  },
});

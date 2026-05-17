/*
 * VITE.CONFIG.JS — Configuração do Vite (bundler do frontend).
 *
 * O QUE É VITE?
 *   Vite é um "bundler" (empacotador) moderno para projetos web.
 *   Ele substitui ferramentas antigas como Webpack.
 *
 *   DIFERENÇAS PRÁTICAS:
 *   - Dev server INSTANTÂNEO (não precisa "buildar" tudo)
 *   - Hot Module Replacement (HMR) — altera o código e a tela atualiza
 *     sem perder estado do React
 *   - Build extremamente rápido (usa Rollup internamente)
 *
 * CONFIGURAÇÕES IMPORTANTES:
 *
 *   server.port: 5173
 *     Porta padrão do Vite. O frontend roda em http://localhost:5173
 *
 *   server.proxy:
 *     Redireciona chamadas /api para o backend (localhost:8000).
 *     Isso resolve problemas de CORS e simplifica o código:
 *       - No frontend: api.get("/pacientes")
 *       - No backend: recebe como http://localhost:8000/api/v1/pacientes
 *
 *   build.outDir: "dist"
 *     Pasta onde o build de produção é gerado.
 *     É esta pasta que o Tauri vai empacotar no desktop.
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Toda requisição para /api é redirecionada ao backend
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});

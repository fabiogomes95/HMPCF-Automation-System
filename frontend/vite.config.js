import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  // Dev server — proxy redireciona /api para o backend local
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },

  // Build de produção
  build: {
    outDir: "dist",
    sourcemap: false,       // sem sourcemaps expostos em produção
    minify: "esbuild",      // minificação rápida
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Separa React em chunk próprio → melhor cache no browser
        manualChunks: {
          vendor: ["react", "react-dom"],
        },
      },
    },
  },
});

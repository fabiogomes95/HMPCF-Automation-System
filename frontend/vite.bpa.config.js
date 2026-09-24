// Build das telas do BPA para o BPA LOCAL (bpa/ui/, servido em /ui/ pelo
// bpa_local). Vai versionado no git: os notebooks não têm Node para montar.
// Rodar depois de mexer em src/pages/bpa/:  npm run build:bpa
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  base: "/ui/",
  publicDir: false, // imagens/páginas do sistema não vão pro BPA
  build: {
    outDir: resolve(__dirname, "../bpa/ui"),
    emptyOutDir: true,
    sourcemap: false,
    minify: "esbuild",
    rollupOptions: {
      input: resolve(__dirname, "bpa-local.html"),
    },
  },
});

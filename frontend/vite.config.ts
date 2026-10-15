import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, /api é encaminhado ao backend local; o navegador vê uma única origem,
// o que mantém os cookies de sessão SameSite=Strict funcionando.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { sourcemap: false },
});

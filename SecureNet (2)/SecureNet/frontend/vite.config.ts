import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Raise chunk size warning threshold — Recharts + lucide-react are large
    // but expected for this application. Consider code splitting in production.
    chunkSizeWarningLimit: 800,
  },
});

import { readFileSync } from 'node:fs';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// App version shown on the Support page (single source: package.json)
const { version } = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8')) as { version: string };

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  build: {
    // Raise chunk size warning threshold — Recharts + lucide-react are large
    // but expected for this application. Consider code splitting in production.
    chunkSizeWarningLimit: 800,
  },
});

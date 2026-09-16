import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base '/' so built assets resolve to /assets/... from any deep SPA route.
export default defineConfig({
  base: '/',
  plugins: [react()],
  build: { outDir: 'dist', chunkSizeWarningLimit: 1200 },
});

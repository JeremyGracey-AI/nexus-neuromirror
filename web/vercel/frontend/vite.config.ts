import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vercel target.
//
// The frontend is served at the deployment root (e.g. https://<project>.vercel.app/),
// so assets use root-absolute paths (`base: '/'`). SPA routing is handled by
// hash-based routing in the app AND a vercel.json rewrite that serves
// index.html for non-/api, non-asset paths.
//
// During local development, `vercel dev` serves both the static build and the
// serverless functions on the same origin, so no dev proxy is required. The
// optional proxy below only matters if you run `vite` standalone against a
// separately running API.
export default defineConfig({
  base: '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});

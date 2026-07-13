import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server proxies /api to the FastAPI backend on :8000.
// Production build emits static files that the backend serves directly, and
// that also deploy correctly under a nested private preview URL.
//
// `base: './'` makes all emitted asset references relative (e.g.
// `./assets/index-xxx.js`) instead of root-absolute (`/assets/...`). Under a
// nested deploy path like `/computer/a/<id>/`, root-absolute paths resolve
// against the wrong origin root and 404, producing a blank page. Relative
// paths resolve against the nested URL and load correctly. The backend still
// serves the built files fine at `/` because relative paths work there too.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});

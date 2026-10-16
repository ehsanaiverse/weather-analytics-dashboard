import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Vite configuration.
 *
 * The dev server proxies `/api` to the FastAPI backend so the browser only ever
 * sees a single origin. That removes the need for CORS during development while
 * still exercising the real endpoints; the backend's CORS configuration stays in
 * place for direct calls (and for production, where the frontend may be served
 * from a different host).
 *
 * Target port: Vite will move to the next free port if 5173 is taken, so the
 * backend's default CORS origins (`localhost:5173`, `127.0.0.1:5173`) cover the
 * common case. Set `VITE_API_PROXY_TARGET` to point at a different backend.
 */
const proxyTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        // Recharts pulls in the d3 modules and is by far the heaviest
        // dependency. Splitting it out keeps the app chunk small and lets the
        // vendor bundles stay cached across deploys.
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('recharts') || id.includes('victory-vendor') || id.includes('/d3-')) {
              return 'charts'
            }
            if (id.includes('react-dom') || id.includes('/react/') || id.includes('scheduler')) {
              return 'react'
            }
            if (id.includes('lucide-react')) {
              return 'icons'
            }
          }
          return undefined
        },
      },
    },
  },
})
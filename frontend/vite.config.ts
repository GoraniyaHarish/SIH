import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API is served by FastAPI on 8000 during development; Vite proxies /api so the browser sees
// a single origin and no CORS relaxation is needed in the default setup.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})

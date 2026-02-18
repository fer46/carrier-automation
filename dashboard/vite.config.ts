import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],  // Tailwind CSS 4 uses a Vite plugin (no postcss.config needed)
  base: '/dashboard/',  // Must match the SPA mount path in app/main.py
  server: {
    proxy: {
      '/api': 'http://localhost:8000',  // Forward API calls to FastAPI during development
    },
  },
  optimizeDeps: {
    include: ['react-simple-maps'],  // Pre-bundle CJS dependency for Vite compatibility
  },
  build: {
    outDir: 'dist',  // FastAPI serves the SPA from dashboard/dist/
  },
})

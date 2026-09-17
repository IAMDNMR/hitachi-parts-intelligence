import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Honour an assigned port so a second dev server can run alongside one
  // that already holds 5173; falls back to Vite's usual default.
  server: {
    port: Number(process.env.PORT) || 5173,
    // In production, Vercel builds api/*.js into serverless functions on the
    // same origin. Locally there is no such thing — server/dev-api.mjs hosts
    // the same handler on its own port, and this proxy is what makes
    // `fetch('/api/part-enrichment')` work identically in both places.
    proxy: {
      '/api': `http://localhost:${Number(process.env.DEV_API_PORT) || 8787}`,
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Honour an assigned port so a second dev server can run alongside one
  // that already holds 5173; falls back to Vite's usual default.
  server: {
    port: Number(process.env.PORT) || 5173,
    // The FastAPI backend (backend/app/main.py) is the single backend
    // surface for this app — every API call goes through /api/v1/*.
    proxy: {
      '/api/v1': `http://localhost:${Number(process.env.BACKEND_PORT) || 8000}`,
    },
  },
})

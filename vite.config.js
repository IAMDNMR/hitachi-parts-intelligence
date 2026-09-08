import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * The parts-ordering service, as the dev server should reach it.
 *
 * WHY A PROXY RATHER THAN A CORS ALLOW-LIST
 * -----------------------------------------
 * The frontend used to call http://localhost:8000 directly, which makes every
 * request cross-origin and puts the browser's CORS check between the two
 * halves of this project. The backend answered that check with an allow-list
 * of origins, and the allow-list named a port — 5173.
 *
 * Vite does not always get 5173. It takes the next free port when that one is
 * busy, which happens whenever a second dev server is already running, and
 * the moment it does every request fails with "Cannot reach the parts-ordering
 * service" even though the service is running perfectly. That failure hit
 * twice in one afternoon and looks exactly like the backend being down.
 *
 * Proxied, the browser only ever talks to the Vite origin, whatever port that
 * turns out to be. There is no cross-origin request, so there is no CORS check
 * to fail and no port written down in two places to drift apart.
 *
 * The backend keeps its CORS settings for anything that calls it directly
 * (curl, the /docs page, a deployed frontend on its own domain) — this just
 * means the dev loop no longer depends on them.
 */
const API = process.env.ORDERING_API_URL || 'http://localhost:8000'

const proxy = {
  '/api': {
    target: API,
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [react()],
  // Honour an assigned port so a second dev server can run alongside one
  // that already holds 5173; falls back to Vite's usual default.
  server: { port: Number(process.env.PORT) || 5173, proxy },
  // `vite preview` serves the build without the dev server, so it needs the
  // same proxy or the built app cannot reach the API either.
  preview: { proxy },
})

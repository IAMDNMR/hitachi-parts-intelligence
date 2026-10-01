// The site is a static build, and a static host only serves paths that exist as files. `/analytics` is a plain path (not a
// #hash route), so after the build we copy the app shell to dist/analytics/index.html. The app reads the URL on load and
// shows the right page. (Vite's dev and preview servers already fall back to index.html, so this only matters on Vercel.)
import { cpSync, existsSync, mkdirSync } from 'node:fs'

const ROUTES = ['analytics']

if (!existsSync('dist/index.html')) throw new Error('dist/index.html not found - run the Vite build first')
for (const route of ROUTES) {
  mkdirSync(`dist/${route}`, { recursive: true })
  cpSync('dist/index.html', `dist/${route}/index.html`)
  console.log(`spa-routes: dist/${route}/index.html`)
}

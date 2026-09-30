/**
 * First-party visitor analytics (see backend/app/modules/analytics/service.py). Nothing here runs until the
 * visitor accepts the cookie banner (see components/CookieConsent). No third-party script, no fingerprinting —
 * a visitor who declines, or who simply hasn't answered yet, is invisible to this module.
 */

const CONSENT_KEY = 'hcme-analytics-consent' // localStorage: 'accepted' | 'declined' — the choice itself, not tracking data
const VISITOR_COOKIE = 'hcme_visitor_id'
const SESSION_KEY = 'hcme-analytics-session-id' // sessionStorage: one id per browser tab session
const API = '/api/v1/analytics/event'

export type Consent = 'accepted' | 'declined' | null

export function getConsent(): Consent {
  try {
    const v = localStorage.getItem(CONSENT_KEY)
    return v === 'accepted' || v === 'declined' ? v : null
  } catch {
    return null
  }
}

function setConsent(value: Exclude<Consent, null>) {
  try {
    localStorage.setItem(CONSENT_KEY, value)
  } catch {
    // localStorage unavailable — the banner will just ask again next visit
  }
}

function uuid(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return m?.[1] ? decodeURIComponent(m[1]) : null
}

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 86400000).toUTCString()
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`
}

function post(body: Record<string, unknown>) {
  const json = JSON.stringify(body)
  try {
    if (navigator.sendBeacon) {
      const ok = navigator.sendBeacon(API, new Blob([json], { type: 'application/json' }))
      if (ok) return
    }
  } catch {
    // fall through to fetch
  }
  fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: json, keepalive: true }).catch(() => {})
}

function detectBrowser(ua: string): string {
  if (/Edg\//.test(ua)) return 'Edge'
  if (/OPR\//.test(ua)) return 'Opera'
  if (/Chrome\//.test(ua) && !/Chromium/.test(ua)) return 'Chrome'
  if (/Firefox\//.test(ua)) return 'Firefox'
  if (/Safari\//.test(ua) && !/Chrome/.test(ua)) return 'Safari'
  return 'Other'
}

function detectOs(ua: string): string {
  if (/Windows/.test(ua)) return 'Windows'
  if (/Mac OS X/.test(ua)) return 'macOS'
  if (/Android/.test(ua)) return 'Android'
  if (/iPhone|iPad|iPod/.test(ua)) return 'iOS'
  if (/Linux/.test(ua)) return 'Linux'
  return 'Other'
}

function collectDevice() {
  const ua = navigator.userAgent
  const w = window.innerWidth
  return {
    device_type: w < 640 ? 'mobile' : w < 1024 ? 'tablet' : 'desktop',
    browser: detectBrowser(ua),
    os: detectOs(ua),
    screen_w: screen.width,
    screen_h: screen.height,
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  }
}

let currentPageviewId: string | null = null
let pageEnteredAt = 0
let started = false

function ids() {
  return { visitorId: getCookie(VISITOR_COOKIE) || '', sessionId: sessionStorage.getItem(SESSION_KEY) || '' }
}

function flushDuration() {
  if (!currentPageviewId) return
  const { visitorId, sessionId } = ids()
  const duration_seconds = (Date.now() - pageEnteredAt) / 1000
  post({ type: 'duration', visitor_id: visitorId, session_id: sessionId, pageview_id: currentPageviewId, duration_seconds })
  currentPageviewId = null
}

function trackPageview(path: string) {
  flushDuration()
  const { visitorId, sessionId } = ids()
  currentPageviewId = uuid()
  pageEnteredAt = Date.now()
  post({ type: 'pageview', visitor_id: visitorId, session_id: sessionId, pageview_id: currentPageviewId, path })
}

/** Called once consent is accepted (either just now, or on a later visit where it was already accepted). */
export function startAnalytics() {
  if (started || getConsent() !== 'accepted') return
  started = true

  let visitorId = getCookie(VISITOR_COOKIE)
  if (!visitorId) {
    visitorId = uuid()
    setCookie(VISITOR_COOKIE, visitorId, 365)
  }
  let sessionId = sessionStorage.getItem(SESSION_KEY)
  const isNewSession = !sessionId
  if (!sessionId) {
    sessionId = uuid()
    sessionStorage.setItem(SESSION_KEY, sessionId)
  }
  const path = window.location.hash || '#/'
  if (isNewSession) {
    post({
      type: 'session_start', visitor_id: visitorId, session_id: sessionId,
      referrer: document.referrer || null, landing_path: path, device: collectDevice(),
    })
  }
  trackPageview(path)
  window.addEventListener('hashchange', () => trackPageview(window.location.hash || '#/'))
  window.addEventListener('pagehide', flushDuration)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushDuration()
  })
}

export function acceptCookies() {
  setConsent('accepted')
  startAnalytics()
}

export function declineCookies() {
  setConsent('declined')
}

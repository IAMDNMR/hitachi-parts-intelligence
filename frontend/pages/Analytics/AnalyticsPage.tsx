import { useEffect, useState, type FormEvent, type MouseEvent } from 'react'
import './AnalyticsPage.css'

import { SiteHeader } from '../../components/SiteHeader/SiteHeader'

/**
 * Visitor analytics dashboard — internal use only, behind a login (one shared admin password; see
 * backend/app/api/v1/analytics.py). Not linked from the public nav. Every number here is read live from the
 * same AuraDB the tracker (frontend/lib/analytics.ts) writes to.
 */

const TOKEN_KEY = 'hcme-analytics-token'

interface Summary {
  total_visitors: number
  total_sessions: number
  visitors_today: number
  sessions_today: number
  new_visitors: number
  returning_visitors: number
  avg_session_seconds: number
  top_pages: { path: string; views: number; total_seconds: number }[]
  top_countries: { country: string; sessions: number }[]
  device_breakdown: { device_type: string; sessions: number }[]
  visits_by_day: { date: string; sessions: number }[]
}

interface SessionRow {
  session_id: string
  visitor_id: string
  started_at: string
  country: string | null
  region: string | null
  city: string | null
  device_type: string | null
  browser: string | null
  os: string | null
  referrer: string | null
  landing_path: string | null
  visitor_visit_count: number
  pages: number
  total_seconds: number
}

const fmtTime = (secs: number) => {
  const s = Math.round(secs || 0)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}
const fmtDateTime = (iso: string) => new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })

export function AnalyticsPage({ onHome }: { onHome: () => void }) {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  })

  return (
    <main className="ps an-screen" id="analytics">
      <SiteHeader
        position="sticky"
        current="analytics"
        onBrandClick={(event: MouseEvent<HTMLAnchorElement>) => {
          event.preventDefault()
          onHome()
        }}
      />
      <div className="an">
        {token ? (
          <Dashboard
            token={token}
            onSignOut={() => {
              try {
                sessionStorage.removeItem(TOKEN_KEY)
              } catch {
                // ignore
              }
              setToken(null)
            }}
          />
        ) : (
          <Login
            onSignedIn={(t) => {
              try {
                sessionStorage.setItem(TOKEN_KEY, t)
              } catch {
                // ignore — the session stays signed in for this tab only
              }
              setToken(t)
            }}
          />
        )}
      </div>
    </main>
  )
}

function Login({ onSignedIn }: { onSignedIn: (token: string) => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const r = await fetch('/api/v1/analytics/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error?.message || 'Incorrect password.')
      onSignedIn(d.token)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="an-login">
      <form className="an-login__card" onSubmit={submit}>
        <p className="an-eyebrow">HCME After-Sales · Internal</p>
        <h1>Analytics sign-in</h1>
        <p className="an-muted">This dashboard is for internal use only.</p>
        <label htmlFor="an-password">Password</label>
        <input
          id="an-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          required
        />
        {error && <p className="an-error" role="alert">{error}</p>}
        <button type="submit" className="an-btn" disabled={busy || !password}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}

function Dashboard({ token, onSignOut }: { token: string; onSignOut: () => void }) {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [sessions, setSessions] = useState<SessionRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` }
    Promise.all([
      fetch('/api/v1/analytics/summary', { headers }).then((r) => {
        if (!r.ok) throw new Error(r.status === 401 || r.status === 403 ? 'Session expired.' : 'Could not load analytics.')
        return r.json()
      }),
      fetch('/api/v1/analytics/sessions', { headers }).then((r) => (r.ok ? r.json() : { sessions: [] })),
    ])
      .then(([s, sess]) => {
        setSummary(s)
        setSessions(sess.sessions)
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : String(e))
        if (String(e).includes('expired')) onSignOut()
      })
  }, [token, onSignOut])

  if (error) return <p className="an-error" role="alert">{error}</p>
  if (!summary) return <p className="an-muted">Loading analytics…</p>

  const maxDay = Math.max(1, ...summary.visits_by_day.map((d) => d.sessions))

  return (
    <section>
      <header className="an-head">
        <div>
          <p className="an-eyebrow">HCME After-Sales · Internal</p>
          <h1>Analytics</h1>
          <p className="an-sub">Real visits, tracked with consent, stored in the same database as everything else.</p>
        </div>
        <button type="button" className="an-btn an-btn--ghost" onClick={onSignOut}>Sign out</button>
      </header>

      <div className="an-summary">
        <Stat label="Total visitors" value={summary.total_visitors} />
        <Stat label="Total sessions" value={summary.total_sessions} />
        <Stat label="Visitors today" value={summary.visitors_today} />
        <Stat label="Sessions today" value={summary.sessions_today} />
        <Stat label="Avg. time on site" value={fmtTime(summary.avg_session_seconds)} />
        <Stat label="New / returning" value={`${summary.new_visitors} / ${summary.returning_visitors}`} />
      </div>

      <div className="an-cols">
        <div className="an-card">
          <h3>Visits, last 30 days</h3>
          {summary.visits_by_day.length === 0 && <p className="an-muted">No visits yet.</p>}
          <div className="an-bars">
            {summary.visits_by_day.map((d) => (
              <div key={d.date} className="an-bar-col" title={`${d.date}: ${d.sessions}`}>
                <div className="an-bar" style={{ height: `${(d.sessions / maxDay) * 100}%` }} />
              </div>
            ))}
          </div>
        </div>

        <div className="an-card">
          <h3>Top pages</h3>
          {summary.top_pages.length === 0 ? (
            <p className="an-muted">No page views yet.</p>
          ) : (
            <table className="an-table">
              <thead><tr><th>Page</th><th>Views</th><th>Total time</th></tr></thead>
              <tbody>
                {summary.top_pages.map((p) => (
                  <tr key={p.path}><td>{p.path}</td><td>{p.views}</td><td>{fmtTime(p.total_seconds)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="an-card">
          <h3>Location</h3>
          {summary.top_countries.length === 0 ? (
            <p className="an-muted">No location data yet.</p>
          ) : (
            <table className="an-table">
              <thead><tr><th>Country</th><th>Sessions</th></tr></thead>
              <tbody>
                {summary.top_countries.map((c) => (
                  <tr key={c.country}><td>{c.country}</td><td>{c.sessions}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="an-card">
          <h3>Devices</h3>
          {summary.device_breakdown.length === 0 ? (
            <p className="an-muted">No device data yet.</p>
          ) : (
            <table className="an-table">
              <thead><tr><th>Device</th><th>Sessions</th></tr></thead>
              <tbody>
                {summary.device_breakdown.map((d) => (
                  <tr key={d.device_type}><td>{d.device_type}</td><td>{d.sessions}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="an-card">
        <h3>Recent sessions</h3>
        {!sessions || sessions.length === 0 ? (
          <p className="an-muted">No sessions yet.</p>
        ) : (
          <div className="an-table-wrap">
            <table className="an-table">
              <thead>
                <tr><th>Started</th><th>Location</th><th>Device</th><th>Landing page</th><th>Referrer</th><th>Pages</th><th>Time</th><th>Visit #</th></tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.session_id}>
                    <td>{fmtDateTime(s.started_at)}</td>
                    <td>{[s.city, s.region, s.country].filter(Boolean).join(', ') || '—'}</td>
                    <td>{[s.device_type, s.browser, s.os].filter(Boolean).join(' · ') || '—'}</td>
                    <td>{s.landing_path || '—'}</td>
                    <td>{s.referrer || 'Direct'}</td>
                    <td>{s.pages}</td>
                    <td>{fmtTime(s.total_seconds)}</td>
                    <td>{s.visitor_visit_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="an-stat">
      <span className="an-stat__label">{label}</span>
      <strong className="an-stat__value">{value}</strong>
    </div>
  )
}

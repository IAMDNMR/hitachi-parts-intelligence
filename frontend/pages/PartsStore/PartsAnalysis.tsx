import { useEffect, useState } from 'react'
import { PiIcon } from './PiIcons'

/**
 * Phase 11 views: ranked similar parts, disruption scenarios and KPIs.
 * Each renders exactly what the backend returns, with its method / data-basis line, so source vs synthetic data
 * stays visible. Backend: /intelligence/parts/{id}/similar, /intelligence/disruption, /intelligence/kpis.
 */

export interface MitigationCandidate {
  order: number
  part_id: string
  part_name: string | null
  status: 'Candidate for Engineering Review' | 'Not Suitable' | 'Insufficient Data'
  shared_machine_models: number
  machine_coverage_pct: number
  text_similarity_pct: number
  compliance: { status: string; missing: string[]; expired: string[]; expiring_soon: string[]; satisfied_demo_evidence: string[] }
  supplier_dependency: { risk: string; basis: string; note: string }
  stock: { status: string; on_hand: number | null; basis: string }
  not_suitable_because: string[]
  open_questions: string[]
}

export interface DisruptionBrief {
  scenario: string
  summary: string
  counts: { parts: number; assemblies: number; machines: number; customers: number; orders: number }
  customers_note: string | null
  notes: string[]
  provenance: Record<string, string>
  mitigation: { target: string; explanation: string; candidates: MitigationCandidate[] }[]
}

const SCENARIO_LABEL: Record<string, string> = {
  part_unavailable: 'Part unavailable',
  supplier_unavailable: 'Supplier unavailable',
  compliance_failure: 'Compliance failure',
  stock_shortage: 'Stock shortage',
}

const PROVENANCE_LABEL: Record<string, string> = {
  machines_and_fitment: 'Machines / fitment',
  assemblies_bom_criticality: 'Assemblies / BOM',
  supplier_links: 'Supplier links',
  compliance_evidence: 'Compliance evidence',
  stock: 'Stock',
  orders: 'Orders',
}

const isReal = (v: string) => v.startsWith('REAL') || v.startsWith('SOURCE')

export function DisruptionView({ d }: { d: DisruptionBrief }) {
  return (
    <div className="pix-section pix-disrupt">
      <div className="pix-disrupt__head">
        <strong>{SCENARIO_LABEL[d.scenario] ?? d.scenario}</strong>
      </div>
      <div className="pix-stats">
        {(
          [
            ['Parts', d.counts.parts],
            ['Assemblies (demo BOM)', d.counts.assemblies],
            ['Machine models', d.counts.machines],
            ['Open orders', d.counts.orders],
          ] as const
        ).map(([label, n]) => (
          <div key={label} className="pix-stat">
            <span>{label}</span>
            <strong>{n}</strong>
          </div>
        ))}
      </div>
      <div className="pix-prov" aria-label="Data basis">
        {Object.entries(d.provenance).map(([k, v]) => (
          <span key={k} className={`pix-chip ${isReal(v) ? 'pix-chip--real' : 'pix-chip--demo'}`} title={v}>
            {PROVENANCE_LABEL[k] ?? k}: {isReal(v) ? 'real' : v === 'NOT_CONNECTED' ? 'not connected' : 'demo'}
          </span>
        ))}
      </div>
      {d.customers_note && <p className="pix-muted"><PiIcon name="info" size={13} /> {d.customers_note}</p>}
      {d.notes.map((n) => (
        <p key={n} className="pix-muted"><PiIcon name="info" size={13} /> {n}</p>
      ))}

      {d.mitigation.map((m) => (
        <div key={m.target} className="pix-mit">
          <h4>Options for {m.target}</h4>
          <p className="pix-explain">{m.explanation}</p>
          {m.candidates.map((c) => (
            <div key={c.part_id} className={`pix-alt pix-alt--${c.status === 'Not Suitable' ? 'not_recommended' : c.status === 'Insufficient Data' ? 'conditional' : 'good_candidate'}`}>
              <div className="pix-alt__head">
                <strong>{c.part_id}</strong>
                <span>{c.part_name}</span>
                <span className={`pix-rec ${c.status === 'Not Suitable' ? 'pix-rec--not_recommended' : c.status === 'Insufficient Data' ? 'pix-rec--conditional' : 'pix-rec--review'}`}>{c.status}</span>
              </div>
              <div className="pix-alt__grid">
                <span>Shared machine models <strong>{c.shared_machine_models} ({c.machine_coverage_pct}%)</strong></span>
                <span>Compliance <strong>{c.compliance.status.replace(/_/g, ' ').toLowerCase()}</strong></span>
                <span>Supplier dependency <strong>{c.supplier_dependency.risk.toLowerCase()}</strong> ({c.supplier_dependency.basis === 'REAL' ? 'real' : 'demo'})</span>
                <span>Stock <strong>{c.stock.status.toLowerCase()}</strong> (demo)</span>
                <span>Text similarity <strong>{c.text_similarity_pct}%</strong> (supporting only)</span>
              </div>
              {c.not_suitable_because.length > 0 && (
                <div className="pix-alt__gaps">Not suitable: {c.not_suitable_because.join('; ')}</div>
              )}
              {c.open_questions.length > 0 && <div className="pix-alt__gaps">Open: {c.open_questions.join('; ')}</div>}
            </div>
          ))}
        </div>
      ))}
      <p className="pix-basis"><PiIcon name="info" size={14} /> Candidates are for engineering review, not approved replacements. No HCME supersession or interchangeability data is loaded.</p>
    </div>
  )
}

/* ---------- Graph Insights tabs ---------- */

interface SimilarPart {
  part_id: string
  part_name: string | null
  similarity_pct: number
  machine_coverage_pct?: number
  status?: string
  reasons: string[]
}

export function SimilarTab({ partId }: { partId: string }) {
  const [d, setD] = useState<{ alternatives: SimilarPart[]; rejected: SimilarPart[]; method: string; note?: string; authoritative_data: string } | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    let off = false
    setD(null)
    setErr(false)
    fetch(`/api/v1/intelligence/parts/${encodeURIComponent(partId)}/similar`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((x) => !off && setD(x))
      .catch(() => !off && setErr(true))
    return () => {
      off = true
    }
  }, [partId])
  if (err) return <p className="pix-muted">Candidates are temporarily unavailable.</p>
  if (!d) return <p className="pix-muted">Checking part type and fitment…</p>
  return (
    <div className="pix-section">
      <h4>Candidates for Engineering Review</h4>
      {d.note && <p className="pix-muted">{d.note}</p>}
      {!d.note && d.alternatives.length === 0 && (
        <p className="pix-muted">No candidate: nothing else in the catalogue is the same part type and fitted to the same machines.</p>
      )}
      {d.alternatives.map((a) => (
        <div key={a.part_id} className="pix-alt pix-alt--good_candidate">
          <div className="pix-alt__head"><strong>{a.part_id}</strong><span>{a.part_name}</span><span className="pix-rec pix-rec--review">{a.status}</span></div>
          <ul className="pix-reasons">{a.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      ))}
      {d.rejected.length > 0 && <h4>Not candidates</h4>}
      {d.rejected.map((a) => (
        <div key={a.part_id} className="pix-alt pix-alt--not_recommended">
          <div className="pix-alt__head"><strong>{a.part_id}</strong><span>{a.part_name}</span></div>
          <ul className="pix-reasons">{a.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      ))}
      <p className="pix-basis"><PiIcon name="info" size={14} /> Not approved replacements. Authoritative HCME data: {d.authoritative_data}. Text similarity is a supporting signal only.</p>
    </div>
  )
}

export function DisruptionTab({ partId }: { partId: string }) {
  const [scenario, setScenario] = useState('part_unavailable')
  const [d, setD] = useState<DisruptionBrief | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    let off = false
    setD(null)
    setErr(false)
    fetch('/api/v1/intelligence/disruption', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario, part_id: partId }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((x) => {
        if (off) return
        const aff = x.affected
        setD({
          scenario: x.scenario, summary: x.summary,
          counts: { parts: aff.parts.length, assemblies: aff.assemblies.length, machines: aff.machines.length, customers: aff.customers.length, orders: aff.orders.length },
          customers_note: aff.customers_note ?? null, notes: x.notes ?? [], provenance: x.provenance,
          mitigation: x.mitigation.map((m: { target: string; explanation: string; candidates: MitigationCandidate[] }) => ({ target: m.target, explanation: m.explanation, candidates: m.candidates.slice(0, 4) })),
        })
      })
      .catch(() => !off && setErr(true))
    return () => {
      off = true
    }
  }, [partId, scenario])
  return (
    <div className="pix-section">
      <div className="pix-scenarios" role="group" aria-label="Disruption scenario">
        {['part_unavailable', 'compliance_failure', 'stock_shortage'].map((s) => (
          <button key={s} type="button" className={`pix-chip pix-chip--btn ${scenario === s ? 'is-active' : ''}`} onClick={() => setScenario(s)}>
            {SCENARIO_LABEL[s]}
          </button>
        ))}
      </div>
      {err && <p className="pix-muted">Disruption analysis is temporarily unavailable.</p>}
      {!d && !err && <p className="pix-muted">Analysing scenario…</p>}
      {d && (
        <>
          <p className="pix-explain">{d.summary}</p>
          <DisruptionView d={d} />
        </>
      )}
    </div>
  )
}

/* ---------- KPIs ---------- */

interface Kpi {
  kpi: string
  measurable: boolean
  numerator?: number
  denominator?: number
  value_pct?: number | null
  method: string
  data_source?: string
  caveat?: string
  needs?: string | null
  demo_only?: boolean
  excluded_test_orders?: number
  demo_numerator?: number
  demo_pct?: number | null
}

export function KpiPanel({ onClose }: { onClose: () => void }) {
  const [d, setD] = useState<{ note: string; kpis: Kpi[]; demo_only: Kpi[] } | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    let off = false
    fetch('/api/v1/intelligence/kpis')
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((x) => !off && setD(x))
      .catch(() => !off && setErr(true))
    return () => {
      off = true
    }
  }, [])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="pix-overlay" role="dialog" aria-modal="true" aria-label="KPIs" onClick={onClose}>
      <div className="pix-modal" onClick={(e) => e.stopPropagation()}>
        <header className="pix-modal__head">
          <div>
            <h3><PiIcon name="graph" size={22} /> KPIs</h3>
            <p>{d?.note ?? 'Calculated live from the graph'}</p>
          </div>
          <button type="button" className="pix-modal__x" onClick={onClose} aria-label="Close KPIs"><PiIcon name="x" size={18} /></button>
        </header>
        <div className="pix-modal__body">
          {err && <p className="pix-muted">KPIs are temporarily unavailable.</p>}
          {!d && !err && <p className="pix-muted">Calculating…</p>}
          {d?.kpis.map((k) => <KpiCard key={k.kpi} k={k} />)}
          {d && d.demo_only.length > 0 && <h4 className="pix-kpi__group">Demo only</h4>}
          {d?.demo_only.map((k) => <KpiCard key={k.kpi} k={k} />)}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ k }: { k: Kpi }) {
  const real = !k.demo_only && !(k.data_source ?? '').startsWith('SYNTHETIC')
  return (
    <div className={`pix-kpi ${k.demo_only ? 'pix-kpi--off' : ''}`}>
      <div className="pix-kpi__top">
        <strong>{k.kpi}</strong>
        <span className="pix-kpi__val">{!k.measurable ? 'not measurable' : `${k.value_pct}%`}</span>
      </div>
      {k.numerator != null && k.denominator != null && <p className="pix-muted">{k.numerator} of {k.denominator}</p>}
      {k.demo_numerator != null && (
        <p className="pix-muted">Demo supplier links (SYNTHETIC_DEMO): {k.demo_numerator} of {k.denominator} ({k.demo_pct}%)</p>
      )}
      <p className="pix-muted">{k.method}</p>
      {k.excluded_test_orders ? <p className="pix-muted">{k.excluded_test_orders} test-session orders are not counted.</p> : null}
      <p className="pix-kpi__basis">
        <span className={`pix-chip ${real ? 'pix-chip--real' : 'pix-chip--demo'}`}>{real ? 'REAL data' : k.demo_only ? 'DEMO only' : 'SYNTHETIC_DEMO data'}</span>
        {k.needs ? <span className="pix-muted"> Needs: {k.needs}</span> : null}
      </p>
    </div>
  )
}

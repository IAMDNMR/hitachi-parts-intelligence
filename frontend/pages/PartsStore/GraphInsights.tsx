import { useEffect, useState } from 'react'
import { PiIcon, type PiIconName } from './PiIcons'
import { DisruptionTab, SimilarTab } from './PartsAnalysis'

/**
 * Graph Insights — four tabs (Impact · Compliance · Supplier Risk ·
 * Mitigation), all from ONE call to GET /api/v1/intelligence/parts/{id}/graph-insights.
 * Every tab ends with its `data_basis` line so source vs synthetic data is visible.
 */

type Tab = 'impact' | 'compliance' | 'risk' | 'mitigation' | 'similar' | 'disruption'

const TABS: { key: Tab; label: string; icon: PiIconName }[] = [
  { key: 'impact', label: 'Impact', icon: 'truck' },
  { key: 'compliance', label: 'Compliance', icon: 'shield' },
  { key: 'risk', label: 'Supplier Risk', icon: 'factory' },
  { key: 'mitigation', label: 'Mitigation', icon: 'bolt' },
  { key: 'similar', label: 'Similar Parts', icon: 'search' },
  { key: 'disruption', label: 'Disruption', icon: 'alert' },
]

/** Which data behind each tab is real, synthetic demo, or not connected (shown as chips above the tab body). */
const TAB_BASIS: Record<Tab, ['real' | 'demo' | 'off', string][]> = {
  impact: [['real', 'REAL: machines & fitment'], ['demo', 'SYNTHETIC_DEMO: assemblies, BOM qty, criticality']],
  compliance: [['real', 'REAL: regulation names'], ['demo', 'SYNTHETIC_DEMO: assembly requirements & certificates']],
  risk: [['real', 'REAL: 1,720-supplier master'], ],
  mitigation: [['real', 'REAL: catalogue & fitment'], ['demo', 'SYNTHETIC_DEMO: suppliers, stock, certificates']],
  similar: [['real', 'REAL: catalogue & fitment']],
  disruption: [],
}

interface Assembly { name: string; criticality: 'high' | 'medium' | 'low'; qty: number; unit: string; machines: number }
interface Supplier { supplier_id: string; name: string; country: string; region: string; tier: number; share_pct: number; role: string; synthetic?: boolean }
interface Concentration { supplier_id: string; name: string; region: string; country: string; parts: number; critical_parts: number; sole_source_critical: number }
interface Alternative {
  part_id: string; part_number: string | null; part_name: string | null
  similarity_pct: number; mitigation_score: number; suppliers: string[]
  compliance_gaps: string[]; depot_stock: number | null; availability: string
}

interface GeoDistribution { code: string; country: string; count: number }
interface SampleSupplier { supplier_number: string; name: string; city: string | null; country: string }

interface GraphInsightsResponse {
  part: { part_id: string; part_number: string | null; part_name: string | null }
  impact: {
    affected_machines: number; total_bom_qty: number; critical_paths: Assembly[]
    machines: { machine_id: string; name: string; family: string | null; category: string | null }[]
    assemblies: Assembly[]; data_basis: string
  }
  compliance: {
    requirements: { compliance_id: string; name: string; standard: string; via: string; parent: string | null; held: boolean }[]
    gaps: { requirement: string; standard: string; required_by: string }[]
    status: string; data_basis: string
  }
  supplier_risk: {
    status?: 'CONNECTED' | 'NOT_CONNECTED'
    connected?: boolean
    reason?: string
    supplier_master_count?: number
    available_dimensions?: string[]
    missing_relationship?: string
    required_source?: string
    risk_calculations?: string
    part_suppliers: Supplier[]
    dual_source: boolean
    concentration: Concentration[]
    spof: { is_spof: boolean; reason: string }
    geographic_distribution?: GeoDistribution[]
    sample_suppliers?: SampleSupplier[]
    data_basis: string
    provenance?: string
  }
  mitigation: {
    executive_summary: string; affected_machines: number; preferred_substitutes_exist: boolean
    steps: string[]; alternatives: Alternative[]; data_basis: string
  }
}

function DataBasis({ text }: { text: string }) {
  return (
    <p className="pix-basis">
      <PiIcon name="info" size={14} />
      {text}
    </p>
  )
}

export default function GraphInsightsPanel({ partId, onClose }: { partId: string; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>('impact')
  const [data, setData] = useState<GraphInsightsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setData(null)
    setError(null)
    fetch(`/api/v1/intelligence/parts/${encodeURIComponent(partId)}/graph-insights`)
      .then((res) => {
        if (!res.ok) throw new Error(String(res.status))
        return res.json()
      })
      .then((d: GraphInsightsResponse) => !cancelled && setData(d))
      .catch(() => !cancelled && setError('Graph Insights are temporarily unavailable.'))
    return () => {
      cancelled = true
    }
  }, [partId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="pix-overlay" role="dialog" aria-modal="true" aria-label="Graph Insights" onClick={onClose}>
      <div className="pix-modal" onClick={(e) => e.stopPropagation()}>
        <header className="pix-modal__head">
          <div>
            <h3>
              <PiIcon name="graph" size={22} />
              Graph Insights
            </h3>
            <p>
              {partId}
              {data?.part.part_name ? ` — ${data.part.part_name}` : ''}
            </p>
          </div>
          <button type="button" className="pix-modal__x" onClick={onClose} aria-label="Close Graph Insights">
            <PiIcon name="x" size={18} />
          </button>
        </header>

        <nav className="pix-tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              className={tab === t.key ? 'is-active' : undefined}
              onClick={() => setTab(t.key)}
            >
              <PiIcon name={t.icon} size={15} />
              {t.label}
            </button>
          ))}
        </nav>

        {tab !== 'disruption' && (
          <div className="pix-prov pix-prov--tab" aria-label="Data basis of this tab">
            {TAB_BASIS[tab].map(([kind, label]) => (
              <span key={label} className={`pix-chip pix-chip--${kind}`}>{label}</span>
            ))}
          </div>
        )}

        <div className="pix-modal__body">
          {error && <p className="pix-error">{error}</p>}
          {!error && !data && <p className="pix-muted">Traversing the graph…</p>}
          {data && tab === 'impact' && <ImpactTab d={data.impact} />}
          {data && tab === 'compliance' && <ComplianceTab d={data.compliance} />}
          {data && tab === 'risk' && <SupplierRiskTab d={data.supplier_risk} />}
          {data && tab === 'mitigation' && <MitigationTab d={data.mitigation} />}
          {data && tab === 'similar' && <SimilarTab partId={partId} />}
          {data && tab === 'disruption' && <DisruptionTab partId={partId} />}
        </div>

        <footer className="pix-modal__foot">
          <button type="button" className="pix-btn pix-btn--primary" onClick={() => setTab('disruption')} disabled={!data}>
            <PiIcon name="bolt" size={16} />
            Analyse Disruption
          </button>
          <button type="button" className="pix-btn" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </div>
  )
}

function ImpactTab({ d }: { d: GraphInsightsResponse['impact'] }) {
  return (
    <div className="pix-section">
      <div className="pix-stats">
        <div className="pix-stat pix-stat--red">
          <span>Affected machines</span>
          <strong>{d.affected_machines}</strong>
        </div>
        <div className="pix-stat pix-stat--amber">
          <span>Total BOM qty</span>
          <strong>{d.total_bom_qty}</strong>
        </div>
      </div>

      <h4><PiIcon name="alert" size={16} /> Critical Paths</h4>
      {d.critical_paths.length ? (
        d.critical_paths.map((a) => (
          <div key={a.name} className="pix-row pix-row--critical">
            {a.name} (qty {a.qty})
          </div>
        ))
      ) : (
        <p className="pix-muted">No high-criticality assembly uses this part.</p>
      )}

      <h4><PiIcon name="truck" size={16} /> Machines</h4>
      {d.machines.length ? (
        d.machines.map((m) => (
          <div key={m.machine_id} className="pix-row">
            <strong>{m.name}</strong>
            <span className="pix-muted">{[m.family, m.category].filter(Boolean).join(' · ')}</span>
          </div>
        ))
      ) : (
        <p className="pix-muted">This part is not fitted to any machine in the HCME Europe dataset.</p>
      )}

      <h4><PiIcon name="layers" size={16} /> Assemblies</h4>
      {d.assemblies.map((a) => (
        <div key={a.name} className="pix-row">
          <strong>{a.name}</strong>
          <span className={`pix-crit pix-crit--${a.criticality}`}>({a.criticality})</span>
          <span className="pix-row__end">qty {a.qty}{a.unit === 'fill' ? ' fills' : ''}</span>
        </div>
      ))}
      <DataBasis text={d.data_basis} />
    </div>
  )
}

function ComplianceTab({ d }: { d: GraphInsightsResponse['compliance'] }) {
  return (
    <div className="pix-section">
      {d.requirements.length ? (
        d.requirements.map((r) => (
          <div key={`${r.compliance_id}-${r.via}`} className="pix-row">
            <strong>{r.name}</strong>
            <span className="pix-muted">via {r.via}</span>
            {r.parent && <span className="pix-link">← {r.parent}</span>}
            <span className={`pix-row__end pix-held ${r.held ? 'is-held' : 'is-gap'}`}>{r.held ? 'Held' : 'Missing'}</span>
          </div>
        ))
      ) : (
        <p className="pix-muted">No compliance requirement is recorded for this part.</p>
      )}

      <h4 className="pix-h-gap"><PiIcon name="alert" size={16} /> Compliance Gaps</h4>
      {d.gaps.length ? (
        d.gaps.map((g) => (
          <div key={`${g.requirement}-${g.required_by}`} className="pix-row pix-row--gap">
            Missing <strong>{g.requirement}</strong> required by {g.required_by}
          </div>
        ))
      ) : (
        <p className="pix-muted">No compliance gaps: every requirement recorded for this part is held.</p>
      )}
      <DataBasis text={d.data_basis} />
    </div>
  )
}

function SupplierRiskTab({ d }: { d: GraphInsightsResponse['supplier_risk'] }) {
  const isConnected = d.status === 'CONNECTED' && d.part_suppliers && d.part_suppliers.length > 0

  if (!isConnected) {
    return (
      <div className="pix-section">
        <div className="pix-risk-grid">
          <div className="pix-risk-card">
            <span className="pix-risk-card__label">Supplier Master</span>
            <strong className="pix-risk-card__val">
              {d.supplier_master_count ? d.supplier_master_count.toLocaleString() : '1,720'}
            </strong>
            <span className="pix-risk-card__sub">HCME suppliers (SAP)</span>
            <span className="pix-badge pix-badge--real">SOURCE-DERIVED</span>
          </div>
        </div>
        <p className="pix-muted pix-small">
          The HCME supplier master gives each supplier's number, name, city and country. It does not say which supplier delivers which part, so no
          supplier is shown as this part's source.
        </p>

        {d.geographic_distribution && d.geographic_distribution.length > 0 && (
          <div className="pix-geo-section">
            <h4><PiIcon name="pin" size={16} /> Suppliers by country</h4>
            <p className="pix-muted pix-small">
              Where HCME's suppliers are located (SOURCE-DERIVED).
            </p>
            <div className="pix-geo-grid">
              {d.geographic_distribution.map((g) => (
                <div key={g.code} className="pix-geo-item">
                  <span className="pix-geo-country">{g.country} ({g.code})</span>
                  <strong className="pix-geo-count">{g.count.toLocaleString()}</strong>
                  <span className="pix-geo-sub">suppliers</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {d.sample_suppliers && d.sample_suppliers.length > 0 && (
          <div className="pix-sample-section">
            <h4><PiIcon name="factory" size={16} /> HCME supplier records (sample)</h4>
            <div className="pix-sample-list">
              {d.sample_suppliers.map((s) => (
                <div key={s.supplier_number} className="pix-row">
                  <div>
                    <strong>{s.name}</strong>
                    <span className="pix-chip">#{s.supplier_number.replace(/^0+/, '')}</span>
                  </div>
                  <span className="pix-row__end">
                    <PiIcon name="pin" size={13} /> {[s.city, s.country].filter(Boolean).join(', ')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <DataBasis text={d.data_basis} />
      </div>
    )
  }

  return (
    <div className="pix-section">
      <div className="pix-supplier">
        <h4>This Part's Supplier{d.part_suppliers.length > 1 ? 's' : ''} {d.provenance === 'SYNTHETIC_DEMO' && <span className="pix-chip pix-chip--demo">SYNTHETIC_DEMO</span>}</h4>
        {d.part_suppliers.map((s) => (
          <div key={s.supplier_id} className="pix-supplier__row">
            <strong>{s.name}</strong>
            <span className="pix-muted">{s.region} · {s.country} · Tier {s.tier}</span>
            <span className="pix-row__end">
              <span className="pix-chip">{s.share_pct}% share</span>
              <span className={`pix-chip ${d.dual_source ? 'pix-chip--green' : 'pix-chip--red'}`}>
                {d.dual_source ? 'Dual-source' : 'Sole source'}
              </span>
            </span>
          </div>
        ))}
      </div>

      <h4>Platform Concentration Risk</h4>
      <p className="pix-muted pix-small">Critical parts per supplier across catalogue supplier links</p>
      {d.concentration.map((c) => (
        <div key={c.supplier_id} className="pix-row">
          <strong>{c.name}</strong>
          <span className="pix-muted">{c.region} · {c.country}</span>
          <span className="pix-row__end pix-stack">
            <span>{c.critical_parts} critical part{c.critical_parts === 1 ? '' : 's'}</span>
            <span>{c.sole_source_critical} sole-source</span>
          </span>
        </div>
      ))}

      <h4>Single Point of Failure (this part)</h4>
      <div className={`pix-row ${d.spof.is_spof ? 'pix-row--gap' : ''}`}>{d.spof.reason}</div>
      <DataBasis text={d.data_basis} />
    </div>
  )
}

function MitigationTab({ d }: { d: GraphInsightsResponse['mitigation'] }) {
  return (
    <div className="pix-section">
      <div className="pix-summary">
        <h4>Executive Summary</h4>
        <p>{d.executive_summary}</p>
        <div className="pix-summary__facts">
          <span><strong>{d.affected_machines}</strong> affected machine models</span>
          <span>
            Approved substitute: <strong>none (no HCME interchangeability data loaded)</strong>
          </span>
        </div>
      </div>

      <ol className="pix-steps">
        {d.steps.map((s) => (
          <li key={s}>
            <PiIcon name="check" size={13} />
            {s}
          </li>
        ))}
      </ol>

      <h4>Candidates for Engineering Review</h4>
      {d.alternatives.length ? (
        d.alternatives.map((a) => (
          <div key={a.part_id} className="pix-alt">
            <div className="pix-alt__head">
              <strong>{a.part_id}</strong>
              <span>{a.part_name}</span>
            </div>
            <div className="pix-alt__grid">
              <span>Text similarity <strong>{a.similarity_pct}%</strong> (supporting only)</span>
              <span>Supplier <strong>{a.suppliers.join(', ') || 'Unknown'}</strong></span>
              <span>
                Depot stock <strong>{a.depot_stock == null ? 'Unknown' : a.depot_stock}</strong>
              </span>
            </div>
            {a.compliance_gaps.length ? (
              <div className="pix-alt__gaps">
                Compliance gaps: {a.compliance_gaps.map((g) => <span key={g} className="pix-chip pix-chip--red">{g}</span>)}
              </div>
            ) : (
              <div className="pix-alt__gaps pix-alt__gaps--ok">No compliance gaps</div>
            )}
          </div>
        ))
      ) : (
        <p className="pix-muted">No sufficiently similar alternative exists in the catalogue.</p>
      )}
      <DataBasis text={d.data_basis} />
    </div>
  )
}

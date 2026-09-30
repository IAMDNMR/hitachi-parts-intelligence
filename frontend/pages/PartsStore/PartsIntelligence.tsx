import { useEffect, useRef, useState, type FormEvent } from 'react'
import GraphInsightsPanel from './GraphInsights'
import NetworkGraph, { type GraphView } from './NetworkGraph'
import { DisruptionView, KpiPanel, type DisruptionBrief } from './PartsAnalysis'
import { PiIcon, type PiIconName } from './PiIcons'
import { trackInteraction } from '../../lib/analytics'
import { dealerCity, tidyAddress, tidyCase } from './dealerFormat'
import './PartsIntelligence.css'

/** A matched part in the result grid — POST /api/v1/intelligence/query → data.candidates. */
export interface PartCard {
  part_id: string
  part_number: string | null
  part_name: string | null
  description: string | null
  match_pct: number | null
  category: string | null
  subcategory: string | null
  assembly: string | null
  fits_count: number
  assessment: string
  risks?: string[]
  commercial?: { availability: { status: string }; price: { status: string }; lead_time: { status: string } }
  specs: {
    genuine_hitachi_part: string | null
    wear_part: string | null
    service_part: string | null
    consumable: string | null
    record_class: string | null
    confidence: string | null
    source_id: string | null
    source_date: string | null
  }
}

interface Dealer {
  dealer_id: string
  dealer_name: string
  city: string | null
  country: string
  address: string | null
  phone: string | null
  email: string | null
  website: string | null
  distance_km?: number
}

/** A supplier from the HCME SAP supplier master (number, name, city, country). */
interface SupplierRow {
  supplier_number: string
  name: string
  city: string | null
  country: string
  country_name: string | null
  possible_duplicate_of: string[] | null
}

/** A machine model from a Part → Machine fitment (HAS_PART_FITMENT) or a machine listing. */
interface MachineRow {
  machine_id: string
  model: string
  category?: string | null
  family?: string | null
  machine_category?: string | null
  operating_weight?: number | string | null
}

/** Explicit result type — controls what the UI renders; nothing is inferred from earlier turns. */
type ResultType =
  | 'MACHINE_RESULTS' | 'PART_RESULTS' | 'DEALER_RESULTS' | 'SUPPLIER_RESULTS' | 'NETWORK_RESULTS'
  | 'ORDER_JOURNEY' | 'DISRUPTION_ANALYSIS' | 'NO_RELATIONSHIP' | 'INSUFFICIENT_DATA' | 'UNSUPPORTED_QUERY' | 'CLARIFICATION_REQUIRED'

interface AssistantResponse {
  intent: string
  result_type: ResultType
  /** Set only when THIS response is about one Part — the only case Graph Insights is offered. */
  insights_part_id: string | null
  answer: string
  needs_clarification: boolean
  graph_path: string[]
  resolved_part_id: string | null
  graph: GraphView | null
  data: { candidates?: PartCard[]; dealers?: Dealer[]; suppliers?: SupplierRow[]; machines?: MachineRow[]; machine_options?: { machine_id: string; model: string; fitted_parts: number }[]; part_id?: string | null; disruption?: DisruptionBrief }
  pipeline: {
    extraction: string
    answer: string
    timings_ms: { understand: number; graph: number; explain: number; total: number }
  }
}

/** A verified question from GET /api/v1/intelligence/catalog (Aura :QuestionTemplate). */
interface CatalogCategory {
  name: string
  questions: { question_id: string; text: string; intent: string; result_type: string }[]
}

const CATEGORY_ICON: Record<string, PiIconName> = {
  'Parts Search': 'search',
  Dealers: 'pin',
  Relationships: 'graph',
  Suppliers: 'factory',
  'Machines & Fleet': 'truck',
  'Orders & Service': 'clock',
}

const STEPS = ['Understand the question', 'Traverse the HCME graph', 'Validate & explain'] as const

/** One question → answer exchange in the conversation thread. */
interface Turn {
  id: number
  question: string
  /** The original question when this turn answers a clarifying question. */
  replyTo: string | null
  response: AssistantResponse | null
  error: string | null
  elapsedMs: number
}

export default function PartsIntelligencePanel({
  onSelectPartNumber,
}: {
  onSelectPartNumber: (partNumber: string) => void
}) {
  const [query, setQuery] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [loading, setLoading] = useState(false)
  const [contextPartId, setContextPartId] = useState<string | null>(null)
  const [insightsPartId, setInsightsPartId] = useState<string | null>(null)

  const endRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const last = turns[turns.length - 1]
  const pending = last?.response?.needs_clarification
    ? { question: last.replyTo ? `${last.replyTo} in ${last.question}` : last.question, prompt: last.response.answer }
    : null

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns, loading])

  const ask = async (e?: FormEvent, overrideText?: string) => {
    e?.preventDefault()
    const q = (overrideText ?? query).trim()
    if (!q || loading) return
    const turn: Turn = { id: Date.now(), question: q, replyTo: pending?.question ?? null, response: null, error: null, elapsedMs: 0 }
    setTurns((t) => [...t, turn])
    setQuery('')
    setLoading(true)
    trackInteraction('pi_query', q) // only recorded if the visitor accepted the cookie banner
    const started = performance.now()
    try {
      const payload: Record<string, any> = {
        query: q,
        limit: 9,
        // Only an explicit back-reference ("this part", "the same part") may reuse the last part.
        context_part_id: /\b(this|that|the same|these|those)\s+(part|item|component)s?\b|\bsame part\b/i.test(q) ? contextPartId : null,
        follow_up_to: pending?.question ?? null,
      }
      const res = await fetch('/api/v1/intelligence/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(String(res.status))
      const data: AssistantResponse = await res.json()
      turn.response = data
      // Each response replaces the context (null when it is not about a Part) — never accumulates.
      setContextPartId(data.insights_part_id)
    } catch {
      turn.error = 'Parts Intelligence is temporarily unavailable. Please try again.'
    } finally {
      turn.elapsedMs = performance.now() - started
      setTurns((t) => t.map((x) => (x.id === turn.id ? { ...turn } : x)))
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const askQuestion = (text: string) => {
    setQuery(text)
    void ask(undefined, text)
  }

  const [catalog, setCatalog] = useState<CatalogCategory[] | null>(null)
  const [catalogError, setCatalogError] = useState(false)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [sideHidden, setSideHidden] = useState(false)
  const [kpiOpen, setKpiOpen] = useState(false)

  // The catalogue is read from Aura (verified questions only); nothing is mirrored by hand in the UI.
  useEffect(() => {
    let cancelled = false
    fetch('/api/v1/intelligence/catalog')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d: { categories: CatalogCategory[] }) => !cancelled && setCatalog(d.categories))
      .catch(() => !cancelled && setCatalogError(true))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section className={`pix pix-shell ${sideHidden ? 'is-side-hidden' : ''}`} aria-label="Parts Intelligence">
      {sideHidden && (
        <button type="button" className="pix-side__open" onClick={() => setSideHidden(false)} aria-label="Show question catalog" title="Show question catalog">
          <PiIcon name="layers" size={20} />
        </button>
      )}
      <aside className="pix-side" aria-label="Question Catalog" hidden={sideHidden}>
        <div className="pix-side__head">
          <span className="pix-side__icon"><PiIcon name="layers" size={22} /></span>
          <div>
            <strong>Question Catalog</strong>
            <small>Click a question to get started</small>
          </div>
          <button type="button" className="pix-side__collapse pix-side__kpi" onClick={() => setKpiOpen(true)} aria-label="Show KPIs" title="KPIs">
            <PiIcon name="graph" size={18} />
          </button>
          <button type="button" className="pix-side__collapse" onClick={() => setSideHidden(true)} aria-label="Hide question catalog" title="Hide question catalog">
            <PiIcon name="chevron" size={18} />
          </button>
        </div>
        {catalogError && <p className="pix-muted pix-side__note">The question catalogue is unavailable right now. You can still type a question.</p>}
        {!catalog && !catalogError && <p className="pix-muted pix-side__note">Loading questions…</p>}
        {catalog?.map((cat) => {
          const shut = collapsed[cat.name]
          return (
            <div key={cat.name} className="pix-side__group">
              <button
                type="button"
                className="pix-side__cat"
                aria-expanded={!shut}
                onClick={() => setCollapsed((c) => ({ ...c, [cat.name]: !c[cat.name] }))}
              >
                <span className="pix-side__cat-icon"><PiIcon name={CATEGORY_ICON[cat.name] ?? 'tag'} size={20} /></span>
                <span className="pix-side__cat-name">{cat.name}</span>
                <span className="pix-side__count">{cat.questions.length} questions</span>
                <span className={`pix-side__chev ${shut ? '' : 'is-open'}`}><PiIcon name="chevron" size={16} /></span>
              </button>
              {!shut && (
                <ul>
                  {cat.questions.map((q) => (
                    <li key={q.question_id}>
                      <button type="button" disabled={loading} onClick={() => askQuestion(q.text)}>{q.text}</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </aside>

      <div className="pix-main">
        <header className="pix-main__head">
          <span className="pix-main__icon"><PiIcon name="graph" size={26} /></span>
          <div>
            <h2>Parts Intelligence</h2>
            <p>Ask about parts, dealers, suppliers and their relationships — powered by Hitachi After-Sales data.</p>
          </div>
          {turns.length > 0 && (
            <button type="button" className="pix-btn pix-head__new" onClick={() => { setTurns([]); setContextPartId(null) }}>
              New conversation
            </button>
          )}
        </header>

        <div className="pix-thread" aria-live="polite">
          {turns.length === 0 && (
            <div className="pix-welcome">
              <svg width="120" height="90" viewBox="0 0 120 90" fill="none" aria-hidden="true">
                <rect x="4" y="34" width="46" height="34" rx="12" fill="#ffd9c9" />
                <rect x="70" y="30" width="46" height="34" rx="12" stroke="#ffb999" strokeWidth="2.5" />
                <rect x="34" y="8" width="52" height="40" rx="12" stroke="#ff5a1f" strokeWidth="3" fill="#fff" />
                <circle cx="48" cy="28" r="3" fill="#ff5a1f" /><circle cx="60" cy="28" r="3" fill="#ff5a1f" /><circle cx="72" cy="28" r="3" fill="#ff5a1f" />
              </svg>
              <h3>How can I help you today?</h3>
              <p>Type your question or choose one from the catalog on the left.</p>
            </div>
          )}
          {turns.map((t, i) => (
            <TurnView
              key={t.id}
              turn={t}
              loading={loading && i === turns.length - 1}
              onInsights={setInsightsPartId}
              onSelectPartNumber={onSelectPartNumber}
              onAsk={askQuestion}
            />
          ))}
          <div ref={endRef} />
        </div>

        <div className={`pix-composer ${pending ? 'pix-composer--reply' : ''}`}>
          {pending && (
            <div className="pix-ask__reply">
              Replying to: <em>{pending.prompt}</em>
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={query}
            maxLength={2000}
            rows={2}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void ask()
              }
            }}
            placeholder={pending ? 'Type your answer, e.g. Netherlands, Eindhoven or 5611 AB…' : 'Type your question here...'}
            aria-label={pending ? 'Answer the clarifying question' : 'Ask Parts Intelligence'}
          />
          <button type="button" className="pix-send" onClick={() => void ask()} disabled={loading || !query.trim()} aria-label="Send question">
            <PiIcon name="send" size={20} />
          </button>
          <span className="pix-count">{query.length}/2000</span>
        </div>
      </div>

      {kpiOpen && <KpiPanel onClose={() => setKpiOpen(false)} />}
      {insightsPartId && <GraphInsightsPanel partId={insightsPartId} onClose={() => setInsightsPartId(null)} />}
    </section>
  )
}

function TurnView({
  turn,
  loading,
  onInsights,
  onSelectPartNumber,
  onAsk,
}: {
  turn: Turn
  loading: boolean
  onInsights: (partId: string) => void
  onSelectPartNumber: (partNumber: string) => void
  onAsk: (text: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const r = turn.response
  const cards = r?.data.candidates ?? []
  const dealers = r?.data.dealers ?? []
  const suppliers = r?.data.suppliers ?? []
  const machines = r?.data.machines ?? []
  const focusPart = r?.insights_part_id ?? null
  const noData = r?.result_type === 'NO_RELATIONSHIP' || r?.result_type === 'INSUFFICIENT_DATA' || r?.result_type === 'UNSUPPORTED_QUERY'
  const t = r?.pipeline.timings_ms

  return (
    <article className="pix-turn">
      <p className="pix-q">{turn.question}</p>

      {loading && (
        <div className="pix-workflow pix-workflow--live">
          <span className="pix-workflow__icon"><PiIcon name="clock" size={16} /></span>
          <span>Understanding the question and traversing the HCME graph…</span>
        </div>
      )}

      {turn.error && <p className="pix-error">{turn.error}</p>}

      {r && (
        <>
          <div className={`pix-answer ${r.needs_clarification || noData ? 'pix-answer--ask' : ''}`}>
            <p>{r.answer}</p>
            {focusPart && cards.length <= 1 && (
              <button type="button" className="pix-btn pix-btn--ghost" onClick={() => onInsights(focusPart)}>
                <PiIcon name="graph" size={16} /> Graph Insights for {focusPart}
              </button>
            )}
          </div>

          <button type="button" className="pix-meta" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
            <PiIcon name="clock" size={13} />
            Workflow Execution · {(turn.elapsedMs / 1000).toFixed(2)}s · {STEPS.length} steps ·{' '}
            {r.pipeline.answer === 'gemini' ? 'answer by Gemini from graph evidence' : 'answer from graph rules'}
            <span className={open ? 'is-open' : ''}><PiIcon name="chevron" size={13} /></span>
          </button>
          {open && t && (
            <ol className="pix-workflow__steps pix-workflow__steps--inline">
              {STEPS.map((s, i) => (
                <li key={s} className="is-done">
                  <span className="pix-workflow__dot"><PiIcon name="check" size={12} /></span>
                  {s}
                  <em>{[t.understand, t.graph, t.explain][i]} ms</em>
                </li>
              ))}
              {r.graph_path.length > 0 && <li className="pix-workflow__path">Graph path: {r.graph_path.join(' → ')}</li>}
            </ol>
          )}

          {r.graph && <NetworkGraph graph={r.graph} />}

          {r.data.disruption && <DisruptionView d={r.data.disruption} />}

          {(r.data.machine_options?.length ?? 0) > 0 && (
            <div className="pix-select">
              <span>Narrow to one machine model:</span>
              {r.data.machine_options!.map((m) => (
                <button key={m.machine_id} type="button" className="pix-chip pix-chip--btn" onClick={() => onAsk(`Tell me about ${m.model}.`)}>
                  {m.model} · {m.fitted_parts} parts
                </button>
              ))}
            </div>
          )}

          {machines.length > 0 && (
            <>
              <h4 className="pix-subhead">
                Machines · {r.intent === 'impact_analysis' ? 'HAS_PART_FITMENT (HCME fitment data)' : 'HCME machine catalogue'}
              </h4>
              <ul className="pix-dealers pix-suppliers">
                {machines.slice(0, showAll ? machines.length : 40).map((m) => (
                  <li key={m.machine_id}>
                    <div className="pix-dealers__top"><strong>{m.model}</strong></div>
                    <span className="pix-dealers__loc">
                      {[m.family, m.category || m.machine_category].filter(Boolean).join(' · ') || 'Machine'}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {dealers.length > 0 && (
            <ul className="pix-dealers">
              {dealers.slice(0, showAll ? dealers.length : 24).map((d) => (
                <li key={d.dealer_id}>
                  <div className="pix-dealers__top">
                    <strong>{tidyCase(d.dealer_name)}</strong>
                    {d.distance_km != null && <span className="pix-chip">{d.distance_km} km</span>}
                    {/^account\s?manager/i.test(d.address ?? '') && <span className="pix-chip">Account manager</span>}
                  </div>
                  <span className="pix-dealers__loc">
                    <PiIcon name="pin" size={13} /> {[dealerCity(d.city, d.address), d.country].filter(Boolean).join(', ')}
                  </span>
                  {d.address && <span className="pix-dealers__addr">{tidyAddress(d.address)}</span>}
                  <div className="pix-dealers__contact">
                    {d.phone && <a href={`tel:${d.phone.replace(/[^+\d]/g, '')}`}>{d.phone}</a>}
                    {d.email && <a href={`mailto:${d.email}`}>{d.email}</a>}
                    {d.website && (
                      <a href={d.website} target="_blank" rel="noreferrer">
                        Website ↗
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {(dealers.length > 24 || machines.length > 40) && (
            <button type="button" className="pix-btn" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Show fewer' : `Show all ${Math.max(dealers.length, machines.length)}`}
            </button>
          )}

          {suppliers.length > 0 && (
            <>
              <h4 className="pix-subhead">Suppliers · HCME SAP supplier master</h4>
              <ul className="pix-dealers pix-suppliers">
                {suppliers.map((sp) => (
                  <li key={sp.supplier_number}>
                    <div className="pix-dealers__top">
                      <strong>{sp.name}</strong>
                      <span className="pix-chip">#{sp.supplier_number.replace(/^0+/, '')}</span>
                    </div>
                    <span className="pix-dealers__loc">
                      <PiIcon name="pin" size={13} /> {[sp.city, sp.country_name || sp.country].filter(Boolean).join(', ')}
                    </span>
                    {sp.possible_duplicate_of && (
                      <span className="pix-dealers__addr pix-muted">
                        Same name as supplier {sp.possible_duplicate_of.map((n) => n.replace(/^0+/, '')).join(', ')}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}

          {cards.length > 0 && (
            <ul className="pix-cards">
              {cards.map((c) => (
                <ResultCard
                  key={c.part_id}
                  card={c}
                  onInsights={() => onInsights(c.part_id)}
                  onStore={c.part_number ? () => onSelectPartNumber(c.part_number!) : undefined}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </article>
  )
}

function ResultCard({ card: c, onInsights, onStore }: { card: PartCard; onInsights: () => void; onStore?: () => void }) {
  const [open, setOpen] = useState(false)
  const yesNo = (v: string | null) => (v === 'Yes' ? 'Yes' : v === 'No' ? 'No' : 'Not stated')
  return (
    <li className="pix-card">
      <div className="pix-card__top">
        <h3>{c.part_id}</h3>
        {c.match_pct != null && <span className="pix-card__pct">{c.match_pct}%</span>}
      </div>
      <p className="pix-card__name">{c.part_name}</p>

      <div className="pix-tiles">
        <Tile icon="hash" label="Part number" value={c.part_number || 'Not published'} />
        <Tile icon="tag" label="Category" value={c.category || '—'} />
        <Tile icon="cog" label="Assembly" value={c.assembly || '—'} />
        <Tile icon="truck" label="Fits" value={c.fits_count === 0 ? 'No fitment recorded' : `${c.fits_count} machine${c.fits_count === 1 ? '' : 's'}`} />
      </div>

      {c.subcategory && <span className="pix-type">{c.subcategory}</span>}
      <p className="pix-assess"><PiIcon name="info" size={15} /> {c.assessment}</p>
      {c.commercial && (() => {
        const bits = ([['Stock', c.commercial.availability.status], ['Price', c.commercial.price.status], ['Lead time', c.commercial.lead_time.status]] as [string, string][])
          .filter(([, st]) => st !== 'NOT_CONNECTED').map(([k, st]) => `${k}: ${st}`)
        return bits.length ? <p className="pix-muted">{bits.join(' · ')}</p> : null
      })()}
      {c.risks && c.risks.length > 0 && (
        <ul className="pix-risks">{c.risks.map((x) => <li key={x}>{x}</li>)}</ul>
      )}

      <div className="pix-card__actions">
        <button type="button" className="pix-btn pix-btn--primary" onClick={onInsights}>
          <PiIcon name="graph" size={15} /> Graph Insights
        </button>
        {onStore && (
          <button type="button" className="pix-btn" onClick={onStore}>View in Store</button>
        )}
      </div>

      <button type="button" className="pix-card__toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? 'Hide Details' : 'View Full Details'}
        <span className={open ? 'is-open' : ''}><PiIcon name="chevron" size={15} /></span>
      </button>

      {open && (
        <div className="pix-card__details">
          <h4><PiIcon name="bolt" size={15} /> Technical Specifications</h4>
          <div className="pix-tiles">
            <Tile label="Genuine Hitachi part" value={yesNo(c.specs.genuine_hitachi_part)} />
            <Tile label="Wear part" value={yesNo(c.specs.wear_part)} />
            <Tile label="Service part" value={yesNo(c.specs.service_part)} />
            <Tile label="Consumable" value={yesNo(c.specs.consumable)} />
            <Tile label="Source" value={[c.specs.source_id, c.specs.source_date].filter(Boolean).join(' · ') || 'Unknown'} />
            <Tile label="Confidence" value={c.specs.confidence || 'Unknown'} />
          </div>
          {c.description && (
            <>
              <h4>Description</h4>
              <p className="pix-card__desc">{c.description}</p>
            </>
          )}
        </div>
      )}
    </li>
  )
}

function Tile({ icon, label, value }: { icon?: 'hash' | 'tag' | 'cog' | 'truck'; label: string; value: string }) {
  return (
    <div className="pix-tile">
      <span>
        {icon && <PiIcon name={icon} size={13} />}
        {label}
      </span>
      <strong>{value}</strong>
    </div>
  )
}

import './NetworkGraph.css'

/** Mirrors backend/app/modules/intelligence/graph_view.py's GraphNode/GraphEdge shape. */
export interface GraphNode {
  id: string
  type: string
  label: string
  data_class: 'REAL' | 'SOURCE_DERIVED' | 'DERIVED' | 'SYNTHETIC_DEMO' | 'UNKNOWN' | 'NOT_CONNECTED' | string
}

export interface GraphEdge {
  source: string
  target: string
  relationship: string
  display_relationship: string
  relationship_source: GraphNode['data_class']
}

export interface GraphView {
  nodes: GraphNode[]
  edges: GraphEdge[]
  relationship_note: string
}

// A fixed left-to-right reading order for the node types this feature
// actually produces (see graph_view.py) — anything unrecognised falls in
// after these, keeping the layout stable across different questions rather
// than reshuffling column order per response.
const TYPE_ORDER = ['Country', 'MachineType', 'City', 'DealerBranch', 'Depot', 'Part', 'Supplier']

const COL_WIDTH = 250
const ROW_HEIGHT = 58
const NODE_W = 210
const NODE_H = 44
const PAD = 24
const MAX_ROWS = 7 // a column with more nodes is split into side-by-side sub-columns so the diagram stays compact
const LABEL_MAX = 30

function columnFor(type: string, columns: string[]): number {
  const known = TYPE_ORDER.indexOf(type)
  if (known >= 0) return TYPE_ORDER.filter((t) => columns.includes(t)).indexOf(type)
  return columns.filter((c) => !TYPE_ORDER.includes(c)).indexOf(type) + TYPE_ORDER.filter((t) => columns.includes(t)).length
}

/** "PT-037 Hitachi Genuine Hydraulic Oil" -> "PT-037 Hydraulic Oil": every catalogue part is a Hitachi genuine part, so the prefix only takes up room. */
function shortLabel(label: string): string {
  return label.replace(/^(PT-\d+\s+)?Hitachi\s+(Genuine\s+)?/i, '$1').trim()
}

function badgeClass(dataClass: string): string {
  if (dataClass === 'SYNTHETIC_DEMO') return 'ng-node--synthetic'
  if (dataClass === 'DERIVED') return 'ng-node--derived'
  if (dataClass === 'UNKNOWN' || dataClass === 'NOT_CONNECTED') return 'ng-node--unknown'
  return 'ng-node--real'
}

function edgeClass(relSource: string): string {
  if (relSource === 'SYNTHETIC_DEMO') return 'ng-edge--synthetic'
  if (relSource === 'DERIVED') return 'ng-edge--derived'
  return 'ng-edge--real'
}

/**
 * Small dependency-free node/edge diagram for Parts Intelligence network
 * answers. Layout is a plain left-to-right column arrangement by node
 * type — no force simulation, no graph library — which is enough for the
 * handful of nodes graph_view.py ever returns (it caps every list well
 * below what would make this unreadable).
 */
export default function NetworkGraph({ graph }: { graph: GraphView }) {
  const { nodes, edges, relationship_note } = graph
  if (nodes.length === 0) return null

  const columnTypes = [...new Set(nodes.map((n) => n.type))]
  const byColumn: Record<number, GraphNode[]> = {}
  for (const n of nodes) {
    const col = columnFor(n.type, columnTypes)
    byColumn[col] = byColumn[col] || []
    byColumn[col].push(n)
  }
  // Each type column may need several sub-columns; give every node a slot.
  const cols = Object.keys(byColumn).map(Number).sort((x, y) => x - y)
  const pos: Record<string, { x: number; y: number }> = {}
  let slot = 0
  let maxRows = 1
  for (const col of cols) {
    const colNodes = byColumn[col] ?? []
    const subCols = Math.ceil(colNodes.length / MAX_ROWS)
    const rowsPer = Math.ceil(colNodes.length / subCols)
    maxRows = Math.max(maxRows, rowsPer)
    colNodes.forEach((n, i) => {
      pos[n.id] = { x: PAD + (slot + Math.floor(i / rowsPer)) * COL_WIDTH + NODE_W / 2, y: i % rowsPer }
    })
    slot += subCols
  }
  const width = slot * COL_WIDTH + PAD * 2 - (COL_WIDTH - NODE_W)
  const height = maxRows * ROW_HEIGHT + PAD * 2
  for (const col of cols) {
    const colNodes = byColumn[col] ?? []
    const subCols = Math.ceil(colNodes.length / MAX_ROWS)
    const rowsPer = Math.ceil(colNodes.length / subCols)
    colNodes.forEach((n, i) => {
      const inThis = Math.min(rowsPer, colNodes.length - Math.floor(i / rowsPer) * rowsPer)
      const offsetY = (maxRows - inThis) / 2
      const q = pos[n.id]
      if (q) q.y = PAD + (offsetY + (i % rowsPer)) * ROW_HEIGHT + NODE_H / 2
    })
  }

  // One label per (source, relationship) group when a hub fans out to many nodes - a label on every line overlaps itself.
  const groupSize: Record<string, number> = {}
  for (const e of edges) groupSize[`${e.source}|${e.display_relationship}`] = (groupSize[`${e.source}|${e.display_relationship}`] || 0) + 1
  const labelled = new Set<string>()

  return (
    <div className="ng">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ maxWidth: width, height: 'auto' }} role="img" aria-label="Relationship graph">
        {edges.map((e, i) => {
          const a = pos[e.source]
          const b = pos[e.target]
          if (!a || !b) return null
          const key = `${e.source}|${e.display_relationship}`
          const many = (groupSize[key] ?? 0) > 3
          let label: string | null = e.display_relationship
          let lx = (a.x + b.x) / 2
          let ly = (a.y + b.y) / 2
          if (many) {
            if (labelled.has(key)) label = null
            else {
              labelled.add(key)
              label = `${e.display_relationship} ×${groupSize[key]}`
              lx = a.x + NODE_W / 2 + 46
              ly = a.y
            }
          }
          return (
            <g key={`${e.source}-${e.target}-${i}`} className={`ng-edge ${edgeClass(e.relationship_source)}`}>
              <line x1={a.x + NODE_W / 2} y1={a.y} x2={b.x - NODE_W / 2} y2={b.y} />
              {label && (
                <>
                  <rect x={lx - label.length * 3.2 - 4} y={ly - 9} width={label.length * 6.4 + 8} height={18} rx={4} />
                  <text x={lx} y={ly + 4} textAnchor="middle">{label}</text>
                </>
              )}
            </g>
          )
        })}
        {nodes.map((n) => {
          const p = pos[n.id]
          if (!p) return null
          return (
            <g key={n.id} className={`ng-node ${badgeClass(n.data_class)}`} transform={`translate(${p.x - NODE_W / 2}, ${p.y - NODE_H / 2})`}>
              <rect width={NODE_W} height={NODE_H} rx={10} />
              <text x={NODE_W / 2} y={17} textAnchor="middle" className="ng-node__type">{n.type}</text>
              <text x={NODE_W / 2} y={33} textAnchor="middle" className="ng-node__label">
                {shortLabel(n.label).length > LABEL_MAX ? `${shortLabel(n.label).slice(0, LABEL_MAX - 1)}…` : shortLabel(n.label)}
              </text>
              <title>{n.label}</title>
            </g>
          )
        })}
      </svg>
      <div className="ng-legend">
        <span className="ng-legend__item"><i className="ng-swatch ng-swatch--real" /> Real / source-derived</span>
        <span className="ng-legend__item"><i className="ng-swatch ng-swatch--derived" /> Derived (e.g. same city)</span>
        <span className="ng-legend__item"><i className="ng-swatch ng-swatch--synthetic" /> Synthetic demo</span>
      </div>
      <p className="ng-note">{relationship_note}</p>
    </div>
  )
}

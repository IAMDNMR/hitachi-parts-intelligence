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

const COL_WIDTH = 190
const ROW_HEIGHT = 64
const NODE_W = 156
const NODE_H = 44
const PAD = 24

function columnFor(type: string, columns: string[]): number {
  const known = TYPE_ORDER.indexOf(type)
  if (known >= 0) return TYPE_ORDER.filter((t) => columns.includes(t)).indexOf(type)
  return columns.filter((c) => !TYPE_ORDER.includes(c)).indexOf(type) + TYPE_ORDER.filter((t) => columns.includes(t)).length
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
  const colCount = Object.keys(byColumn).length
  const maxRows = Math.max(...Object.values(byColumn).map((n) => n.length))
  const width = colCount * COL_WIDTH + PAD * 2
  const height = maxRows * ROW_HEIGHT + PAD * 2

  const pos: Record<string, { x: number; y: number }> = {}
  Object.entries(byColumn).forEach(([colStr, colNodes]) => {
    const col = Number(colStr)
    const rowsInCol = colNodes.length
    const offsetY = (maxRows - rowsInCol) / 2
    colNodes.forEach((n, row) => {
      pos[n.id] = {
        x: PAD + col * COL_WIDTH + NODE_W / 2,
        y: PAD + (offsetY + row) * ROW_HEIGHT + NODE_H / 2,
      }
    })
  })

  return (
    <div className="ng">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label="Relationship graph">
        {edges.map((e, i) => {
          const a = pos[e.source]
          const b = pos[e.target]
          if (!a || !b) return null
          const midX = (a.x + b.x) / 2
          const midY = (a.y + b.y) / 2
          return (
            <g key={`${e.source}-${e.target}-${i}`} className={`ng-edge ${edgeClass(e.relationship_source)}`}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
              <rect x={midX - e.display_relationship.length * 3.2 - 4} y={midY - 9} width={e.display_relationship.length * 6.4 + 8} height={18} rx={4} />
              <text x={midX} y={midY + 4} textAnchor="middle">{e.display_relationship}</text>
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
                {n.label.length > 22 ? `${n.label.slice(0, 21)}…` : n.label}
              </text>
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

import type { Confidence, Edge, GroundNode } from '../types/ground'

/**
 * THE FINDINGS.
 *
 * Everything in the model that is not confirmed by the material we were
 * given, collected into one list.
 *
 * The map already carries this — every node and every edge declares where it
 * came from — but it carries it one node at a time, as a mark on a box that
 * has to be hunted for. Read that way it is a caveat. Read all at once it is
 * something else: a list of the questions the client's own architecture
 * documentation does not answer, which is the most useful thing this project
 * can hand them and the only part of it they could not have produced
 * themselves.
 *
 * Nothing here is authored. Every finding is derived from the provenance
 * already written against the model, so the report cannot drift from the map
 * — change a node's confidence and this changes with it.
 */

export type OpenConfidence = Exclude<Confidence, 'confirmed'>

export interface Finding {
  /** Stable key: the node id, or the edge it describes. */
  key: string
  confidence: OpenConfidence
  /** What the finding is about — a node's name, or "A → B". */
  title: string
  /** What the model claims. */
  claim: string
  /** Why it is claimed, where the model says. */
  basis?: string
  /** The supplied artefact behind it, where there is one. */
  sourceReference?: string
  /** Where to look on the map. Edges point at the node they leave. */
  nodeId: string
  /** Node findings and relationship findings read differently. */
  about: 'node' | 'relationship'
}

/**
 * Severity order, and it is not alphabetical.
 *
 * What the supplied material fails to answer comes before what we reasoned in
 * its absence. A box the client's own diagram draws and does not route is a
 * harder question for them than a step we assumed because every parts
 * operation has one.
 */
export const FINDING_ORDER: readonly OpenConfidence[] = [
  'not-supplied',
  'source-unsure',
  'inferred',
  'assumed',
  'demo',
]

/** What each level means, written for the client rather than for the code. */
export const FINDING_MEANING: Readonly<Record<OpenConfidence, string>> = {
  'not-supplied': 'Present in the supplied diagram with nothing behind it. We could not determine what it does.',
  'source-unsure':
    'The supplied diagram marks this uncertain itself — a question mark, a note, an unlabelled segment. We preserved the uncertainty rather than resolving it.',
  inferred:
    'Not drawn in any supplied material, but it follows from something that is. The reasoning is given so it can be checked.',
  assumed:
    'Ordinary practice for an operation of this kind, with nothing supplied behind it. Included so the map has no dead ends, and flagged so it is not mistaken for the architecture.',
  demo: 'Illustrative, so the experience can be understood.',
}

export function collectFindings(
  nodes: readonly GroundNode[],
  edges: readonly Edge[],
): Finding[] {
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const name = (id: string) => byId.get(id)?.label ?? id
  const out: Finding[] = []

  for (const node of nodes) {
    const { confidence, source, sourceReference } = node.provenance
    if (confidence === 'confirmed') continue
    out.push({
      key: node.id,
      confidence,
      title: node.label,
      claim: node.summary,
      basis: source,
      sourceReference,
      nodeId: node.id,
      about: 'node',
    })
  }

  for (const edge of edges) {
    if (edge.confidence === 'confirmed') continue
    out.push({
      key: `${edge.from}->${edge.to}`,
      confidence: edge.confidence,
      title: `${name(edge.from)} → ${name(edge.to)}`,
      /* An edge's own justification is the flow that travels along it. Where
         it carries none, say so plainly rather than inventing a sentence —
         an unexplained relationship IS the finding. */
      claim: edge.label
        ? `Carries "${edge.label}".`
        : 'A relationship with no flow named against it.',
      basis: EDGE_KIND_BASIS[edge.kind],
      nodeId: edge.from,
      about: 'relationship',
    })
  }

  return out.sort(
    (a, b) =>
      FINDING_ORDER.indexOf(a.confidence) - FINDING_ORDER.indexOf(b.confidence) ||
      a.title.localeCompare(b.title),
  )
}

/** What kind of relationship the edge is, in the report's words. */
const EDGE_KIND_BASIS: Readonly<Record<Edge['kind'], string>> = {
  flow: 'One step of a business process leading to the next.',
  system: 'A business step reaching the system that records it.',
  integration: 'A system reaching outside the estate.',
  data: 'A system writing a data entity, or an entity joining the canonical model.',
}

/** How much of the model rests on supplied material, for the summary. */
export function countConfidence(
  nodes: readonly GroundNode[],
  edges: readonly Edge[],
): { confirmed: number; open: number; total: number } {
  const confirmedNodes = nodes.filter((n) => n.provenance.confidence === 'confirmed').length
  const confirmedEdges = edges.filter((e) => e.confidence === 'confirmed').length
  const total = nodes.length + edges.length
  const confirmed = confirmedNodes + confirmedEdges
  return { confirmed, open: total - confirmed, total }
}

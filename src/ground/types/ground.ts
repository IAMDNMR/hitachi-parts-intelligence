/**
 * The Ground — type contract.
 *
 * A LAYERED DIRECTED GRAPH, NOT A TREE
 * ------------------------------------
 * Nodes declare which architectural layer they sit in (`column`); edges are
 * declared separately, because the real ecosystem is a mesh. Service reaches
 * into Parts, monitoring data raises a parts requirement, the dealer is
 * arrived at from two directions, and one entity is written by one system
 * while being referenced by another. A parent/child tree cannot express any
 * of that, so nothing here uses one.
 *
 * PROVENANCE IS PART OF THE SCHEMA
 * --------------------------------
 * The Ground describes a real enterprise. The difference between "this is
 * how it works", "this is illustrative", and "the source diagram itself is
 * unsure" has to survive to the screen, so it is typed rather than written
 * into prose.
 */

export type Confidence =
  /** Stated in supplied source material, or in the project's own data. */
  | 'confirmed'
  /**
   * The supplied source itself marks this uncertain — a red "?", a "not
   * routed" note, a box cropped out of the image. This is a finding about the
   * client's own documentation and is worth surfacing as one.
   */
  | 'source-unsure'
  /**
   * Not drawn anywhere, but it follows from something that is. `source` on
   * the provenance carries the reasoning, so the reader can check it.
   */
  | 'inferred'
  /**
   * Ordinary practice, with nothing behind it. Present so the map is not full
   * of dead ends, and flagged so nobody mistakes it for the real architecture.
   */
  | 'assumed'
  /** Illustrative, so the experience can be understood. */
  | 'demo'
  /** Known to be missing. Renders as "Not supplied". */
  | 'not-supplied'

export interface Provenance {
  confidence: Confidence
  /** Human-readable origin, e.g. 'project data: partsCatalogue.js'. */
  source?: string
  /** A specific artefact, e.g. 'reference diagram: …'. */
  sourceReference?: string
}

/**
 * What kind of thing a node is. Drives its shape and weight on the canvas,
 * so the layer a node belongs to is legible before anything is clicked.
 */
export type NodeType =
  | 'milestone' // Machine Sold, Uptime — the two ends of the story
  | 'party' // Customer
  | 'stage' // Sales & Handover, After-Sales
  | 'pillar' // Parts, Service, Machine Data, Warranty, Network
  | 'process' // an operational step
  | 'system' // ERP / WMS / TMS
  | 'hub' // an EDI integration hub
  | 'third-party' // external / satellite system
  | 'entity' // a data entity
  | 'canonical' // a canonical data model group

/** One row of the system-of-record fact table on an entity. */
export interface RecordFact {
  label: string
  /** Undefined means the source table left this cell blank. */
  value?: string
}

export interface GroundNode {
  id: string
  type: NodeType
  /**
   * The architectural layer this node belongs to — origin, pillar, process,
   * system, hub, third party, entity, canonical, outcome.
   *
   * NOT READ BY THE LAYOUT. It used to say "drives horizontal placement",
   * and that stopped being true when layout.ts began computing rank from the
   * relationships instead: the authored columns did not describe a hierarchy
   * — the whole sales spine sat in column 0 and all twenty-seven business
   * processes sat in column 4, which is a row no screen can hold.
   *
   * It is kept rather than deleted because it is the one thing in the model
   * that states the intended ARCHITECTURAL layering, as opposed to the flow
   * order the ranking derives. A layout that lays a process chain out
   * left-to-right instead of down the page — which is what the current
   * one-node-wide ribbon needs — would be built on this.
   */
  column: number
  label: string
  summary: string
  /** What it does, or its role in the architecture. */
  role?: string
  /** Short supporting lines — flows, caveats, source annotations. */
  detail?: string[]
  /** System-of-record style facts, for data entities. */
  facts?: RecordFact[]
  provenance: Provenance
}

/** A directed relationship. `label` is the flow that travels along it. */
export interface Edge {
  from: string
  to: string
  label?: string
  /**
   * flow        — business process to business process
   * system      — a process reaching its system of record
   * integration — system to hub to third party
   * data        — a system writing an entity, or an entity joining the model
   */
  kind: 'flow' | 'system' | 'integration' | 'data'
  confidence: Confidence
}

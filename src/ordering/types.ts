/**
 * Mirrors backend/parts_ordering/app/schemas.py exactly. Two sides of one
 * API contract, kept in the same shape deliberately — a field renamed on one
 * side and not the other should fail to compile here, not fail silently at
 * runtime in front of a client.
 */

export type Stage =
  | 'requirement_raised'
  | 'identified'
  | 'availability_checked'
  | 'ordered'
  | 'inventory_allocated'
  | 'shipped'
  | 'received'

/** Same order the backend enforces — see STAGE_SEQUENCE in app/models.py. */
export const STAGE_SEQUENCE: readonly Stage[] = [
  'requirement_raised',
  'identified',
  'availability_checked',
  'ordered',
  'inventory_allocated',
  'shipped',
  'received',
]

/** The graph's own words for each stage — src/ground/data/graph.ts node labels. */
export const STAGE_LABELS: Readonly<Record<Stage, string>> = {
  requirement_raised: 'Parts Requirement',
  identified: 'Part Identification',
  availability_checked: 'Parts Availability',
  ordered: 'Parts Ordering',
  inventory_allocated: 'Inventory',
  shipped: 'Shipment',
  received: 'Goods Receipt',
}

export interface Part {
  id: string
  part_number: string
  name: string
  category: string
  description: string
}

/**
 * A part as the catalogue table lists it — mirrors PartRow in schemas.py.
 *
 * What it fits and whether it can be had are the two questions a catalogue
 * row exists to answer, so they travel with the row rather than costing a
 * request each.
 */
export interface PartRow extends Part {
  lead_time_days: number
  machines: string[]
  stock: Stock | null
}

export interface Fitment {
  machine_model: string
  assembly: string
}

export interface PartDocument {
  title: string
  doc_type: string
  reference: string
}

/** What a part record answers, in after-sales terms. */
export interface PartDetail extends Part {
  lead_time_days: number
  stock: Stock | null
  fitments: Fitment[]
  documents: PartDocument[]
  supersedes: Part | null
  /** What replaced this one. Null unless the record being read is itself a
   *  superseded number — see get_part in routers/parts.py. */
  superseded_by: Part | null
}

/** "Where used", the way after-sales means it: machines that needed it. */
export interface PartUsage {
  requirement_id: number
  machine_serial: string
  quantity: number
  stage: Stage
  created_at: string
}

export interface Stock {
  warehouse: string
  qty_on_hand: number
  reorder_point: number
}

export interface StatusEvent {
  stage: Stage
  at: string
  note?: string | null
}

export interface Requirement {
  id: number
  machine_serial: string
  part: Part
  quantity: number
  reason: string
  stage: Stage
  created_at: string
  available_at_check?: boolean | null
  supplier?: string | null
  carrier?: string | null
}

export interface RequirementDetail extends Requirement {
  events: StatusEvent[]
  next_stage: Stage | null
}

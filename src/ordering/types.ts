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
  /** The machine as a record, so "machines that needed it" links back to
   *  Machine 360 rather than printing a serial as text. */
  machine_id: string
  machine_serial: string
  machine_model: string
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
  machine_id: string
  /** Read off the machine, not stored beside it — see the property on the
   *  Requirement model. */
  machine_serial: string
  machine_model: string
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


/* ------------------------------------------------------------- machines */

export type MachineStatus = 'working' | 'down' | 'in_workshop'

/** Context, not a customer record — three fields on purpose. */
export interface Party {
  id: string
  name: string
  region: string
}

/** A machine in the field. The central operational context. */
export interface Machine {
  id: string
  serial_number: string
  /** Matches PartFitment.machine_model. The authority for fitment. */
  model: string
  status: MachineStatus
  commissioned_at: string
  warranty_end: string | null
  customer: Party
  dealer: Party
  /** Requirements not yet received — what the machine is waiting on. */
  open_requirements: number
  /** Derived from warranty_end against today, never stored. */
  in_warranty: boolean
}

export interface MachineDetail extends Machine {
  fitting_parts: number
}

/** A part the catalogue lists against this machine's model. */
export interface MachinePart extends Part {
  lead_time_days: number
  /** Where it sits on the machine. */
  assembly: string
  stock: Stock | null
}

/** One line of a machine's parts history, derived from its requirements. */
export interface MachineRequirement {
  id: number
  part: Part
  quantity: number
  stage: Stage
  reason: string
  created_at: string
}

export const MACHINE_STATUS_LABELS: Readonly<Record<MachineStatus, string>> = {
  working: 'Working',
  down: 'Down',
  in_workshop: 'In workshop',
}

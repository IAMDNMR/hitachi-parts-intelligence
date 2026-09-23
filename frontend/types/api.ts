/**
 * Frontend API type layer.
 *
 * These types describe what the browser sends to and receives from the
 * backend. They intentionally mirror the JSON shapes the frontend code
 * already reads/writes (including any pre-existing naming inconsistencies
 * between components) rather than the FastAPI backend's own internal
 * (snake_case) response shape — this file types the frontend/backend
 * *contract as currently implemented*, it does not change it. No business
 * logic belongs here; this is data shape only.
 */

/** A part as shown in the Parts Store catalogue / Quick View / cart. */
export interface Part {
  id: string
  partNumber?: string
  name?: string
  category?: string
  price?: number
  currency?: string
  image?: string
  imageSource?: string
  machine?: string
  [key: string]: unknown
}

/** BR-01: availability must always resolve to one of these four states — never a bare "0" or a silent failure. */
export type AvailabilityStatus = 'AVAILABLE' | 'PARTIALLY_AVAILABLE' | 'UNAVAILABLE' | 'UNKNOWN'

/** One inventory source's result within an availability check response. */
/** One source row of `availabilityResults` — the backend's
 *  SourceInventoryItem.model_dump() (snake_case). */
export interface AvailabilitySource {
  source_id: string
  source_name: string
  source_type: string
  location_id: string
  available_qty: number
  inventory_timestamp: string
  status: AvailabilityStatus
  is_stale: boolean
  /** 'SYNTHETIC_DEMO' when the stock comes from the labelled demo dataset. */
  provenance: string
}

/** The response body of POST /api/v1/fulfilment-requests/{id}/availability. */
export interface AvailabilityResponse {
  availabilityResults?: AvailabilitySource[]
}

/** The payload sent to create a Fulfilment Request. */
export interface FulfilmentRequestPayload {
  partNumber: string
  quantity: number
  destinationBranchId: string
  machineContext?: string | null
}

/** A created Fulfilment Request, as returned by the backend. */
export interface FulfilmentRequest {
  id: string
  status?: string
  part_number?: string
  quantity?: number
  selected_option_id?: string | null
  [key: string]: unknown
}

/** Phase 5: Candidate Fulfilment Option derived from an availability result. */
export interface FulfilmentOption {
  id: string
  fulfilment_request_id: string
  source_id: string
  source_type: string
  destination_branch_id: string
  transport_mode: string | null
  carrier_code: string | null
  service_level: string | null
  transit_days: number | null
  eta: string | null
  transport_cost: number | null
  currency: string | null
  confidence: 'CONFIRMED' | 'UNCONFIRMED' | 'PARTIAL'
  /** NOT_CONNECTED when no confirmed carrier/tariff exists — mode, carrier,
   *  transit, ETA and cost are then null and must not be shown as facts. */
  transport_data_status: 'CONFIRMED' | 'NOT_CONNECTED'
  /** true when the option's stock source is SYNTHETIC_DEMO data. */
  synthetic?: boolean
  is_selected: boolean
  is_split?: boolean
  details?: Record<string, unknown>
}

export interface FulfilmentOptionsResponse {
  fulfilment_request_id: string
  options: FulfilmentOption[]
  total_options: number
}

export interface SelectOptionResponse {
  fulfilment_request_id: string
  status: string
  selected_option_id: string
}

/** A line item in the Parts Store cart / quote request (mirrors backend/app/api/v1/quote_request.py's `item.*` reads). */
export interface CartItem {
  id: string
  name: string
  qty: number
  machine: string | null
  image: string | null
  partNumber: string | null
}

/** The payload sent to POST /api/v1/quote-request. */
export interface QuoteRequestDetails {
  name: string
  email: string
  phone: string
  note?: string
}

export type QuoteRequest = QuoteRequestDetails & {
  items: CartItem[]
}

/** The response body of POST /api/v1/quote-request. */
export interface QuoteRequestResponse {
  ok: boolean
  inquiryId?: string
  requestedPartCount?: number
  projectionStatus?: 'SUCCESS' | 'FAILED' | 'DEGRADED'
  error?: { message?: string }
}

/** A shallow API error envelope, as returned by the FastAPI backend. */
export interface ApiErrorBody {
  error?: { message?: string }
}

/** Response body of POST/GET /api/v1/fulfilment-requests/{id}/allocation (Phase 6). */
export interface AllocationResult {
  allocation_id?: string
  id?: string
  fulfilment_request_id?: string
  part_number?: string
  partNumber?: string
  source_id?: string
  sourceId?: string
  quantity: number
  status: 'PENDING' | 'RESERVED' | 'CONFIRMED' | 'CONSUMED' | 'RELEASED' | 'EXPIRED' | 'FAILED'
  expiry_at?: string | null
}

/** Response body of POST/GET .../order and GET /api/v1/orders/{id} (Phase 6). */
export interface OrderResult {
  id: string
  fulfilmentRequestId: string
  partNumber: string
  quantity: number
  sourceId: string
  destinationBranchId: string
  unitPrice: number | null
  currency: string | null
  pricingStatus: 'NOT_AVAILABLE' | 'CONFIRMED'
  status: 'CREATED' | 'ACCEPTED' | 'CANCELLED'
  provenance: string
  integration_status: 'NOT_CONNECTED' | 'CONNECTED'
  integration_label: string
}

/** Real European Dealer Branch from /api/v1/dealers */
export interface DealerOption {
  dealer_id: string
  dealer_name: string
  address?: string | null
  city?: string | null
  country: string
  latitude?: number | null
  longitude?: number | null
  phone?: string | null
  email?: string | null
  website?: string | null
  distance_km?: number | null
}

/** Transport option DTO from /api/v1/transport/options */
export interface TransportOptionDTO {
  transport_option_id: string
  mode: 'ROAD' | 'RAIL' | 'AIR' | 'INTERNAL_TRANSFER'
  service_level: 'STANDARD' | 'EXPRESS'
  display_name: string
  carrier_label: string
  transit_days: number
  estimated_delivery_date: string
  dispatch_cutoff_time: string
  currency: string
  base_cost: number
  distance_cost: number
  service_level_cost: number
  total_cost: number
  data_class: string
  provenance_note: string
  highlight_tag?: 'LOWEST COST' | 'FASTEST' | string | null
  is_selected?: boolean
}

export interface LocationInfo {
  id: string
  name: string
  city?: string | null
  country?: string | null
  latitude?: number | null
  longitude?: number | null
}

export interface TransportComparisonResponse {
  origin: LocationInfo
  destination: LocationInfo
  straight_line_distance_km: number
  estimated_road_distance_km: number
  distance_band: string
  distance_band_name: string
  options: TransportOptionDTO[]
  provenance: {
    distance: string
    rates: string
    carrier_connectivity: string
  }
}

export interface ShipmentEvent {
  id: string
  event_type: string
  description: string
  location?: string | null
  timestamp: string
}

export interface ShipmentData {
  shipment_id: string
  order_id: string
  status: string
  carrier: string
  tracking_number?: string | null
  origin?: string | null
  destination?: string | null
  destination_branch_id?: string | null
  eta?: string | null
  shipped_at?: string | null
  delivered_at?: string | null
  synthetic: boolean
  integration_status?: string
  integration_label: string
  events: ShipmentEvent[]
}

export interface ServiceJobEvent {
  id: string
  event_type: string
  description: string
  technician_role?: string | null
  timestamp: string
}

export interface ServiceJobData {
  service_job_id: string
  order_id: string
  shipment_id?: string | null
  dealer_id: string
  dealer_name?: string | null
  dealer_city?: string | null
  dealer_country?: string | null
  status: string
  service_type: string
  work_order_number?: string | null
  notes?: string | null
  received_at?: string | null
  started_at?: string | null
  installed_at?: string | null
  completed_at?: string | null
  synthetic: boolean
  events: ServiceJobEvent[]
}

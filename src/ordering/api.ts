import type {
  Part,
  PartDetail,
  PartRow,
  PartUsage,
  Requirement,
  RequirementDetail,
  Stock,
} from './types'

/**
 * Points at the FastAPI service in backend/parts_ordering. Overridable via
 * VITE_ORDERING_API_URL (an .env at the project root) for anything other
 * than "the backend is running on localhost:8000", which is what
 * `uvicorn app.main:app --port 8000` gives you with no flags.
 */
const BASE = (import.meta.env.VITE_ORDERING_API_URL as string | undefined) ?? 'http://localhost:8000'

/**
 * Every error the backend can return is a JSON body shaped
 * `{ detail: string }` — FastAPI's own convention, for both validation
 * errors and the ones services/workflow.py raises. Surfacing `detail`
 * directly means "Requirement 3 is at 'ordered'; this action needs
 * 'inventory_allocated'." reaches the screen exactly as the state machine
 * wrote it, not as a generic "Something went wrong."
 */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    // The service is not reachable at all — down, wrong port, CORS refused
    // before a response existed. Distinguished from a 4xx/5xx on purpose:
    // the fix for "it's not running" is different from the fix for "it said
    // no", and the message should say which one this is.
    throw new ApiError(0, `Cannot reach the parts-ordering service at ${BASE}. Is it running?`)
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) {
        // Pydantic validation errors: a list of {loc, msg}.
        detail = body.detail.map((e: { msg: string }) => e.msg).join('; ')
      }
    } catch {
      /* body wasn't JSON; the status text is what we have */
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  listParts: (search?: string) =>
    request<PartRow[]>(`/api/parts${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  getPart: (partId: string) => request<PartDetail>(`/api/parts/${encodeURIComponent(partId)}`),
  getPartUsage: (partId: string) =>
    request<PartUsage[]>(`/api/parts/${encodeURIComponent(partId)}/usage`),
  getStock: (partId: string) => request<Stock>(`/api/parts/${encodeURIComponent(partId)}/stock`),

  listRequirements: (stage?: string) =>
    request<Requirement[]>(`/api/requirements${stage ? `?stage=${stage}` : ''}`),
  getRequirement: (id: number) => request<RequirementDetail>(`/api/requirements/${id}`),
  createRequirement: (body: {
    machine_serial: string
    part_id: string
    quantity: number
    reason: string
  }) => request<RequirementDetail>('/api/requirements', { method: 'POST', body: JSON.stringify(body) }),

  updateRequirement: (
    id: number,
    body: { machine_serial?: string; quantity?: number; reason?: string },
  ) => request<RequirementDetail>(`/api/requirements/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  }),
  cancelRequirement: (id: number) =>
    request<void>(`/api/requirements/${id}`, { method: 'DELETE' }),
  adjustStock: (partId: string, delta: number) =>
    request<Stock>(`/api/parts/${encodeURIComponent(partId)}/stock/adjust`, {
      method: 'POST',
      body: JSON.stringify({ delta }),
    }),

  checkAvailability: (id: number) =>
    request<RequirementDetail>(`/api/requirements/${id}/check-availability`, { method: 'POST' }),
  order: (id: number, supplier?: string) =>
    request<RequirementDetail>(`/api/requirements/${id}/order`, {
      method: 'POST',
      body: JSON.stringify({ supplier: supplier || undefined }),
    }),
  allocate: (id: number) =>
    request<RequirementDetail>(`/api/requirements/${id}/allocate`, { method: 'POST' }),
  ship: (id: number, carrier?: string) =>
    request<RequirementDetail>(`/api/requirements/${id}/ship`, {
      method: 'POST',
      body: JSON.stringify({ carrier: carrier || undefined }),
    }),
  receive: (id: number) =>
    request<RequirementDetail>(`/api/requirements/${id}/receive`, { method: 'POST' }),
}

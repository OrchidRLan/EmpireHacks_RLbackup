/**
 * Typed API client for the Rento FastAPI backend.
 * All paths are relative to /api/v1 and proxied through Vite in dev
 * or resolved via VITE_API_URL in production.
 */

const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api/v1'
const TOKEN_KEY = 'rento_token'

/* ─────────────────────────────────────────
   Token helpers
───────────────────────────────────────── */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/* ─────────────────────────────────────────
   Core fetch wrapper
───────────────────────────────────────── */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    let message = `API error ${res.status}`
    try {
      const body = await res.json()
      message = body?.detail ?? body?.message ?? message
    } catch {
      // ignore parse errors
    }
    throw new Error(message)
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as unknown as T
  }

  return res.json() as Promise<T>
}

/* ─────────────────────────────────────────
   Backend response types
───────────────────────────────────────── */

export interface UserOut {
  id: string
  name: string
  email: string
  onboardingComplete: boolean
}

export interface AuthResponse {
  token: string
  user: UserOut
}

export interface ListingOut {
  id: string
  title: string
  address: string
  neighborhood: string | null
  price: number
  bedrooms: string
  pets: boolean
  parking: string[]
  laundry: string[]
  images: string[]
  imageLabels: string[]
  lat: number | null
  lng: number | null
  availableFrom: string | null
  leaseLength: number | null
  matchScore: number | null
  matchReasoning: string | null
  negotiationStatus: string | null
  commuteMinutes: number | null
  matchId: string | null
  matchType: string
  status: string
  hostEmail: string | null
  hostPhone: string | null
}

export interface ListingsPage {
  items: ListingOut[]
  total: number
  page: number
  pageSize: number
}

export interface ReactResponse {
  matchId: string
  action: string
}

// Backend field names for preferences (camelCase matching backend Pydantic schemas)
export interface HousingPatch {
  bedroomType?: string       // "studio"|"1b"|"2b"|"3b"|"4plus"
  selectedAreas?: string[]   // neighborhood IDs
  minBudget?: number
  maxBudget?: number
  moveInDate?: string
  leaseLengthMonths?: number
  laundry?: string[]         // ["in_unit","on_site"]
  parking?: string[]         // ["garage","street"]
  pets?: boolean
  workLatitude?: number
  workLongitude?: number
  commuteMethod?: string     // "drive"|"transit"|"bike"
  maxCommuteMinutes?: number
}

export interface NegotiationPatch {
  enableAutomation?: boolean
  negotiableItems?: string[]
  goals?: string[]
  maxRent?: number
  maxDeposit?: number
  latestMoveInDate?: string
  minLeaseMonths?: number
  maxLeaseMonths?: number
  negotiationStyle?: string
}

export interface NotificationsPatch {
  enableNotifications?: boolean
  autoScheduling?: boolean
  notificationTypes?: string[]
  frequency?: string
}

export interface PreferencesOut {
  housing: HousingPatch
  negotiation: NegotiationPatch
  notifications: NotificationsPatch
}

export interface NegotiationOut {
  id: string
  listingId: string
  status: string
  createdAt: string
}

export interface MessageOut {
  id: string
  role: 'agent' | 'host'
  text: string
  timestamp: string
}

export interface AgentStatusOut {
  isRunning: boolean
  currentAction: string
  phase: string
  matchesFound: number
  negotiationsActive: number
  toursScheduled: number
}

export interface AgentLogOut {
  id: string
  timestamp: string
  level: string
  message: string
  phase: string
}

export interface AgentLogsPage {
  items: AgentLogOut[]
  total: number
  page: number
  pageSize: number
}

export interface NotificationOut {
  id: string
  type: string
  title: string
  message: string
  timestamp: string
  read: boolean
  listingId?: string
}

export interface NotificationsPage {
  items: NotificationOut[]
  total: number
  page: number
  pageSize: number
}

/* ─────────────────────────────────────────
   Auth
───────────────────────────────────────── */
export const authApi = {
  register(body: { email: string; password: string; name: string }): Promise<AuthResponse> {
    return apiFetch('/auth/register', { method: 'POST', body: JSON.stringify(body) })
  },
  login(body: { email: string; password: string }): Promise<AuthResponse> {
    return apiFetch('/auth/login', { method: 'POST', body: JSON.stringify(body) })
  },
  me(): Promise<UserOut> {
    return apiFetch('/auth/me')
  },
}

/* ─────────────────────────────────────────
   Listings
───────────────────────────────────────── */
export interface ListingsQuery {
  page?: number
  pageSize?: number
  negotiationStatus?: string
  matchType?: string
  minPrice?: number
  maxPrice?: number
  minScore?: number
  sortBy?: string
  sortOrder?: string
}

export const listingsApi = {
  list(query: ListingsQuery = {}): Promise<ListingsPage> {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null) params.set(k, String(v))
    }
    const qs = params.toString()
    return apiFetch(`/listings${qs ? `?${qs}` : ''}`)
  },
  get(id: string): Promise<ListingOut> {
    return apiFetch(`/listings/${id}`)
  },
  react(id: string, action: 'like' | 'dislike'): Promise<ReactResponse> {
    return apiFetch(`/listings/${id}/react`, { method: 'POST', body: JSON.stringify({ action }) })
  },
}

/* ─────────────────────────────────────────
   Preferences
───────────────────────────────────────── */
export const preferencesApi = {
  get(): Promise<PreferencesOut> {
    return apiFetch('/preferences')
  },
  updateHousing(body: HousingPatch): Promise<HousingPatch> {
    return apiFetch('/preferences/housing', { method: 'PUT', body: JSON.stringify(body) })
  },
  updateNegotiation(body: NegotiationPatch): Promise<NegotiationPatch> {
    return apiFetch('/preferences/negotiation', { method: 'PUT', body: JSON.stringify(body) })
  },
  updateNotifications(body: NotificationsPatch): Promise<NotificationsPatch> {
    return apiFetch('/preferences/notifications', { method: 'PUT', body: JSON.stringify(body) })
  },
}

export interface FilterResult { matched: number; message: string }
export interface ScoringResult { scored: number; message: string }

export const matchingApi = {
  runFilter(): Promise<FilterResult> {
    return apiFetch('/listings/run-filter', { method: 'POST' })
  },
  runScoring(): Promise<ScoringResult> {
    return apiFetch('/listings/run-scoring', { method: 'POST' })
  },
}

/* ─────────────────────────────────────────
   Negotiations
───────────────────────────────────────── */
export const negotiationsApi = {
  list(): Promise<NegotiationOut[]> {
    return apiFetch('/negotiations')
  },
  start(listingId: string): Promise<NegotiationOut> {
    return apiFetch('/negotiations', { method: 'POST', body: JSON.stringify({ listingId }) })
  },
  messages(listingId: string): Promise<MessageOut[]> {
    return apiFetch(`/negotiations/${listingId}/messages`)
  },
  sendMessage(listingId: string, text: string): Promise<MessageOut> {
    return apiFetch(`/negotiations/${listingId}/messages`, { method: 'POST', body: JSON.stringify({ text }) })
  },
  updateStatus(listingId: string, status: 'accept' | 'reject' | 'pause'): Promise<void> {
    return apiFetch(`/negotiations/${listingId}/status`, { method: 'PUT', body: JSON.stringify({ status }) })
  },
}

/* ─────────────────────────────────────────
   Agent
───────────────────────────────────────── */
export const agentApi = {
  status(): Promise<AgentStatusOut> {
    return apiFetch('/agent/status')
  },
  start(): Promise<void> {
    return apiFetch('/agent/start', { method: 'POST' })
  },
  stop(): Promise<void> {
    return apiFetch('/agent/stop', { method: 'POST' })
  },
  logs(page = 1, pageSize = 100): Promise<AgentLogsPage> {
    return apiFetch(`/agent/logs?page=${page}&pageSize=${pageSize}`)
  },
}

/* ─────────────────────────────────────────
   Notifications
───────────────────────────────────────── */
export const notificationsApi = {
  list(page = 1, pageSize = 50): Promise<NotificationsPage> {
    return apiFetch(`/notifications?page=${page}&pageSize=${pageSize}`)
  },
  readAll(): Promise<void> {
    return apiFetch('/notifications/read-all', { method: 'PUT' })
  },
  readOne(id: string): Promise<void> {
    return apiFetch(`/notifications/${id}/read`, { method: 'PUT' })
  },
}

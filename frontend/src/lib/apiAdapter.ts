/**
 * Adapters that convert backend API shapes to the frontend domain types.
 */

import type { ListingOut, AgentLogOut, NotificationOut as ApiNotificationOut } from './api'
import type { Listing, BedroomType, AgentLog, Notification, NotificationEvent } from '../types'

/* ─────────────────────────────────────────
   Bedroom mapping
───────────────────────────────────────── */
function adaptBedrooms(raw: string): BedroomType {
  const map: Record<string, BedroomType> = {
    studio: 'Studio',
    '1b': '1BR',
    '2b': '2BR',
    '3b': '3BR+',
    '4plus': '3BR+',
  }
  return map[raw.toLowerCase()] ?? '1BR'
}

/* ─────────────────────────────────────────
   Laundry mapping
───────────────────────────────────────── */
function adaptLaundry(raw: string[]): 'In-unit' | 'In-building' | 'None' {
  if (raw.includes('in_unit')) return 'In-unit'
  if (raw.includes('on_site')) return 'In-building'
  return 'None'
}

/* ─────────────────────────────────────────
   Negotiation status mapping
───────────────────────────────────────── */
function adaptNegotiationStatus(
  raw: string | null,
): Listing['negotiationStatus'] {
  if (!raw) return undefined
  const valid = new Set(['pending', 'negotiating', 'responded', 'accepted', 'rejected'])
  if (valid.has(raw)) return raw as Listing['negotiationStatus']
  // "negotiating" is the likely backend value — keep as-is if valid, else map
  return 'pending'
}

/* ─────────────────────────────────────────
   Notification type mapping
───────────────────────────────────────── */
const NOTIFICATION_TYPE_MAP: Record<string, NotificationEvent> = {
  new_matches: 'New matches',
  match: 'New matches',
  price_drops: 'Price drops',
  price_drop: 'Price drops',
  landlord_replies: 'Landlord replies',
  negotiation_updates: 'Negotiation updates',
  negotiation: 'Negotiation updates',
  tour_scheduled: 'Tour scheduled',
  application_updates: 'Application updates',
  documents_required: 'Documents required',
  lease_offers: 'Lease offers',
}

function adaptNotificationType(raw: string): NotificationEvent {
  return NOTIFICATION_TYPE_MAP[raw] ?? 'Negotiation updates'
}

/* ─────────────────────────────────────────
   Main listing adapter
───────────────────────────────────────── */
export function adaptListing(out: ListingOut): Listing {
  const matchScore = out.matchScore !== null ? Math.round(out.matchScore * 100) : 0

  const landlordContact =
    out.hostEmail ?? out.hostPhone ?? 'Contact via app'

  const leaseLengthStr =
    out.leaseLength !== null ? `${out.leaseLength} months` : 'Flexible'

  // Derive tags from imageLabels (up to 4)
  const tags = (out.imageLabels ?? []).slice(0, 4)

  return {
    id: out.id,
    title: out.title,
    // Backend currently returns apt.name for both title and address; use address field
    address: out.address,
    neighborhood: out.neighborhood ?? 'Unknown',
    price: out.price,
    originalPrice: out.price,
    bedrooms: adaptBedrooms(out.bedrooms),
    bathrooms: 1,
    sqft: 600,
    matchScore,
    matchType: (out.matchType === 'perfect' || out.matchType === 'flex') ? out.matchType : 'flex',
    status: 'available',
    negotiationStatus: adaptNegotiationStatus(out.negotiationStatus),
    commuteTime: out.commuteMinutes ?? 0,
    images: out.images.length > 0
      ? out.images
      : [`https://picsum.photos/seed/${out.id}/400/200`],
    amenities: [],
    pets: out.pets,
    parking: out.parking.length > 0,
    laundry: adaptLaundry(out.laundry),
    lat: out.lat ?? 37.7749,
    lng: out.lng ?? -122.4194,
    aiExplanation: out.matchReasoning ?? '',
    aiRationale: [],
    safetyScore: 80,
    priceTrend: [],
    tags,
    nearbyPOIs: [],
    landlord: landlordContact,
    availableFrom: out.availableFrom ?? new Date().toISOString().slice(0, 10),
    leaseLength: leaseLengthStr,
    deposit: out.price,
  }
}

/* ─────────────────────────────────────────
   Agent log adapter
───────────────────────────────────────── */
export function adaptAgentLog(out: AgentLogOut): AgentLog {
  return {
    id: out.id,
    timestamp: out.timestamp,
    level: (['info', 'success', 'warning', 'error'].includes(out.level)
      ? out.level
      : 'info') as AgentLog['level'],
    message: out.message,
    phase: out.phase,
  }
}

/* ─────────────────────────────────────────
   Notification adapter
───────────────────────────────────────── */
export function adaptNotification(out: ApiNotificationOut): Notification {
  return {
    id: out.id,
    type: adaptNotificationType(out.type),
    title: out.title,
    message: out.message,
    timestamp: out.timestamp,
    read: out.read,
    listingId: out.listingId,
  }
}

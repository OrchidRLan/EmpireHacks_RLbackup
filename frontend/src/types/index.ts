export type BedroomType = 'Studio' | '1BR' | '2BR' | '3BR+'

export type TransportMode = 'Drive' | 'Transit' | 'Bike'

export type Amenity =
  | 'Hardwood floors'
  | 'Dishwasher'
  | 'Air conditioning'
  | 'Balcony'
  | 'Pool'
  | 'Gym'

export type MoveInUrgency = 'Just browsing' | 'Flexible' | 'Soon' | 'Urgent'

export type NegotiableItem =
  | 'Rent'
  | 'Move-in date'
  | 'Lease length'
  | 'Deposit'
  | 'Parking fee'
  | 'Pet fee'
  | 'Utilities'
  | 'Furnishing'
  | 'Application fee'
  | 'Promotions'

export type NegotiationGoal =
  | 'Lowest price'
  | 'Best value'
  | 'Fastest approval'
  | 'Flexible move-in'
  | 'Lowest upfront cost'

export type AgentTone = 'Polite' | 'Professional' | 'Assertive' | 'Flexible'

export type OutreachTiming = 'Anytime' | 'Business hours' | 'Weekdays'

export type NotificationMode = 'Minimal' | 'Balanced' | 'Aggressive'

export type NotificationChannel = 'Email' | 'SMS' | 'Push' | 'WhatsApp' | 'In-app'

export type NotificationEvent =
  | 'New matches'
  | 'Price drops'
  | 'Landlord replies'
  | 'Negotiation updates'
  | 'Tour scheduled'
  | 'Application updates'
  | 'Documents required'
  | 'Lease offers'

export type NotificationFrequency = 'Real-time' | 'Daily' | 'Twice daily' | 'Weekly'

export interface HousingPreferences {
  bedrooms: BedroomType[]
  budgetMin: number
  budgetMax: number
  location: string
  moveInDate: string
  moveInUrgency: MoveInUrgency | null
  commuteAddress: string
  transportModes: TransportMode[]
  maxCommuteTime: number
  amenities: Amenity[]
  pets: boolean | null
  laundry: 'In-unit' | 'In-building' | 'None' | null
  parking: boolean | null
}

export interface NegotiationPreferences {
  enabled: boolean
  negotiableItems: NegotiableItem[]
  goal: NegotiationGoal | null
  maxRent: number
  maxDeposit: number
  latestMoveIn: string
  leaseLengthMin: number
  leaseLengthMax: number
  approvalConditions: string[]
  agentTone: AgentTone | null
  outreachTiming: OutreachTiming | null
  maxFollowUps: number
  canScheduleTours: boolean
  canSubmitApplications: boolean
  canConfirmLeaseTerms: boolean
  idealRent: number
  absoluteMaxRent: number
}

export interface NotificationPreferences {
  mode: NotificationMode | null
  channels: NotificationChannel[]
  events: NotificationEvent[]
  frequency: NotificationFrequency | null
  quietHoursStart: string
  quietHoursEnd: string
  timezone: string
  priceDropThreshold: number
  matchScoreThreshold: number
  reminderCount: number
  reminderIntervalHours: number
}

export interface UserPreferences {
  housing: HousingPreferences
  negotiation: NegotiationPreferences
  notifications: NotificationPreferences
}

export type ListingStatus = 'available' | 'pending' | 'unavailable'
export type MatchType = 'perfect' | 'flex'
export type NegotiationStatus = 'pending' | 'negotiating' | 'responded' | 'accepted' | 'rejected'

export interface Listing {
  id: string
  title: string
  address: string
  neighborhood: string
  price: number
  originalPrice?: number
  bedrooms: BedroomType
  bathrooms: number
  sqft: number
  matchScore: number
  matchType: MatchType
  status: ListingStatus
  negotiationStatus?: NegotiationStatus
  commuteTime: number
  images: string[]
  amenities: Amenity[]
  pets: boolean
  parking: boolean
  laundry: 'In-unit' | 'In-building' | 'None'
  lat: number
  lng: number
  aiExplanation: string
  aiRationale: string[]
  safetyScore: number
  priceTrend: number[]
  tags: string[]
  nearbyPOIs: { name: string; distance: string; type: string }[]
  landlord: string
  availableFrom: string
  leaseLength: string
  deposit: number
}

export interface AgentStatus {
  isRunning: boolean
  currentAction: string
  phase: 'search' | 'filter' | 'rank' | 'negotiate' | 'notify' | 'idle'
  logs: AgentLog[]
  matchesFound: number
  negotiationsActive: number
  toursScheduled: number
}

export interface AgentLog {
  id: string
  timestamp: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  phase: string
}

export interface Notification {
  id: string
  type: NotificationEvent
  title: string
  message: string
  timestamp: string
  read: boolean
  listingId?: string
}

export type DashboardPanel = 'match' | 'preferences' | 'negotiation' | 'agent'

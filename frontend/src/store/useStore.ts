import { create } from 'zustand'
import type {
  UserPreferences,
  Listing,
  AgentStatus,
  Notification,
  DashboardPanel,
  HousingPreferences,
  NegotiationPreferences,
  NotificationPreferences,
} from '../types'
import { mockListings, mockAgentLogs } from '../data/mockListings'
import {
  authApi,
  listingsApi,
  agentApi,
  notificationsApi,
  preferencesApi,
  matchingApi,
  getToken,
  setToken,
} from '../lib/api'
import { adaptListing, adaptAgentLog, adaptNotification } from '../lib/apiAdapter'

/* ─────────────────────────────────────────
   State interface
───────────────────────────────────────── */
interface AppState {
  // Theme
  darkMode: boolean
  toggleDarkMode: () => void

  // Auth
  userId: string | null
  userName: string | null
  userEmail: string | null
  authLoading: boolean
  initAuth: () => Promise<void>

  // Onboarding
  onboardingStep: number
  setOnboardingStep: (step: number) => void
  onboardingComplete: boolean
  setOnboardingComplete: (v: boolean) => void

  // Preferences
  preferences: UserPreferences
  updateHousing: (patch: Partial<HousingPreferences>) => void
  updateNegotiation: (patch: Partial<NegotiationPreferences>) => void
  updateNotifications: (patch: Partial<NotificationPreferences>) => void
  savePreferences: () => Promise<void>

  // Listings
  listings: Listing[]
  selectedListingId: string | null
  setSelectedListing: (id: string | null) => void
  negotiationCart: string[]
  addToNegotiation: (id: string) => void
  removeFromNegotiation: (id: string) => void
  removeListing: (id: string) => void
  likedListings: Set<string>
  toggleLike: (id: string) => void
  loadListings: () => Promise<void>

  // Dashboard
  activePanel: DashboardPanel
  setActivePanel: (panel: DashboardPanel) => void
  sidebarOpen: boolean
  toggleSidebar: () => void

  // New nav / layout
  topTab: 'match' | 'agent'
  setTopTab: (tab: 'match' | 'agent') => void
  negStatusFilter: 'all' | 'not-started' | 'in-progress' | 'completed'
  setNegStatusFilter: (f: 'all' | 'not-started' | 'in-progress' | 'completed') => void
  listSidebarOpen: boolean
  toggleListSidebar: () => void
  dashboardModules: string[]
  addDashboardModule: (m: string) => void
  removeDashboardModule: (m: string) => void
  prefModalOpen: boolean
  prefModalTab: 'housing' | 'negotiation' | 'notifications'
  setPrefModal: (open: boolean, tab?: 'housing' | 'negotiation' | 'notifications') => void

  // Agent
  agentStatus: AgentStatus
  toggleAgent: () => Promise<void>
  loadAgentStatus: () => Promise<void>
  loadAgentLogs: () => Promise<void>

  // Notifications
  notifications: Notification[]
  markNotificationRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
  unreadCount: number
  loadNotifications: () => Promise<void>
}

/* ─────────────────────────────────────────
   Default preference values
───────────────────────────────────────── */
const defaultHousing: HousingPreferences = {
  bedrooms: ['1BR', '2BR'],
  budgetMin: 1500,
  budgetMax: 3500,
  location: 'San Francisco, CA',
  moveInDate: '2026-09-01',
  moveInUrgency: 'Soon',
  commuteAddress: '101 California St, San Francisco, CA',
  transportModes: ['Transit'],
  maxCommuteTime: 30,
  amenities: ['Hardwood floors', 'Dishwasher', 'Air conditioning'],
  pets: true,
  laundry: 'In-unit',
  parking: null,
}

const defaultNegotiation: NegotiationPreferences = {
  enabled: true,
  negotiableItems: ['Rent', 'Deposit', 'Pet fee'],
  goal: 'Best value',
  maxRent: 3500,
  maxDeposit: 7000,
  latestMoveIn: '2026-05-01',
  leaseLengthMin: 12,
  leaseLengthMax: 24,
  approvalConditions: ['Rent exceeds budget', 'High deposit'],
  agentTone: 'Professional',
  outreachTiming: 'Business hours',
  maxFollowUps: 3,
  canScheduleTours: true,
  canSubmitApplications: false,
  canConfirmLeaseTerms: false,
  idealRent: 2800,
  absoluteMaxRent: 3500,
}

const defaultNotifications: NotificationPreferences = {
  mode: 'Balanced',
  channels: ['Email', 'In-app'],
  events: ['New matches', 'Price drops', 'Landlord replies', 'Negotiation updates'],
  frequency: 'Real-time',
  quietHoursStart: '22:00',
  quietHoursEnd: '08:00',
  timezone: 'America/Los_Angeles',
  priceDropThreshold: 5,
  matchScoreThreshold: 75,
  reminderCount: 2,
  reminderIntervalHours: 24,
}

/* ─────────────────────────────────────────
   Mock fallback notifications
───────────────────────────────────────── */
const mockNotifications: Notification[] = [
  {
    id: 'notif-001',
    type: 'Landlord replies',
    title: 'Landlord replied on Mission District listing',
    message: 'Rosa M. Herrera offered $2,350/mo with waived pet fee',
    timestamp: '2026-03-21T09:03:30',
    read: false,
    listingId: 'lst-002',
  },
  {
    id: 'notif-002',
    type: 'Price drops',
    title: 'Price drop on Hayes Valley studio',
    message: '501 Fell St dropped $50 to $1,950/mo',
    timestamp: '2026-03-21T08:45:00',
    read: false,
    listingId: 'lst-003',
  },
  {
    id: 'notif-003',
    type: 'New matches',
    title: '7 new perfect matches found',
    message: 'Your agent found 7 listings scoring above 80%',
    timestamp: '2026-03-21T09:00:15',
    read: true,
  },
  {
    id: 'notif-004',
    type: 'Negotiation updates',
    title: 'Negotiation update for SoMa listing',
    message: 'Agent submitted counter-offer of $3,100/mo for 450 Brannan St',
    timestamp: '2026-03-21T08:00:00',
    read: true,
    listingId: 'lst-001',
  },
]

/* ─────────────────────────────────────────
   Demo credentials helpers
───────────────────────────────────────── */
const DEMO_EMAIL_KEY = 'rento_demo_email'

function getDemoEmail(): string {
  const existing = localStorage.getItem(DEMO_EMAIL_KEY)
  if (existing) return existing
  const uuid = crypto.randomUUID()
  const email = `demo-${uuid}@rento.app`
  localStorage.setItem(DEMO_EMAIL_KEY, email)
  return email
}

/* ─────────────────────────────────────────
   Store
───────────────────────────────────────── */
export const useStore = create<AppState>((set, get) => ({
  /* ── Theme ── */
  darkMode: false,
  toggleDarkMode: () => {
    const next = !get().darkMode
    set({ darkMode: next })
    if (next) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },

  /* ── Auth ── */
  userId: null,
  userName: null,
  userEmail: null,
  authLoading: true,

  initAuth: async () => {
    set({ authLoading: true })
    try {
      const existingToken = getToken()
      if (existingToken) {
        // Validate with backend
        try {
          const me = await authApi.me()
          set({ userId: me.id, userName: me.name, userEmail: me.email, authLoading: false })
          return
        } catch {
          // Token invalid — fall through to demo login
        }
      }

      // No valid token — register or login demo user
      const email = getDemoEmail()
      const password = 'rento-demo-2026'
      const name = 'Alex Kim'

      try {
        const res = await authApi.register({ email, password, name })
        setToken(res.token)
        set({ userId: res.user.id, userName: res.user.name, userEmail: res.user.email })
      } catch (err) {
        // 409 Conflict means user exists — try login
        const msg = err instanceof Error ? err.message : ''
        if (msg.includes('409') || msg.toLowerCase().includes('already') || msg.toLowerCase().includes('exist')) {
          try {
            const res = await authApi.login({ email, password })
            setToken(res.token)
            set({ userId: res.user.id, userName: res.user.name, userEmail: res.user.email })
          } catch {
            // login also failed — continue without auth
          }
        }
      }
    } catch {
      // Network error or backend not running — continue with mock data
    } finally {
      set({ authLoading: false })
    }
  },

  /* ── Onboarding ── */
  onboardingStep: 1,
  setOnboardingStep: (step) => set({ onboardingStep: step }),
  onboardingComplete: false,
  setOnboardingComplete: (v) => set({ onboardingComplete: v }),

  /* ── Preferences ── */
  preferences: {
    housing: defaultHousing,
    negotiation: defaultNegotiation,
    notifications: defaultNotifications,
  },
  updateHousing: (patch) =>
    set((s) => ({
      preferences: {
        ...s.preferences,
        housing: { ...s.preferences.housing, ...patch },
      },
    })),
  updateNegotiation: (patch) =>
    set((s) => ({
      preferences: {
        ...s.preferences,
        negotiation: { ...s.preferences.negotiation, ...patch },
      },
    })),
  updateNotifications: (patch) =>
    set((s) => ({
      preferences: {
        ...s.preferences,
        notifications: { ...s.preferences.notifications, ...patch },
      },
    })),

  savePreferences: async () => {
    const { preferences } = get()
    const { housing, negotiation, notifications } = preferences

    // Map frontend bedroom names to backend format
    const bedroomMap: Record<string, string> = {
      'Studio': 'studio', '1BR': '1b', '2BR': '2b', '3BR+': '3b',
    }
    const bedroomType = housing.bedrooms.length > 0
      ? (bedroomMap[housing.bedrooms[0]] ?? '1b')
      : '1b'

    // Map laundry
    const laundryMap: Record<string, string> = {
      'In-unit': 'in_unit', 'In-building': 'on_site', 'None': '',
    }
    const laundry = housing.laundry
      ? (laundryMap[housing.laundry] ? [laundryMap[housing.laundry]] : [])
      : []

    // Map commute method
    const commuteMap: Record<string, string> = {
      'Drive': 'drive', 'Transit': 'transit', 'Bike': 'bike',
    }
    const commuteMethod = housing.transportModes.length > 0
      ? (commuteMap[housing.transportModes[0]] ?? 'transit')
      : 'transit'

    try {
      await Promise.all([
        preferencesApi.updateHousing({
          bedroomType,
          minBudget: housing.budgetMin,
          maxBudget: housing.budgetMax,
          moveInDate: housing.moveInDate,
          laundry,
          pets: housing.pets ?? false,
          commuteMethod,
          maxCommuteMinutes: housing.maxCommuteTime,
          parking: housing.parking ? ['garage'] : [],
        }),
        preferencesApi.updateNegotiation({
          enableAutomation: negotiation.enabled,
          negotiableItems: negotiation.negotiableItems,
          goals: negotiation.goal ? [negotiation.goal] : [],
          maxRent: negotiation.maxRent,
          maxDeposit: negotiation.maxDeposit,
          latestMoveInDate: negotiation.latestMoveIn,
          minLeaseMonths: negotiation.leaseLengthMin,
          maxLeaseMonths: negotiation.leaseLengthMax,
          negotiationStyle: (negotiation.agentTone ?? 'professional').toLowerCase(),
        }),
        preferencesApi.updateNotifications({
          enableNotifications: true,
          notificationTypes: ['match', 'price_drop', 'negotiation'],
          frequency: 'realtime',
        }),
      ])
      // Trigger filter + scoring in background after preferences saved
      matchingApi.runFilter().catch(() => {})
    } catch {
      // Silently fail — preferences saved locally regardless
    }
  },

  /* ── Listings ── */
  listings: mockListings,
  selectedListingId: 'lst-001',
  setSelectedListing: (id) => set({ selectedListingId: id }),
  negotiationCart: ['lst-002', 'lst-003'],
  addToNegotiation: (id) =>
    set((s) => ({
      negotiationCart: s.negotiationCart.includes(id)
        ? s.negotiationCart
        : [...s.negotiationCart, id],
    })),
  removeFromNegotiation: (id) =>
    set((s) => ({ negotiationCart: s.negotiationCart.filter((x) => x !== id) })),

  removeListing: (id) =>
    set((s) => ({
      listings: s.listings.filter((l) => l.id !== id),
      negotiationCart: s.negotiationCart.filter((x) => x !== id),
      selectedListingId: s.selectedListingId === id ? null : s.selectedListingId,
    })),

  likedListings: new Set<string>(),
  toggleLike: (id) =>
    set((s) => {
      const next = new Set(s.likedListings)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return { likedListings: next }
    }),

  loadListings: async () => {
    try {
      const page = await listingsApi.list({ pageSize: 100 })
      if (page.items.length > 0) {
        set({ listings: page.items.map(adaptListing) })
      }
    } catch {
      // Keep existing mock data on error
    }
  },

  /* ── Dashboard ── */
  activePanel: 'match',
  setActivePanel: (panel) => set({ activePanel: panel }),
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  /* ── New nav / layout ── */
  topTab: 'match',
  setTopTab: (tab) => set({ topTab: tab }),
  negStatusFilter: 'all',
  setNegStatusFilter: (f) => set({ negStatusFilter: f }),
  listSidebarOpen: true,
  toggleListSidebar: () => set((s) => ({ listSidebarOpen: !s.listSidebarOpen })),
  dashboardModules: ['info', 'rationale', 'map', 'neighborhood', 'negotiation'],
  addDashboardModule: (m) =>
    set((s) => ({
      dashboardModules: s.dashboardModules.includes(m)
        ? s.dashboardModules
        : [...s.dashboardModules, m],
    })),
  removeDashboardModule: (m) =>
    set((s) => ({ dashboardModules: s.dashboardModules.filter((x) => x !== m) })),
  prefModalOpen: false,
  prefModalTab: 'housing',
  setPrefModal: (open, tab) =>
    set((s) => ({ prefModalOpen: open, prefModalTab: tab ?? s.prefModalTab })),

  /* ── Agent ── */
  agentStatus: {
    isRunning: true,
    currentAction: 'Scanning new listings...',
    phase: 'search',
    logs: mockAgentLogs,
    matchesFound: 7,
    negotiationsActive: 2,
    toursScheduled: 1,
  },

  toggleAgent: async () => {
    const { agentStatus } = get()
    try {
      if (agentStatus.isRunning) {
        await agentApi.stop()
      } else {
        await agentApi.start()
      }
      await get().loadAgentStatus()
    } catch {
      // Fallback to local toggle
      set((s) => ({
        agentStatus: {
          ...s.agentStatus,
          isRunning: !s.agentStatus.isRunning,
          currentAction: s.agentStatus.isRunning ? 'Agent paused' : 'Resuming search...',
          phase: s.agentStatus.isRunning ? 'idle' : 'search',
        },
      }))
    }
  },

  loadAgentStatus: async () => {
    try {
      const status = await agentApi.status()
      set((s) => ({
        agentStatus: {
          ...s.agentStatus,
          isRunning: status.isRunning,
          currentAction: status.currentAction,
          phase: status.phase as AgentStatus['phase'],
          matchesFound: status.matchesFound,
          negotiationsActive: status.negotiationsActive,
          toursScheduled: status.toursScheduled,
        },
      }))
    } catch {
      // Keep existing mock status
    }
  },

  loadAgentLogs: async () => {
    try {
      const page = await agentApi.logs(1, 100)
      if (page.items.length > 0) {
        set((s) => ({
          agentStatus: {
            ...s.agentStatus,
            logs: page.items.map(adaptAgentLog),
          },
        }))
      }
    } catch {
      // Keep existing mock logs
    }
  },

  /* ── Notifications ── */
  notifications: mockNotifications,
  unreadCount: mockNotifications.filter((n) => !n.read).length,

  loadNotifications: async () => {
    try {
      const page = await notificationsApi.list()
      if (page.items.length > 0) {
        const adapted = page.items.map(adaptNotification)
        set({
          notifications: adapted,
          unreadCount: adapted.filter((n) => !n.read).length,
        })
      }
    } catch {
      // Keep existing mock notifications
    }
  },

  markNotificationRead: async (id) => {
    // Optimistic update
    set((s) => ({
      notifications: s.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
      unreadCount: Math.max(0, s.unreadCount - 1),
    }))
    try {
      await notificationsApi.readOne(id)
    } catch {
      // Optimistic update already applied — no rollback needed for UX
    }
  },

  markAllRead: async () => {
    // Optimistic update
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    }))
    try {
      await notificationsApi.readAll()
    } catch {
      // Optimistic update already applied
    }
  },
}))

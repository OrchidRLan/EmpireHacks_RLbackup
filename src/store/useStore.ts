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

interface AppState {
  // Theme
  darkMode: boolean
  toggleDarkMode: () => void

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

  // Listings
  listings: Listing[]
  selectedListingId: string | null
  setSelectedListing: (id: string | null) => void
  negotiationCart: string[]
  addToNegotiation: (id: string) => void
  removeFromNegotiation: (id: string) => void

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
  toggleAgent: () => void

  // Notifications
  notifications: Notification[]
  markNotificationRead: (id: string) => void
  markAllRead: () => void
  unreadCount: number
}

const defaultHousing: HousingPreferences = {
  bedrooms: ['1BR', '2BR'],
  budgetMin: 1500,
  budgetMax: 3500,
  location: 'San Francisco, CA',
  moveInDate: '2026-04-01',
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

export const useStore = create<AppState>((set, get) => ({
  // Theme
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

  // Onboarding
  onboardingStep: 1,
  setOnboardingStep: (step) => set({ onboardingStep: step }),
  onboardingComplete: false,
  setOnboardingComplete: (v) => set({ onboardingComplete: v }),

  // Preferences
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

  // Listings
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

  // Dashboard
  activePanel: 'match',
  setActivePanel: (panel) => set({ activePanel: panel }),
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  // New nav / layout
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

  // Agent
  agentStatus: {
    isRunning: true,
    currentAction: 'Scanning new listings...',
    phase: 'search',
    logs: mockAgentLogs,
    matchesFound: 7,
    negotiationsActive: 2,
    toursScheduled: 1,
  },
  toggleAgent: () =>
    set((s) => ({
      agentStatus: {
        ...s.agentStatus,
        isRunning: !s.agentStatus.isRunning,
        currentAction: s.agentStatus.isRunning ? 'Agent paused' : 'Resuming search...',
        phase: s.agentStatus.isRunning ? 'idle' : 'search',
      },
    })),

  // Notifications
  notifications: mockNotifications,
  markNotificationRead: (id) =>
    set((s) => ({
      notifications: s.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
      unreadCount: Math.max(0, s.unreadCount - 1),
    })),
  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
  unreadCount: mockNotifications.filter((n) => !n.read).length,
}))

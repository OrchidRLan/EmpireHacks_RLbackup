# Rento UI

A React + TypeScript single-page application for AI-assisted apartment hunting. Users define preferences once, and an AI agent continuously searches, filters, ranks, and negotiates listings on their behalf.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 19 |
| Language | TypeScript 5 (strict) |
| Build Tool | Vite 8 |
| Styling | Tailwind CSS 3 (dark mode via class) |
| State Management | Zustand 5 |
| Routing | React Router DOM 7 |
| UI Primitives | Radix UI + shadcn-style wrappers |
| Icons | Lucide React |
| Drag & Drop | DnD Kit + React Grid Layout |
| Maps | Leaflet + React Leaflet |

---

## Project Structure

```
ui/
├── index.html                    # HTML entry — loads fonts, mounts #root
├── src/
│   ├── main.tsx                  # ReactDOM.createRoot entry point
│   ├── App.tsx                   # Router + ThemeProvider root
│   │
│   ├── pages/
│   │   ├── Onboarding/
│   │   │   ├── index.tsx         # 3-step wizard shell (progress bar, nav)
│   │   │   ├── Step1Housing.tsx  # Bedroom, budget, location, amenities
│   │   │   ├── Step2Negotiation.tsx  # Negotiation goals, tone, limits
│   │   │   ├── Step3Notifications.tsx  # Channels, events, quiet hours
│   │   │   ├── CompletionScreen.tsx    # Finish + redirect to dashboard
│   │   │   └── AIPreviewPanel.tsx      # Live AI preview during onboarding
│   │   │
│   │   └── Dashboard/
│   │       ├── index.tsx         # Layout shell (Navbar + panel switcher)
│   │       ├── PanelMatch.tsx    # Listing list, detail view, grid modules
│   │       ├── PanelAgent.tsx    # Agent pipeline log + toggle
│   │       ├── PanelNegotiation.tsx  # Negotiation status management
│   │       └── PanelPreferences.tsx  # Quick preferences surface
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Navbar.tsx        # Logo, tab switcher, agent pill, notifications, user menu
│   │   │   ├── Sidebar.tsx       # Collapsible side nav with badges
│   │   │   └── PreferencesModal.tsx  # Full preferences editor (3 tabs)
│   │   └── ui/                   # Radix-based primitives
│   │       ├── badge.tsx
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── slider.tsx
│   │       ├── switch.tsx
│   │       └── tabs.tsx
│   │
│   ├── store/
│   │   └── useStore.ts           # Single Zustand store — all global state
│   ├── types/
│   │   └── index.ts              # All TypeScript type & union definitions
│   ├── data/
│   │   └── mockListings.ts       # 7 SF apartments + 15 agent log entries
│   └── lib/
│       └── utils.ts              # cn(), formatCurrency(), formatTime()
│
├── public/                       # Static assets served as-is
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.app.json             # Strict TS for src/
└── package.json
```

---

## Routes

| Path | Component | Description |
|---|---|---|
| `/` | — | Redirects to `/onboarding` |
| `/onboarding` | `OnboardingPage` | 3-step preference wizard |
| `/dashboard` | `DashboardPage` | Main app with Match / Agent tabs |
| `*` | — | Fallback redirect to `/onboarding` |

---

## State Architecture

All global state lives in a single Zustand store at [src/store/useStore.ts](src/store/useStore.ts). It is divided into the following slices:

| Slice | Key Fields |
|---|---|
| **Theme** | `darkMode`, `toggleDarkMode()` |
| **Onboarding** | `onboardingStep` (1–4), `onboardingComplete` |
| **Housing Preferences** | bedrooms, budget, location, commute, amenities, pets, parking, urgency |
| **Negotiation Preferences** | enabled, goals, tone, limits, lease terms, approval conditions |
| **Notification Preferences** | channels, events, frequency, quiet hours, thresholds |
| **Listings** | `listings[]`, `selectedListingId`, `negotiationCart[]` |
| **Dashboard UI** | `activePanel`, `sidebarOpen`, `topTab`, `prefModalOpen` |
| **Agent** | `agentStatus` (phase, logs, counts), `toggleAgent()` |
| **Notifications** | `notifications[]`, `markNotificationRead()`, `unreadCount` |

Components read state with `useStore(s => s.field)` and mutate it via actions returned from the same store.

---

## User Flow

```
/onboarding
  Step 1 — Housing Preferences
      ↓ (Next)
  Step 2 — Negotiation Preferences
      ↓ (Next)
  Step 3 — Notification Preferences
      ↓ (Finish)
  Completion Screen
      ↓ (Go to Dashboard)

/dashboard
  ┌─────────────────────────────────────────┐
  │ Navbar (tabs: Match | Agent)            │
  ├──────────┬──────────────────────────────┤
  │ Sidebar  │  PanelMatch                  │
  │          │    ├── Listing list (left)    │
  │          │    └── Detail view (right)   │
  │          │         ├── Info module      │
  │          │         ├── AI Rationale     │
  │          │         ├── Map              │
  │          │         ├── Neighborhood     │
  │          │         └── Negotiation      │
  │          │                              │
  │          │  PanelAgent (tab switch)     │
  │          │    ├── Search stage          │
  │          │    ├── Image analysis        │
  │          │    ├── Filter logs           │
  │          │    ├── Ranking / scoring     │
  │          │    ├── Negotiation convos    │
  │          │    └── Notification delivery │
  └──────────┴──────────────────────────────┘
```

---

## Key Component Responsibilities

### Navbar
- Branding ("RentAgent AI")
- Tab switcher between **Match** and **Agent** views
- Agent status pill (pulsing when running)
- Dark mode toggle
- Notifications bell with unread badge
- User profile menu — opens PreferencesModal or logs out

### Sidebar
- Collapsible icon rail
- Nav items: Match, Preferences, Negotiation, Agent
- Badges: negotiation cart count, agent running indicator
- Expanded mode shows labels + descriptions; collapsed mode shows tooltips
- Session stats: matches found, active negotiations

### PanelMatch
- Filterable, searchable listing list
- Selected listing opens a **React Grid Layout** detail view with draggable/resizable modules
- Each module is independently movable: Info, AI Rationale, Map, Neighborhood, Negotiation Status
- Negotiation status displayed with color-coded dot indicators

### PanelAgent
- Visualizes the full AI pipeline in stages:
  1. **Search** — data sources being queried
  2. **Image Analysis** — photo processing logs
  3. **Filter** — rules applied + count of results
  4. **Rank** — match score computation
  5. **Negotiate** — message threads per listing
  6. **Notify** — delivery confirmation
- Agent can be toggled on/off from this panel or the Navbar

### PreferencesModal
- Triggered from user menu or Sidebar
- Three-tab editor: Housing / Negotiation / Notifications
- Writes directly to Zustand store; changes take effect immediately

---

## Data Types

All types are defined in [src/types/index.ts](src/types/index.ts).

**Core models:**

```
Listing          — id, address, price, bedrooms, matchScore, negotiationStatus,
                   aiExplanation, safetyScore, priceTrends, landlordInfo, ...

HousingPreferences     — bedrooms, budget, location, commute, amenities, pets, ...
NegotiationPreferences — enabled, goal, tone, limits, timing, permissions, ...
NotificationPreferences — mode, channels, events, frequency, quietHours, ...

AgentStatus      — isRunning, currentAction, phase, logs[], matchesFound,
                   negotiationsActive, toursScheduled
AgentLog         — id, timestamp, level, message, phase

Notification     — id, type, title, message, timestamp, read, listingId
```

---

## Mock Data

[src/data/mockListings.ts](src/data/mockListings.ts) provides:
- **7 SF apartment listings** across SoMa, Mission, Hayes Valley, Pacific Heights, Alamo Square, Dogpatch, Noe Valley
- **15 agent log entries** simulating a full search → filter → rank → negotiate → notify pipeline

No real backend or API calls exist in the current build.

---

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Type-check + build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

The dev server runs on `http://localhost:5173` by default.

---

## Conventions

- **Styling**: Tailwind utility classes only. Custom colors and animations are defined in `tailwind.config.js`. Dark mode is toggled by adding the `dark` class to `<html>` via the `ThemeProvider` in `App.tsx`.
- **Component variants**: Use `class-variance-authority` (CVA) via the primitives in `src/components/ui/`.
- **Class merging**: Always use the `cn()` helper from `src/lib/utils.ts` to safely merge Tailwind classes.
- **State mutations**: All state changes go through Zustand action functions — components never mutate state directly.
- **TypeScript**: Strict mode is on. Prefer named union types over raw strings for enums (see `src/types/index.ts`).

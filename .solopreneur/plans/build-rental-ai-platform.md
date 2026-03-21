# Plan: Real Estate Rental AI Agent Platform

## Context
A complete React + TypeScript frontend for an AI-powered rental agent platform. Users configure preferences via a 3-step onboarding wizard, then interact with a dashboard showing matches, negotiation status, and agent activity. All data is mocked; state is managed via Zustand.

## Step 1: Project Configuration
**Files**: `tailwind.config.js` (modify), `src/index.css` (modify), `vite.config.ts` (modify)
**Do**: Configure Tailwind with dark mode class strategy, extend theme with custom colors. Add Tailwind directives to CSS.
**Acceptance**: `npm run dev` starts without errors.

## Step 2: Type Definitions & Mock Data
**Files**: `src/types/index.ts` (create), `src/data/mockListings.ts` (create)
**Do**: Define all TypeScript interfaces (Listing, Preferences, AgentStatus, Notification). Create 6 mock property listings with realistic data.
**Acceptance**: No TypeScript errors on import.

## Step 3: Zustand Store
**Files**: `src/store/useStore.ts` (create)
**Do**: Create global store with slices for preferences, selectedListing, agentStatus, notifications, onboarding step, and dark mode.
**Acceptance**: Store exports work from any component.

## Step 4: shadcn/ui Utility & Base Components
**Files**: `src/lib/utils.ts` (create), `src/components/ui/button.tsx` (create), `src/components/ui/badge.tsx` (create), `src/components/ui/card.tsx` (create), `src/components/ui/slider.tsx` (create), `src/components/ui/switch.tsx` (create), `src/components/ui/tabs.tsx` (create)
**Do**: Implement cn() util and shadcn-style UI primitives using Radix + Tailwind CVA.
**Acceptance**: Components render with correct variants.

## Step 5: Onboarding Pages (3 steps)
**Files**: `src/pages/Onboarding/index.tsx` (create), `src/pages/Onboarding/Step1Housing.tsx` (create), `src/pages/Onboarding/Step2Negotiation.tsx` (create), `src/pages/Onboarding/Step3Notifications.tsx` (create), `src/pages/Onboarding/CompletionScreen.tsx` (create)
**Do**: Implement the full 3-step wizard with slide transitions, AI preview panel, all form controls (chips, sliders, date picker, map placeholder, toggles, cards).
**Acceptance**: All 3 steps navigable, inputs update Zustand state.

## Step 6: Dashboard Layout
**Files**: `src/pages/Dashboard/index.tsx` (create), `src/components/layout/Navbar.tsx` (create), `src/components/layout/Sidebar.tsx` (create)
**Do**: Full dashboard layout with collapsible sidebar, navbar with agent status pulse animation and notification bell, panel switcher.
**Acceptance**: Sidebar collapses, panels switch on nav click.

## Step 7: Dashboard Panels
**Files**: `src/pages/Dashboard/PanelMatch.tsx` (create), `src/pages/Dashboard/PanelPreferences.tsx` (create), `src/pages/Dashboard/PanelNegotiation.tsx` (create), `src/pages/Dashboard/PanelAgent.tsx` (create)
**Do**: Implement all 4 panels with full interactivity: listing cards, map placeholder, detail panel, negotiation cart, agent workflow graph, log stream.
**Acceptance**: Each panel renders mock data and responds to user interactions.

## Step 8: App Router
**Files**: `src/App.tsx` (modify), `src/main.tsx` (modify)
**Do**: Set up React Router with routes for `/`, `/onboarding`, `/dashboard`. Redirect root to `/onboarding`.
**Acceptance**: Navigation between pages works.

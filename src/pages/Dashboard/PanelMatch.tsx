import { useState, useRef, useEffect } from 'react'
import GridLayout from 'react-grid-layout'
import type { Layout, LayoutItem } from 'react-grid-layout'
import { noCompactor } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import {
  MapPin, Clock, Star, Plus, Calendar, Bookmark,
  ChevronLeft, ChevronRight, TrendingDown, Shield,
  Coffee, ShoppingBag, TreePine, Train,
  Sparkles, CheckCircle2, MessageSquare,
  PanelLeftClose, PanelLeftOpen, X, LayoutGrid,
  Send, Bot, User, AlertCircle, ArrowUpDown,
} from 'lucide-react'
import { useStore } from '../../store/useStore'
import type { Listing } from '../../types'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { cn, formatCurrency } from '../../lib/utils'

/* ─────────────────────────────────────────
   Types
───────────────────────────────────────── */
type NegStatusFilter = 'all' | 'not-started' | 'in-progress' | 'completed'
type ModuleKey = 'info' | 'rationale' | 'map' | 'neighborhood' | 'negotiation'

const MODULE_DEFS: { key: ModuleKey; label: string; emoji: string }[] = [
  { key: 'info',         label: 'Detail Info',         emoji: '📋' },
  { key: 'rationale',   label: 'AI Rationale',         emoji: '✨' },
  { key: 'map',         label: 'Map',                  emoji: '🗺️' },
  { key: 'neighborhood', label: 'Neighborhood',         emoji: '🏘️' },
  { key: 'negotiation', label: 'Negotiation History',  emoji: '💬' },
]

const STATUS_FILTERS: { key: NegStatusFilter; label: string }[] = [
  { key: 'all',          label: 'All' },
  { key: 'not-started',  label: 'Not Started' },
  { key: 'in-progress',  label: 'In Progress' },
  { key: 'completed',    label: 'Completed' },
]

function negStatusOf(l: Listing): NegStatusFilter {
  if (!l.negotiationStatus) return 'not-started'
  if (l.negotiationStatus === 'responded' || l.negotiationStatus === 'accepted') return 'completed'
  return 'in-progress'
}

/* ─────────────────────────────────────────
   Listing list card (slim)
───────────────────────────────────────── */
function ListCard({ listing, selected, onClick }: {
  listing: Listing; selected: boolean; onClick: () => void
}) {
  const statusColor = negStatusOf(listing) === 'completed'
    ? 'bg-emerald-500'
    : negStatusOf(listing) === 'in-progress'
    ? 'bg-amber-500'
    : 'bg-slate-300 dark:bg-slate-600'

  return (
    <div
      onClick={onClick}
      className={cn(
        'flex gap-3 p-3 rounded-xl border cursor-pointer transition-all duration-150 hover:shadow-sm',
        selected
          ? 'border-indigo-400 bg-indigo-50/60 dark:bg-indigo-900/15 shadow-sm'
          : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-slate-300 dark:hover:border-slate-600'
      )}
    >
      {/* Thumbnail */}
      <div className="relative w-16 h-16 rounded-lg overflow-hidden shrink-0 bg-slate-100 dark:bg-slate-700">
        <img
          src={listing.images[0]}
          alt={listing.title}
          className="w-full h-full object-cover"
          onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${listing.id}/100/100` }}
        />
        <div className={cn('absolute top-1 right-1 w-2 h-2 rounded-full', statusColor)} />
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-1">
          <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-tight line-clamp-1">
            {listing.title}
          </p>
          <span
            className={cn(
              'shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full',
              listing.matchType === 'perfect'
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300'
                : 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300'
            )}
          >
            {listing.matchScore}%
          </span>
        </div>
        <p className="text-[11px] text-indigo-600 dark:text-indigo-400 font-semibold mt-0.5">
          {formatCurrency(listing.price)}<span className="text-slate-400 font-normal">/mo</span>
        </p>
        <p className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1 line-clamp-1">
          <MapPin size={9} />{listing.neighborhood}
        </p>
        <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400">
          <span>{listing.bedrooms}</span>
          <span>·</span>
          <span className="flex items-center gap-0.5"><Clock size={9} />{listing.commuteTime}m</span>
          {listing.originalPrice && listing.originalPrice > listing.price && (
            <><span>·</span><span className="text-amber-500 flex items-center gap-0.5"><TrendingDown size={9} />drop</span></>
          )}
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Map — 2-color markers
   🔴 red  = currently viewing (selected detail)
   🔵 blue = all listings in the filtered sidebar list
───────────────────────────────────────── */
const PIN_POSITIONS = [
  { top: '35%', left: '44%' }, { top: '56%', left: '31%' },
  { top: '41%', left: '27%' }, { top: '22%', left: '38%' },
  { top: '47%', left: '29%' }, { top: '61%', left: '54%' },
  { top: '69%', left: '34%' },
]

function MapView({ listings, selectedId, onSelect, height = 'h-56' }: {
  listings: Listing[]
  selectedId: string | null
  onSelect: (id: string) => void
  height?: string
}) {
  return (
    <div className={cn('relative w-full rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700', height)}>
      {/* Grid lines */}
      <svg className="absolute inset-0 w-full h-full opacity-10">
        <defs><pattern id="mg" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1"/></pattern></defs>
        <rect width="100%" height="100%" fill="url(#mg)"/>
      </svg>
      {/* Roads */}
      <svg className="absolute inset-0 w-full h-full opacity-20 dark:opacity-30">
        <line x1="0" y1="40%" x2="100%" y2="40%" stroke="#94a3b8" strokeWidth="3"/>
        <line x1="0" y1="65%" x2="100%" y2="65%" stroke="#94a3b8" strokeWidth="2"/>
        <line x1="30%" y1="0" x2="30%" y2="100%" stroke="#94a3b8" strokeWidth="2"/>
        <line x1="65%" y1="0" x2="65%" y2="100%" stroke="#94a3b8" strokeWidth="3"/>
        <line x1="15%" y1="20%" x2="80%" y2="80%" stroke="#94a3b8" strokeWidth="1.5"/>
      </svg>

      {/* Location label */}
      <div className="absolute top-2 left-2 bg-white/90 dark:bg-slate-900/90 rounded-lg px-2 py-1 text-[11px] font-medium text-slate-600 dark:text-slate-400 shadow border border-slate-200 dark:border-slate-700 z-20">
        San Francisco, CA
      </div>

      {/* Pins */}
      {listings.map((l, i) => {
        const pos = PIN_POSITIONS[i % PIN_POSITIONS.length]
        const isSel = l.id === selectedId
        return (
          <button
            key={l.id}
            onClick={() => onSelect(l.id)}
            style={{ top: pos.top, left: pos.left, zIndex: isSel ? 30 : 10 }}
            className="absolute -translate-x-1/2 -translate-y-full group"
          >
            {/* Price bubble */}
            <div className={cn(
              'px-2 py-0.5 rounded-full text-[10px] font-bold shadow-lg border-2 transition-all duration-150',
              isSel
                ? 'bg-red-500 border-white ring-2 ring-red-300 scale-110'
                : 'bg-blue-500 border-white hover:scale-105'
            )}>
              <span className="text-white drop-shadow-sm">{formatCurrency(l.price)}</span>
            </div>
            {/* Pin stem */}
            <div className={cn('w-1.5 h-1.5 rounded-full mx-auto -mt-px', isSel ? 'bg-red-500' : 'bg-blue-500')} />

            {/* Hover tooltip */}
            <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none w-36 bg-slate-900 text-white text-[10px] rounded-lg p-2 shadow-xl z-40">
              <p className="font-semibold leading-tight">{l.title}</p>
              <p className="text-slate-300 mt-0.5">{l.neighborhood}</p>
              <div className="flex items-center gap-1 mt-1">
                <span className={cn('w-1.5 h-1.5 rounded-full', isSel ? 'bg-red-400' : 'bg-blue-400')} />
                <span className="text-slate-300">{isSel ? 'Currently viewing' : 'In list'}</span>
              </div>
            </div>
          </button>
        )
      })}

      {/* Legend */}
      <div className="absolute bottom-2 right-2 bg-white/95 dark:bg-slate-900/95 rounded-lg p-2 shadow-md border border-slate-200 dark:border-slate-700 space-y-1 z-20">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-600 dark:text-slate-400">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500 ring-1 ring-red-300"/>
          Viewing
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-600 dark:text-slate-400">
          <div className="w-2.5 h-2.5 rounded-full bg-blue-500"/>
          In list
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Negotiation history for a listing
───────────────────────────────────────── */
const mockMessages: Record<string, { sender: 'agent' | 'landlord' | 'user'; text: string; time: string }[]> = {
  'lst-002': [
    { sender: 'agent', text: 'Hi Rosa, reaching out on behalf of a qualified tenant interested in your 1BR at 2300 Mission St. Would you be open to discussing terms?', time: '08:00' },
    { sender: 'landlord', text: 'Hi! Unit available April 1st. Asking $2,400/mo, $4,800 deposit. Small pets fine with $500 deposit.', time: '09:00' },
    { sender: 'agent', text: 'Thank you! Given a 12-month lease with renewal potential, would you consider $2,350/mo?', time: '09:02' },
    { sender: 'landlord', text: "I can do $2,350 with one month deposit. I'll waive the pet deposit if they're responsible. When can they view?", time: '09:03' },
  ],
  'lst-003': [
    { sender: 'agent', text: 'Hello, reaching out about the studio at 501 Fell St. My client is very interested.', time: '07:30' },
    { sender: 'landlord', text: 'Thanks for reaching out! We just dropped the price to $1,950. Is your client flexible on move-in?', time: '08:45' },
  ],
}

function NegotiationHistory({ listingId }: { listingId: string }) {
  const [reply, setReply] = useState('')
  const messages = mockMessages[listingId] || []

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <MessageSquare size={28} className="text-slate-300 dark:text-slate-600 mb-2" />
        <p className="text-sm text-slate-500 dark:text-slate-400">No negotiation started yet</p>
        <button className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors">
          <Plus size={13} /> Start negotiation
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Pending approval banner */}
      {listingId === 'lst-002' && (
        <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-lg">
          <AlertCircle size={14} className="text-amber-500 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-amber-800 dark:text-amber-300">Your approval needed</p>
            <p className="text-xs text-amber-700 dark:text-amber-400 mt-0.5">Landlord accepted $2,350/mo with waived pet deposit.</p>
          </div>
          <div className="flex gap-1 shrink-0">
            <button className="px-2 py-1 bg-emerald-500 text-white text-[10px] font-semibold rounded">Accept</button>
            <button className="px-2 py-1 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px] font-semibold rounded">Decline</button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="space-y-2">
        {messages.map((m, i) => (
          <div key={i} className={cn('flex gap-2', m.sender === 'agent' || m.sender === 'user' ? 'flex-row' : 'flex-row-reverse')}>
            <div className={cn('w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-white text-[9px] font-bold',
              m.sender === 'agent' ? 'bg-indigo-500' : m.sender === 'user' ? 'bg-slate-500' : 'bg-emerald-500')}>
              {m.sender === 'agent' ? <Bot size={11} /> : m.sender === 'user' ? <User size={11} /> : 'L'}
            </div>
            <div className={cn('flex-1 max-w-[80%] px-3 py-2 rounded-xl text-xs leading-relaxed',
              m.sender === 'landlord'
                ? 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-tr-sm'
                : 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-900 dark:text-indigo-100 rounded-tl-sm')}>
              {m.text}
              <div className="text-[9px] text-slate-400 mt-1">{m.time}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Reply box */}
      <div className="flex gap-2 pt-1">
        <input
          value={reply}
          onChange={e => setReply(e.target.value)}
          placeholder="Send a message..."
          className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button className="p-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
          <Send size={13} />
        </button>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Modular detail dashboard — react-grid-layout
───────────────────────────────────────── */
const DEFAULT_LAYOUT: LayoutItem[] = [
  { i: 'info',         x: 0, y: 0,  w: 12, h: 18, minH: 12, minW: 4 },
  { i: 'rationale',   x: 0, y: 18, w: 6,  h: 8,  minH: 5,  minW: 3 },
  { i: 'map',         x: 6, y: 18, w: 6,  h: 11, minH: 6,  minW: 3 },
  { i: 'neighborhood', x: 0, y: 29, w: 6,  h: 11, minH: 7,  minW: 3 },
  { i: 'negotiation', x: 6, y: 29, w: 6,  h: 11, minH: 6,  minW: 3 },
]

function DetailDashboard({ listing, filteredListings }: { listing: Listing; filteredListings: Listing[] }) {
  const { dashboardModules, addDashboardModule, removeDashboardModule, setSelectedListing } = useStore()
  const { addToNegotiation, negotiationCart } = useStore()
  const [imageIdx, setImageIdx] = useState(0)
  const [addMenuOpen, setAddMenuOpen] = useState(false)
  const inCart = negotiationCart.includes(listing.id)

  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(800)

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(entries => {
      setContainerWidth(entries[0].contentRect.width)
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  const [layout, setLayout] = useState<LayoutItem[]>(DEFAULT_LAYOUT)

  const poiIcons: Record<string, React.ElementType> = {
    transit: Train, grocery: ShoppingBag, park: TreePine,
    restaurant: Coffee, food: Coffee, culture: Star,
    shopping: ShoppingBag, landmark: Star, market: ShoppingBag,
  }

  const visibleModules = MODULE_DEFS.filter(m => dashboardModules.includes(m.key))
  const hiddenModules = MODULE_DEFS.filter(m => !dashboardModules.includes(m.key))
  const visibleLayout: LayoutItem[] = layout.filter(l => dashboardModules.includes(l.i as ModuleKey))

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Module manager toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 shrink-0 bg-white dark:bg-slate-900">
        <div className="flex items-center gap-2">
          <LayoutGrid size={14} className="text-slate-400" />
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Dashboard</span>
          <span className="text-xs text-slate-400">· {visibleModules.length} modules · drag header to move · drag corner to resize</span>
        </div>
        <div className="relative">
          <button
            onClick={() => setAddMenuOpen(v => !v)}
            disabled={hiddenModules.length === 0}
            className={cn(
              'flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg border transition-colors',
              hiddenModules.length === 0
                ? 'opacity-40 cursor-not-allowed border-slate-200 dark:border-slate-700 text-slate-400'
                : 'border-indigo-300 dark:border-indigo-700 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'
            )}
          >
            <Plus size={11} /> Add module
          </button>
          {addMenuOpen && hiddenModules.length > 0 && (
            <div className="absolute right-0 top-8 w-44 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl z-20 overflow-hidden">
              {hiddenModules.map(m => (
                <button
                  key={m.key}
                  onClick={() => { addDashboardModule(m.key); setAddMenuOpen(false) }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                  <span>{m.emoji}</span>{m.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Grid area */}
      <div ref={containerRef} className="flex-1 overflow-y-auto scrollbar-thin">
        {visibleModules.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center h-full">
            <LayoutGrid size={32} className="text-slate-300 dark:text-slate-600 mb-3" />
            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">All modules removed</p>
            <p className="text-xs text-slate-400 mt-1">Click "Add module" above to restore</p>
          </div>
        ) : (
          <GridLayout
            layout={visibleLayout}
            width={containerWidth}
            gridConfig={{ cols: 12, rowHeight: 30, margin: [8, 8] as [number, number], containerPadding: [8, 8] as [number, number] }}
            dragConfig={{ handle: '.drag-handle' }}
            compactor={noCompactor}
            onLayoutChange={(newLayout: Layout) =>
              setLayout(prev => {
                const updated = new Map(Array.from(newLayout).map(l => [l.i, l]))
                return prev.map(l => updated.has(l.i) ? { ...l, ...updated.get(l.i)! } : l)
              })
            }
          >
            {visibleModules.map(({ key, label, emoji }) => (
              <div
                key={key}
                className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col"
              >
                {/* Drag handle header */}
                <div className="drag-handle flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700 cursor-grab active:cursor-grabbing shrink-0 select-none">
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 dark:text-slate-500 text-xs leading-none">⠿</span>
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">{emoji} {label}</span>
                  </div>
                  <button
                    onMouseDown={e => e.stopPropagation()}
                    onClick={() => removeDashboardModule(key)}
                    className="p-0.5 text-slate-300 hover:text-slate-500 dark:hover:text-slate-400 transition-colors rounded"
                  >
                    <X size={13} />
                  </button>
                </div>

                {/* Module content */}
                <div className="flex-1 p-3 overflow-y-auto scrollbar-thin min-h-0">

              {key === 'info' && (
                <div className="space-y-3">
                  {/* ── Image carousel (top of info) ── */}
                  <div className="relative w-full h-52 rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-700 shrink-0">
                    <img
                      src={listing.images[imageIdx]}
                      alt={listing.title}
                      className="w-full h-full object-cover"
                      onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${listing.id}${imageIdx}/600/300` }}
                    />
                    {listing.images.length > 1 && (
                      <>
                        <button onClick={() => setImageIdx(i => Math.max(0, i - 1))} disabled={imageIdx === 0}
                          className="absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 disabled:opacity-0 transition-all">
                          <ChevronLeft size={14} />
                        </button>
                        <button onClick={() => setImageIdx(i => Math.min(listing.images.length - 1, i + 1))} disabled={imageIdx === listing.images.length - 1}
                          className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 disabled:opacity-0 transition-all">
                          <ChevronRight size={14} />
                        </button>
                        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                          {listing.images.map((_, i) => (
                            <button key={i} onClick={() => setImageIdx(i)}
                              className={cn('w-1.5 h-1.5 rounded-full transition-colors', i === imageIdx ? 'bg-white' : 'bg-white/50')} />
                          ))}
                        </div>
                      </>
                    )}
                    <div className={cn('absolute top-2 left-2 flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold',
                      listing.matchType === 'perfect' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700')}>
                      <Star size={10} fill="currentColor" />{listing.matchScore}%
                    </div>
                    <div className="absolute bottom-2 right-2 text-[10px] bg-black/50 text-white rounded px-1.5 py-0.5">
                      {imageIdx + 1} / {listing.images.length}
                    </div>
                  </div>

                  {/* ── Title + price ── */}
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100">{listing.title}</h3>
                    <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5"><MapPin size={11} />{listing.address}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xl font-bold text-indigo-600 dark:text-indigo-400">
                        {formatCurrency(listing.price)}<span className="text-xs font-normal text-slate-400">/mo</span>
                      </span>
                      {listing.originalPrice && listing.originalPrice > listing.price && (
                        <span className="text-xs text-slate-400 line-through">{formatCurrency(listing.originalPrice)}</span>
                      )}
                    </div>
                  </div>

                  {/* ── Stats grid ── */}
                  <div className="grid grid-cols-4 gap-2">
                    {[
                      { label: 'Beds', value: listing.bedrooms },
                      { label: 'Bath', value: `${listing.bathrooms}` },
                      { label: 'Sqft', value: listing.sqft.toLocaleString() },
                      { label: 'Commute', value: `${listing.commuteTime}m` },
                    ].map(({ label, value }) => (
                      <div key={label} className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-2 text-center">
                        <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">{value}</div>
                        <div className="text-[10px] text-slate-400">{label}</div>
                      </div>
                    ))}
                  </div>

                  {/* ── Details table ── */}
                  <div className="space-y-1.5">
                    {[
                      { label: 'Available', value: listing.availableFrom },
                      { label: 'Lease', value: listing.leaseLength },
                      { label: 'Deposit', value: formatCurrency(listing.deposit) },
                      { label: 'Landlord', value: listing.landlord },
                      { label: 'Pets', value: listing.pets ? 'Allowed' : 'Not allowed' },
                      { label: 'Laundry', value: listing.laundry },
                      { label: 'Parking', value: listing.parking ? 'Included' : 'Not included' },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-700/50 text-xs">
                        <span className="text-slate-500">{label}</span>
                        <span className="font-medium text-slate-800 dark:text-slate-200">{value}</span>
                      </div>
                    ))}
                  </div>

                  {/* ── Tags ── */}
                  <div className="flex flex-wrap gap-1">
                    {listing.tags.map(tag => (
                      <Badge key={tag} variant="secondary" className="text-[10px] px-2 py-0.5">{tag}</Badge>
                    ))}
                  </div>

                  {/* ── Actions ── */}
                  <div className="flex gap-2">
                    <Button className="flex-1 h-8 text-xs gap-1" onClick={() => addToNegotiation(listing.id)} disabled={inCart}>
                      {inCart ? <><CheckCircle2 size={12} />In negotiation</> : <><Plus size={12} />Negotiate</>}
                    </Button>
                    <Button variant="outline" className="h-8 text-xs gap-1"><Calendar size={12} />Tour</Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8"><Bookmark size={13} /></Button>
                  </div>
                </div>
              )}

              {key === 'rationale' && (
                <div className="space-y-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Sparkles size={13} className="text-indigo-500" />
                    <span className="text-xs font-semibold text-indigo-700 dark:text-indigo-300 uppercase tracking-wide">Why this matches you</span>
                  </div>
                  <ul className="space-y-2">
                    {listing.aiRationale.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                        <CheckCircle2 size={11} className="text-emerald-500 mt-0.5 shrink-0" />{r}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs text-slate-500 dark:text-slate-400 italic leading-relaxed border-l-2 border-indigo-200 dark:border-indigo-700 pl-3">
                    {listing.aiExplanation}
                  </p>
                </div>
              )}

              {key === 'map' && (
                <MapView
                  listings={filteredListings}
                  selectedId={listing.id}
                  onSelect={setSelectedListing}
                  height="h-full"
                />
              )}

              {key === 'neighborhood' && (
                <div className="space-y-3">
                  {/* Neighborhood name */}
                  <div className="flex items-center gap-2">
                    <MapPin size={13} className="text-indigo-500 shrink-0" />
                    <span className="font-semibold text-sm text-slate-800 dark:text-slate-100">{listing.neighborhood}</span>
                  </div>

                  {/* Score cards */}
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { label: 'Safety', value: listing.safetyScore, icon: Shield, color: 'text-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
                      { label: 'Walk', value: Math.min(99, listing.safetyScore + 7), icon: Coffee, color: 'text-amber-500', bg: 'bg-amber-50 dark:bg-amber-900/20' },
                      { label: 'Transit', value: Math.min(99, listing.safetyScore - 4), icon: Train, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
                    ].map(({ label, value, icon: Icon, color, bg }) => (
                      <div key={label} className={cn('rounded-xl p-3 text-center', bg)}>
                        <Icon size={14} className={cn('mx-auto mb-1', color)} />
                        <div className={cn('text-base font-bold', color)}>{value}</div>
                        <div className="text-[10px] text-slate-400">{label} score</div>
                      </div>
                    ))}
                  </div>

                  {/* Price trend */}
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Rent trend (6 mo)</span>
                      {listing.priceTrend[listing.priceTrend.length - 1] < listing.priceTrend[0]
                        ? <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-0.5"><TrendingDown size={10} />Dropping</span>
                        : <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium">Rising</span>
                      }
                    </div>
                    <div className="flex items-end gap-0.5 h-10">
                      {listing.priceTrend.map((p, i) => {
                        const max = Math.max(...listing.priceTrend)
                        const min = Math.min(...listing.priceTrend)
                        const h = max === min ? 50 : ((p - min) / (max - min)) * 100
                        return (
                          <div key={i} className="flex-1 flex flex-col justify-end gap-0.5">
                            <div
                              className={cn('w-full rounded-sm', i === listing.priceTrend.length - 1 ? 'bg-indigo-400' : 'bg-slate-300 dark:bg-slate-600')}
                              style={{ height: `${Math.max(12, h)}%` }}
                            />
                            <span className="text-[8px] text-slate-400 text-center">{['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'][i]}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Nearby POIs */}
                  <div>
                    <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Nearby Places</p>
                    <div className="space-y-2">
                      {listing.nearbyPOIs.map(poi => {
                        const Icon = poiIcons[poi.type] || MapPin
                        return (
                          <div key={poi.name} className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                              <div className="w-6 h-6 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center shrink-0">
                                <Icon size={11} className="text-slate-400" />
                              </div>
                              {poi.name}
                            </div>
                            <span className="text-slate-400 text-[10px]">{poi.distance}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}

              {key === 'negotiation' && <NegotiationHistory listingId={listing.id} />}
                </div>
              </div>
            ))}

          </GridLayout>
        )}
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Main PanelMatch
───────────────────────────────────────── */
type SortOrder = 'price-asc' | 'price-desc'

export function PanelMatch() {
  const {
    listings, selectedListingId, setSelectedListing,
    negStatusFilter, setNegStatusFilter,
    listSidebarOpen, toggleListSidebar,
  } = useStore()

  const [sortOrder, setSortOrder] = useState<SortOrder>('price-asc')

  const filtered = (negStatusFilter === 'all'
    ? listings
    : listings.filter(l => negStatusOf(l) === negStatusFilter)
  ).slice().sort((a, b) =>
    sortOrder === 'price-asc' ? a.price - b.price : b.price - a.price
  )

  const selectedListing = filtered.find(l => l.id === selectedListingId) ?? filtered[0] ?? listings[0]

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Status filter tabs ── */}
      <div className="flex items-center gap-1 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shrink-0">
        {STATUS_FILTERS.map(({ key, label }) => {
          const count = key === 'all'
            ? listings.length
            : listings.filter(l => negStatusOf(l) === key).length
          return (
            <button
              key={key}
              onClick={() => setNegStatusFilter(key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                negStatusFilter === key
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              )}
            >
              {label}
              <span className={cn(
                'text-[10px] px-1.5 py-0.5 rounded-full font-bold',
                negStatusFilter === key
                  ? 'bg-white/25 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
              )}>
                {count}
              </span>
            </button>
          )
        })}
        <div className="flex-1" />
        <span className="text-xs text-slate-400">{filtered.length} apartments</span>
      </div>

      {/* ── Body: sidebar + detail ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* LEFT: collapsible list sidebar */}
        <aside className={cn(
          'flex flex-col border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 transition-all duration-300 shrink-0 overflow-hidden',
          listSidebarOpen ? 'w-72' : 'w-0'
        )}>
          {listSidebarOpen && (
            <>
              {/* Sidebar header */}
              <div className="flex items-center justify-between px-3 py-2.5 border-b border-slate-200 dark:border-slate-700 shrink-0">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Apartments
                </span>
                <div className="flex items-center gap-1">
                  {/* Price sort toggle */}
                  <button
                    onClick={() => setSortOrder(o => o === 'price-asc' ? 'price-desc' : 'price-asc')}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    title="Sort by price"
                  >
                    <ArrowUpDown size={11} />
                    {sortOrder === 'price-asc' ? 'Low→High' : 'High→Low'}
                  </button>
                  <button
                    onClick={toggleListSidebar}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    <PanelLeftClose size={15} />
                  </button>
                </div>
              </div>
              {/* Listing cards */}
              <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-2">
                {filtered.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center px-4">
                    <p className="text-sm text-slate-500 dark:text-slate-400">No apartments in this status</p>
                  </div>
                ) : (
                  filtered.map(l => (
                    <ListCard
                      key={l.id}
                      listing={l}
                      selected={selectedListingId === l.id}
                      onClick={() => setSelectedListing(l.id)}
                    />
                  ))
                )}
              </div>
            </>
          )}
        </aside>

        {/* Sidebar toggle when collapsed */}
        {!listSidebarOpen && (
          <button
            onClick={toggleListSidebar}
            className="flex flex-col items-center justify-center w-8 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 gap-1"
          >
            <PanelLeftOpen size={14} />
            <span className="text-[9px] writing-mode-vertical font-medium tracking-wide"
              style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}>
              Apartments
            </span>
          </button>
        )}

        {/* RIGHT: modular detail dashboard */}
        <div className="flex-1 overflow-hidden bg-slate-50 dark:bg-slate-900">
          {selectedListing ? (
            <DetailDashboard listing={selectedListing} filteredListings={filtered} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-5xl mb-4">🏠</div>
                <p className="text-sm text-slate-500 dark:text-slate-400">Select an apartment to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

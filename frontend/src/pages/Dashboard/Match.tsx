import { useState, useEffect } from 'react'
import { useMap } from 'react-leaflet'
import { GridLayout, verticalCompactor, useContainerWidth } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import {
  BedDouble, Bath, Maximize2,
  ListFilter, MessageSquare, Plus,
  Sparkles, MapPin, GripVertical, X,
  ChevronLeft, ChevronRight, LayoutGrid, Heart,
} from 'lucide-react'
import dislikeIcon from '../../assets/image/dislike.svg'
import laundryIcon from '../../assets/image/landry.svg'
import parkingIcon from '../../assets/image/parking.svg'
import petIcon from '../../assets/image/pet.svg'
import { MapContainer, TileLayer, Marker } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Fix default Leaflet marker icons broken by bundlers
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow })
import { useStore } from '../../store/useStore'
import type { Listing } from '../../types'
import { cn, formatCurrency } from '../../lib/utils'
import { listingsApi, negotiationsApi } from '../../lib/api'
import type { MessageOut } from '../../lib/api'

/* ─────────────────────────────────────────
   Types
───────────────────────────────────────── */
type NegStatusFilter = 'all' | 'not-started' | 'in-progress' | 'completed'

const STATUS_FILTERS: { key: NegStatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'not-started', label: 'Not Started' },
  { key: 'in-progress', label: 'In Progress' },
  { key: 'completed', label: 'Done' },
]

function negStatusOf(l: Listing): NegStatusFilter {
  if (!l.negotiationStatus) return 'not-started'
  if (l.negotiationStatus === 'responded' || l.negotiationStatus === 'accepted') return 'completed'
  return 'in-progress'
}

/* ─────────────────────────────────────────
   Negotiation chat (real API)
───────────────────────────────────────── */
function NegotiationChat({ listingId }: { listingId: string }) {
  const [messages, setMessages] = useState<MessageOut[]>([])
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    negotiationsApi.messages(listingId)
      .then((msgs) => { if (!cancelled) setMessages(msgs) })
      .catch(() => { /* keep empty array */ })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [listingId])

  async function handleStartNegotiation() {
    setStarting(true)
    try {
      await negotiationsApi.start(listingId)
      const msgs = await negotiationsApi.messages(listingId)
      setMessages(msgs)
    } catch {
      // ignore
    } finally {
      setStarting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-5 h-5 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <MessageSquare size={28} className="text-white/30 mb-2" />
        <p className="text-sm text-white/50">No negotiation started yet</p>
        <button
          onClick={handleStartNegotiation}
          disabled={starting}
          className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-[#6A5CFF] text-white text-xs font-medium rounded-lg hover:bg-[#5a4def] transition-colors disabled:opacity-50"
        >
          <Plus size={13} /> {starting ? 'Starting...' : 'Start negotiation'}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {messages.map((m) => {
        const time = new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        return (
          <div key={m.id} className={cn('flex', m.role === 'agent' ? 'justify-end' : 'justify-start')}>
            <div className={cn(
              'max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed',
              m.role === 'agent'
                ? 'bg-white text-gray-900 rounded-br-sm'
                : 'bg-[#A0BCE8]/40 text-white rounded-bl-sm'
            )}>
              {m.text}
              <div className="text-[10px] opacity-50 mt-1 text-right">{time}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ─────────────────────────────────────────
   Grid card (full view)
───────────────────────────────────────── */
function GridCard({ listing, selected, onClick }: {
  listing: Listing; selected: boolean; onClick: () => void
}) {
  const { removeListing, likedListings, toggleLike } = useStore()
  const isLiked = likedListings.has(listing.id)
  const [animating, setAnimating] = useState(false)
  const bedLabel = listing.bedrooms === 'Studio' ? 'Studio' : `${listing.bedrooms.replace(/\D/g, '')} beds`

  async function handleLike(e: React.MouseEvent) {
    e.stopPropagation()
    toggleLike(listing.id)
    if (!isLiked) {
      setAnimating(true)
      setTimeout(() => setAnimating(false), 500)
    }
    try {
      await listingsApi.react(listing.id, isLiked ? 'dislike' : 'like')
    } catch {
      // ignore
    }
  }

  async function handleDislike(e: React.MouseEvent) {
    e.stopPropagation()
    removeListing(listing.id)
    try {
      await listingsApi.react(listing.id, 'dislike')
    } catch {
      // ignore
    }
  }

  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white rounded-2xl overflow-hidden cursor-pointer transition-all duration-200 hover:shadow-2xl hover:-translate-y-0.5',
        selected && 'ring-2 ring-[#6A5CFF] shadow-lg shadow-[#6A5CFF]/20'
      )}
    >
      <div className="relative h-44 overflow-hidden">
        <img
          src={listing.images[0]}
          alt={listing.title}
          className="w-full h-full object-cover"
          onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${listing.id}/400/200` }}
        />
        <div className="absolute top-3 right-3 flex gap-2">
          <button
            onClick={handleLike}
            className={cn(
              'flex items-center justify-center w-8 h-8 rounded-full backdrop-blur-sm transition-all duration-200',
              isLiked ? 'bg-red-500/20' : 'bg-black/20 hover:bg-black/30'
            )}
          >
            <Heart
              size={18}
              className={cn(
                'transition-all duration-200',
                isLiked ? 'text-red-500 fill-red-500' : 'text-white',
                animating && 'animate-heart-pop'
              )}
            />
          </button>
          <button
            onClick={handleDislike}
            className="flex items-center justify-center w-8 h-8 rounded-full bg-black/20 backdrop-blur-sm hover:bg-black/30 transition-all duration-200"
          >
            <img src={dislikeIcon} alt="dislike" className="w-5 h-5 object-contain" />
          </button>
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-bold text-gray-900 text-[15px] leading-tight">{listing.title}</h3>
        <p className="text-gray-400 text-xs mt-1 leading-snug">{listing.address}</p>
        <p className="text-[#6A5CFF] font-bold text-xl mt-2">{formatCurrency(listing.price)}</p>
        <div className="border-t border-gray-100 mt-3 pt-3 flex items-center gap-1.5 text-[11px] text-gray-500">
          <BedDouble size={12} className="text-gray-400 shrink-0" />
          <span>{bedLabel}</span>
          <span className="text-gray-200 px-0.5">|</span>
          <Bath size={12} className="text-gray-400 shrink-0" />
          <span>{listing.bathrooms} baths</span>
          <span className="text-gray-200 px-0.5">|</span>
          <Maximize2 size={12} className="text-gray-400 shrink-0" />
          <span>{listing.sqft} ft²</span>
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Narrow list card (detail view sidebar)
───────────────────────────────────────── */
function ListCard({ listing, selected, onClick }: {
  listing: Listing; selected: boolean; onClick: () => void
}) {
  const { removeListing, likedListings, toggleLike } = useStore()
  const isLiked = likedListings.has(listing.id)
  const [animating, setAnimating] = useState(false)
  const bedLabel = listing.bedrooms === 'Studio' ? 'Studio' : `${listing.bedrooms.replace(/\D/g, '')} beds`

  async function handleLike(e: React.MouseEvent) {
    e.stopPropagation()
    toggleLike(listing.id)
    if (!isLiked) {
      setAnimating(true)
      setTimeout(() => setAnimating(false), 500)
    }
    try {
      await listingsApi.react(listing.id, isLiked ? 'dislike' : 'like')
    } catch {
      // ignore
    }
  }

  async function handleDislike(e: React.MouseEvent) {
    e.stopPropagation()
    removeListing(listing.id)
    try {
      await listingsApi.react(listing.id, 'dislike')
    } catch {
      // ignore
    }
  }

  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white rounded-2xl overflow-hidden cursor-pointer transition-all duration-200 hover:shadow-lg shrink-0',
        selected && 'ring-2 ring-[#6A5CFF]'
      )}
    >
      <div className="relative h-32 overflow-hidden">
        <img
          src={listing.images[0]}
          alt={listing.title}
          className="w-full h-full object-cover"
          onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${listing.id}/300/200` }}
        />
        <div className="absolute top-2 right-2 flex gap-1.5">
          <button
            onClick={handleLike}
            className={cn(
              'flex items-center justify-center w-7 h-7 rounded-full backdrop-blur-sm transition-all duration-200',
              isLiked ? 'bg-red-500/20' : 'bg-black/20 hover:bg-black/30'
            )}
          >
            <Heart
              size={14}
              className={cn(
                'transition-all duration-200',
                isLiked ? 'text-red-500 fill-red-500' : 'text-white',
                animating && 'animate-heart-pop'
              )}
            />
          </button>
          <button
            onClick={handleDislike}
            className="flex items-center justify-center w-7 h-7 rounded-full bg-black/20 backdrop-blur-sm hover:bg-black/30 transition-all duration-200"
          >
            <img src={dislikeIcon} alt="dislike" className="w-4 h-4 object-contain" />
          </button>
        </div>
      </div>
      <div className="p-3">
        <h3 className="font-bold text-gray-900 text-sm leading-tight">{listing.title}</h3>
        <p className="text-gray-400 text-[11px] mt-0.5">{listing.address}</p>
        <p className="text-[#6A5CFF] font-bold text-base mt-1">{formatCurrency(listing.price)}</p>
        <div className="border-t border-gray-100 mt-2 pt-2 flex items-center gap-1 text-[10px] text-gray-400">
          <BedDouble size={10} className="shrink-0" /><span>{bedLabel}</span>
          <span className="text-gray-200 px-0.5">|</span>
          <Bath size={10} className="shrink-0" /><span>{listing.bathrooms} baths</span>
          <span className="text-gray-200 px-0.5">|</span>
          <Maximize2 size={10} className="shrink-0" /><span>{listing.sqft} ft²</span>
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Grid layout card helpers
───────────────────────────────────────── */
type CardId = 'image' | 'rationale' | 'map' | 'neighborhood' | 'negotiation'

interface LayoutItem { i: string; x: number; y: number; w: number; h: number; minW?: number; minH?: number }

const ALL_CARD_DEFS: { id: CardId; label: string }[] = [
  { id: 'image', label: 'Image & Info' },
  { id: 'rationale', label: 'Rationale' },
  { id: 'map', label: 'Map' },
  { id: 'neighborhood', label: 'Neighborhood' },
  { id: 'negotiation', label: 'Negotiation' },
]

const DEFAULT_LAYOUT: LayoutItem[] = [
  { i: 'image', x: 0, y: 0, w: 6, h: 10, minW: 3, minH: 5 },
  { i: 'rationale', x: 6, y: 0, w: 6, h: 5, minW: 3, minH: 3 },
  { i: 'map', x: 6, y: 5, w: 6, h: 5, minW: 3, minH: 3 },
  { i: 'neighborhood', x: 0, y: 10, w: 12, h: 3, minW: 4, minH: 2 },
  { i: 'negotiation', x: 0, y: 13, w: 12, h: 5, minW: 4, minH: 3 },
]

function MapInvalidator() {
  const map = useMap()
  useEffect(() => {
    const ro = new ResizeObserver(() => map.invalidateSize())
    const el = map.getContainer().parentElement
    if (el) ro.observe(el)
    return () => ro.disconnect()
  }, [map])
  return null
}

/* ─────────────────────────────────────────
   Apartment detail view
───────────────────────────────────────── */
function AptDetail({ listing }: { listing: Listing }) {
  const { preferences } = useStore()
  const [mapCenter, setMapCenter] = useState<[number, number]>([listing.lat, listing.lng])
  const [layout, setLayout] = useState<LayoutItem[]>(DEFAULT_LAYOUT)
  const [activeCards, setActiveCards] = useState<CardId[]>(['image', 'rationale', 'map', 'neighborhood', 'negotiation'])
  const [showAddMenu, setShowAddMenu] = useState(false)
  const { containerRef, width } = useContainerWidth({ initialWidth: 800 })

  useEffect(() => {
    const loc = preferences.housing.location
    if (!loc) return
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(loc)}&limit=1`)
      .then(r => r.json())
      .then(data => { if (data[0]) setMapCenter([parseFloat(data[0].lat), parseFloat(data[0].lon)]) })
      .catch(() => { })
  }, [preferences.housing.location])

  const moveInDate = new Date(listing.availableFrom).toLocaleDateString('en-US', {
    month: 'numeric', day: 'numeric', year: 'numeric',
  })

  const amenities = [
    { label: 'On Site', icon: laundryIcon },
    { label: 'garage', icon: parkingIcon },
    { label: 'pets friendly', icon: petIcon },
  ]

  function removeCard(id: CardId) {
    setActiveCards(prev => prev.filter(c => c !== id))
    setLayout(prev => prev.filter(l => l.i !== id))
  }

  function addCard(id: CardId) {
    const def = DEFAULT_LAYOUT.find(l => l.i === id)!
    setLayout(prev => [...prev, { ...def, y: Infinity }])
    setActiveCards(prev => [...prev, id])
    setShowAddMenu(false)
  }

  const hiddenCards = ALL_CARD_DEFS.filter(c => !activeCards.includes(c.id))

  /* card header shared by every card */
  function CardHeader({ id, label, icon }: { id: CardId; label: string; icon: React.ReactNode }) {
    return (
      <div className="drag-handle flex items-center justify-between px-4 py-2.5 cursor-grab active:cursor-grabbing shrink-0 border-b border-white/10">
        <div className="flex items-center gap-2">
          <GripVertical size={14} className="text-white/30" />
          {icon}
          <span className="text-white font-semibold text-sm">{label}</span>
        </div>
        <button
          className="text-white/30 hover:text-white/70 transition-colors"
          onMouseDown={e => e.stopPropagation()}
          onClick={() => removeCard(id)}
        >
          <X size={13} />
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* ── Add card bar ── */}
      {hiddenCards.length > 0 && (
        <div className="flex items-center gap-2 px-1 pb-2 shrink-0 relative">
          <button
            onClick={() => setShowAddMenu(v => !v)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/60 hover:text-white text-xs font-medium transition-all"
          >
            <Plus size={12} /> Add card
          </button>
          {showAddMenu && (
            <div className="absolute top-full left-0 mt-1 bg-[#0F1428] border border-white/10 rounded-xl shadow-xl z-50 overflow-hidden">
              {hiddenCards.map(c => (
                <button
                  key={c.id}
                  onClick={() => addCard(c.id)}
                  className="w-full text-left px-4 py-2.5 text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors whitespace-nowrap"
                >
                  {c.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Grid ── */}
      <div ref={containerRef} className="flex-1 overflow-y-auto">
        <style>{`
          .react-resizable-handle { opacity: 0; transition: opacity 0.15s; }
          .react-grid-item:hover .react-resizable-handle { opacity: 1; }
          .react-resizable-handle-se {
            width: 18px; height: 18px; bottom: 6px; right: 6px;
            background: none; border-right: 2px solid rgba(255,255,255,0.5);
            border-bottom: 2px solid rgba(255,255,255,0.5); border-radius: 0 0 6px 0;
          }
          .react-grid-item.react-grid-placeholder { background: rgba(106,92,255,0.2); border-radius: 16px; }
        `}</style>
        <GridLayout
          layout={layout}
          width={width}
          gridConfig={{ cols: 12, rowHeight: 52, margin: [12, 12], containerPadding: [0, 0] }}
          dragConfig={{ handle: '.drag-handle' }}
          resizeConfig={{ handles: ['se'] }}
          compactor={verticalCompactor}
          onLayoutChange={(l) => setLayout([...l] as LayoutItem[])}
        >
          {/* Image & Info */}
          {activeCards.includes('image') && (
            <div key="image" className="bg-white/30 backdrop-blur-sm rounded-2xl overflow-hidden flex flex-col">
              <CardHeader id="image" label="Image & Info" icon={null} />
              <div className="relative flex-1 overflow-hidden">
                <img
                  src={listing.images[0]} alt={listing.title}
                  className="w-full h-full object-cover"
                  onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${listing.id}/800/500` }}
                />
                <div className="absolute top-5 left-5">
                  <h2 className="text-white font-bold text-3xl leading-tight drop-shadow-lg">{listing.title}</h2>
                  <p className="text-white/80 text-sm mt-1 drop-shadow">{listing.address}</p>
                </div>
              </div>
              <div className="px-5 pt-3 pb-4 flex flex-col gap-3 shrink-0">
                <div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-[#6A5CFF] font-bold text-3xl">{formatCurrency(listing.price)}</span>
                    <span className="text-white/50 text-sm font-medium">/month</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-white font-semibold text-sm">
                    <span>{listing.bedrooms}</span><span className="text-white/30">|</span>
                    <span>{listing.bathrooms} Bath</span><span className="text-white/30">|</span>
                    <span>{listing.sqft} ft</span>
                  </div>
                </div>
                <div className="border-t border-white/20 pt-3 grid grid-cols-3 divide-x divide-white/20">
                  {[
                    { label: 'Move in date', value: moveInDate },
                    { label: 'Lease Length', value: listing.leaseLength },
                    { label: 'Host Contact', value: listing.landlord },
                  ].map(({ label, value }, i) => (
                    <div key={label} className={i === 0 ? 'pr-4' : i === 1 ? 'px-4' : 'pl-4'}>
                      <div className="text-white/50 text-xs mb-1">{label}</div>
                      <div className="text-white text-sm font-medium truncate">{value}</div>
                    </div>
                  ))}
                </div>
                <div className="border-t border-white/20 pt-3 flex items-center gap-8">
                  {amenities.map(({ label, icon }) => (
                    <div key={label} className="flex items-center gap-2.5 text-white text-sm">
                      <img src={icon} alt={label} className="w-7 h-7 object-contain" />
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Rationale */}
          {activeCards.includes('rationale') && (
            <div key="rationale" className="bg-white/30 backdrop-blur-sm rounded-2xl flex flex-col overflow-hidden">
              <CardHeader id="rationale" label="Rationale" icon={<Sparkles size={13} className="text-white" />} />
              <div className="flex-1 overflow-y-auto p-5 scrollbar-thin">
                <p className="text-white/70 text-sm leading-relaxed">{listing.aiExplanation}</p>
                {listing.aiRationale.length > 0 && (
                  <ul className="mt-3 space-y-1.5">
                    {listing.aiRationale.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-white/60">
                        <span className="text-[#6A5CFF] shrink-0 mt-0.5">•</span>{r}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* Map */}
          {activeCards.includes('map') && (
            <div key="map" className="bg-white/30 backdrop-blur-sm rounded-2xl overflow-hidden flex flex-col">
              <CardHeader id="map" label="Map" icon={<MapPin size={13} className="text-white" />} />
              <div className="flex-1 overflow-hidden">
                <MapContainer
                  center={mapCenter} zoom={12}
                  scrollWheelZoom={true} zoomControl={false}
                  style={{ width: '100%', height: '100%' }}
                >
                  <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                  />
                  <Marker position={[listing.lat, listing.lng]} />
                  <MapInvalidator />
                </MapContainer>
              </div>
            </div>
          )}

          {/* Neighborhood */}
          {activeCards.includes('neighborhood') && (
            <div key="neighborhood" className="bg-white/30 backdrop-blur-sm rounded-2xl flex flex-col overflow-hidden">
              <CardHeader id="neighborhood" label="Neighborhood Info" icon={<MapPin size={13} className="text-white" />} />
              <div className="flex-1 overflow-y-auto p-5 scrollbar-thin">
                <p className="text-white/70 text-sm leading-relaxed">
                  {listing.neighborhood} is a vibrant area with easy access to transit and local amenities.
                  {listing.nearbyPOIs.length > 0 && (
                    <> Nearby highlights include {listing.nearbyPOIs.map(p => `${p.name} (${p.distance})`).join(', ')}.</>
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Negotiation */}
          {activeCards.includes('negotiation') && (
            <div key="negotiation" className="bg-white/30 backdrop-blur-sm rounded-2xl flex flex-col overflow-hidden">
              <CardHeader id="negotiation" label="Negotiation" icon={<MessageSquare size={13} className="text-white" />} />
              <div className="flex-1 overflow-y-auto p-5 scrollbar-thin">
                <NegotiationChat listingId={listing.id} />
              </div>
            </div>
          )}
        </GridLayout>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Main Match
───────────────────────────────────────── */
type SortOrder = 'price-asc' | 'price-desc'
type ViewMode = 'grid' | 'split' | 'detail'

export function Match() {
  const {
    listings, selectedListingId, setSelectedListing,
    negStatusFilter, setNegStatusFilter,
    loadListings,
  } = useStore()

  const [sortOrder, setSortOrder] = useState<SortOrder>('price-asc')
  const [view, setView] = useState<ViewMode>(selectedListingId ? 'split' : 'grid')

  useEffect(() => {
    loadListings()
  }, [loadListings])

  const filtered = (negStatusFilter === 'all'
    ? listings
    : listings.filter(l => negStatusOf(l) === negStatusFilter)
  ).slice().sort((a, b) =>
    sortOrder === 'price-asc' ? a.price - b.price : b.price - a.price
  )

  const selectedListing = listings.find(l => l.id === selectedListingId) ?? null

  // When the selected listing is removed (e.g. disliked), auto-select next or fall back to grid
  useEffect(() => {
    if (view !== 'grid' && !selectedListing) {
      if (filtered.length > 0) {
        setSelectedListing(filtered[0].id)
      } else {
        setView('grid')
      }
    }
  }, [selectedListing, view, filtered, setSelectedListing])

  function handleSelectApt(id: string) {
    setSelectedListing(id)
    if (view === 'grid') setView('split')
  }

  function handleExpand() {
    setSelectedListing(null)
    setView('grid')
  }

  function handleFoldToggle() {
    setView(v => v === 'split' ? 'detail' : 'split')
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Filter / control bar ── */}
      <div className="flex items-center gap-4 px-6 py-4 shrink-0">
        {/* Status filters */}
        <span className="text-white font-semibold text-sm whitespace-nowrap">Negotiation Progress</span>
        <div className="flex items-center gap-2">
          {STATUS_FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setNegStatusFilter(key)}
              className={cn(
                'px-4 py-1.5 rounded-full text-sm font-medium transition-all whitespace-nowrap',
                negStatusFilter === key
                  ? 'bg-[#6A5CFF] text-white shadow-lg shadow-[#6A5CFF]/30'
                  : 'bg-white/10 text-white/60 hover:bg-white/20 hover:text-white'
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        {/* Sort — only shown in grid view; split/detail has it inside the list panel */}
        {view === 'grid' && (
          <button
            onClick={() => setSortOrder(o => o === 'price-asc' ? 'price-desc' : 'price-asc')}
            className="text-white/60 hover:text-white transition-colors"
            title="Sort by price"
          >
            <ListFilter size={18} />
          </button>
        )}

      </div>

      {/* ── Content ── */}
      {view === 'grid' && (
        <div className="flex-1 overflow-y-auto scrollbar-thin px-6 pb-6">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-white/40 text-sm">No apartments in this status</p>
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-4">
              {filtered.map(l => (
                <GridCard
                  key={l.id}
                  listing={l}
                  selected={selectedListingId === l.id}
                  onClick={() => handleSelectApt(l.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {view === 'split' && selectedListing && (
        <div className="flex-1 overflow-hidden flex gap-4 px-6 pb-6">
          {/* Left panel */}
          <div className="w-64 shrink-0 bg-white/10 backdrop-blur-sm rounded-2xl flex flex-col overflow-hidden">
            {/* Panel header with icons */}
            <div className="flex items-center justify-between px-4 py-3 shrink-0">
              <button
                onClick={() => setSortOrder(o => o === 'price-asc' ? 'price-desc' : 'price-asc')}
                className="text-white/60 hover:text-white transition-colors"
              >
                <ListFilter size={18} />
              </button>
              <div className="flex items-center gap-3">
                <button onClick={handleFoldToggle} className="text-white/60 hover:text-white transition-colors" title="Fold list">
                  <ChevronLeft size={18} />
                </button>
                <button onClick={handleExpand} className="text-white/60 hover:text-white transition-colors" title="Full grid">
                  <LayoutGrid size={18} />
                </button>
              </div>
            </div>
            {/* Card list */}
            <div className="flex-1 overflow-y-auto space-y-3 px-3 pb-3 scrollbar-thin">
              {filtered.map(l => (
                <ListCard
                  key={l.id}
                  listing={l}
                  selected={selectedListingId === l.id}
                  onClick={() => setSelectedListing(l.id)}
                />
              ))}
            </div>
          </div>
          {/* Detail */}
          <AptDetail listing={selectedListing} />
        </div>
      )}

      {view === 'detail' && selectedListing && (
        <div className="flex-1 overflow-hidden px-6 pb-6 flex gap-4">
          {/* Collapsed panel — just icons */}
          <div className="shrink-0 bg-white/10 backdrop-blur-sm rounded-2xl flex flex-col items-center py-3 px-2 gap-3">
            <button onClick={handleFoldToggle} className="text-white/60 hover:text-white transition-colors" title="Unfold list">
              <ChevronRight size={18} />
            </button>
            <button onClick={handleExpand} className="text-white/60 hover:text-white transition-colors" title="Full grid">
              <LayoutGrid size={18} />
            </button>
          </div>
          <AptDetail listing={selectedListing} />
        </div>
      )}
    </div>
  )
}

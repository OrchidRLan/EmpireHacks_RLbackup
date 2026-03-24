import { useState, useEffect } from 'react'
import { BedDouble, Bath, Maximize2 } from 'lucide-react'
import bellIcon from '../../assets/image/bell.svg'
import { useStore } from '../../store/useStore'
import { cn } from '../../lib/utils'
import { formatCurrency } from '../../lib/utils'
import type { Listing, Notification } from '../../types'
import logosImg from '../../assets/image/logos.png'
import googleCalendarImg from '../../assets/image/googlecalendar.png'
import successIcon from '../../assets/image/success.svg'
import errorIcon from '../../assets/image/error.svg'
import workingIcon from '../../assets/image/working.svg'

/* ─────────────────────────────────────────
   Stage types
───────────────────────────────────────── */
type StageId = 'search' | 'filter' | 'negotiate' | 'notify'

const STAGES: { id: StageId; label: string }[] = [
  { id: 'search',    label: 'Searching' },
  { id: 'filter',    label: 'Filtering' },
  { id: 'negotiate', label: 'Negotiating' },
  { id: 'notify',    label: 'Notification' },
]

/* ─────────────────────────────────────────
   Mock data
───────────────────────────────────────── */
const IMAGE_LOGS = [
  {
    id: 1, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: 'The space appears well-lit with large windows and neutral tones. The furniture layout is minimal and modern, suggesting a clean and comfortable environment.',
    tags: ['modern', 'spacious', 'industrial'], pass: true,
  },
  {
    id: 2, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: 'The space appears well-lit with large windows and neutral tones. The furniture layout is minimal and modern, suggesting a clean and comfortable environment.',
    tags: ['modern', 'spacious', 'industrial'], pass: false,
  },
  {
    id: 3, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: 'The space appears well-lit with large windows and neutral tones. The furniture layout is minimal and modern, suggesting a clean and comfortable environment.',
    tags: ['modern', 'spacious', 'industrial'], pass: true,
  },
  {
    id: 4, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: 'The space appears well-lit with large windows and neutral tones. The furniture layout is minimal and modern, suggesting a clean and comfortable environment.',
    tags: ['modern', 'spacious', 'industrial'], pass: true,
  },
]

const FILTER_LOGS = [
  {
    id: 1, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: "This apartment was selected because it matches the user's core objective preferences: it is within budget, located in the preferred area, and meets the required bedroom count. It also includes high-priority amenities such as in-unit laundry and parking, making it a strong overall fit.",
    pass: true,
  },
  {
    id: 2, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: "This apartment was selected because it matches the user's core objective preferences: it is within budget, located in the preferred area, and meets the required bedroom count. It also includes high-priority amenities such as in-unit laundry and parking, making it a strong overall fit.",
    pass: false,
  },
  {
    id: 3, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: "This apartment was selected because it matches the user's core objective preferences: it is within budget, located in the preferred area, and meets the required bedroom count. It also includes high-priority amenities such as in-unit laundry and parking, making it a strong overall fit.",
    pass: true,
  },
  {
    id: 4, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    desc: "This apartment was selected because it matches the user's core objective preferences: it is within budget, located in the preferred area, and meets the required bedroom count. It also includes high-priority amenities such as in-unit laundry and parking, making it a strong overall fit.",
    pass: true,
  },
]

const NEG_LOGS = [
  {
    id: 1, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    thinking: "The listing price is slightly above similar apartments in the area, and the user prioritizes saving money. Since the apartment meets most other requirements, it is reasonable to request a small price adjustment while showing strong interest.",
    message: "Hi, I'm reaching out regarding this apartment. I'm very interested and would love to learn more about the lease terms and availability.",
  },
  {
    id: 2, time: '09:00', apt: 'lst-002 · 2300 Mission St',
    thinking: "The listing price is slightly above similar apartments in the area, and the user prioritizes saving money. Since the apartment meets most other requirements, it is reasonable to request a small price adjustment while showing strong interest.",
    message: "Hi, I'm reaching out regarding this apartment. I'm very interested and would love to learn more about the lease terms and availability.",
  },
]

const PREF_BUBBLES = [
  { label: 'cozy',     color: 'bg-teal-400',   w: 76,  h: 76  },
  { label: 'quiet',    color: 'bg-indigo-400',  w: 95,  h: 95  },
  { label: 'relaxing', color: 'bg-indigo-500',  w: 115, h: 115 },
  { label: 'Warm',     color: 'bg-blue-400',    w: 72,  h: 72  },
  { label: 'peaceful', color: 'bg-indigo-300',  w: 88,  h: 88  },
  { label: 'homey',    color: 'bg-indigo-700',  w: 102, h: 102 },
]


/* ─────────────────────────────────────────
   Timeline
───────────────────────────────────────── */
function Timeline({ active, onSelect }: { active: StageId; onSelect: (s: StageId) => void }) {
  return (
    <div className="relative flex items-start justify-between px-24 pt-5 pb-1 shrink-0">
      {/* connecting line — vertically centered in the 44px dot area */}
      <div className="absolute left-24 right-24 h-px bg-white/40" style={{ top: 'calc(20px + 22px)' }} />

      {STAGES.map((stage) => {
        const isActive = stage.id === active
        return (
          <button
            key={stage.id}
            onClick={() => onSelect(stage.id)}
            className="relative z-10 flex flex-col items-center gap-2"
          >
            {/* dot */}
            <div className="h-11 flex items-center justify-center">
              {isActive ? (
                <div className="w-11 h-11 rounded-full bg-[#5B4FEA] flex items-center justify-center shadow-lg shadow-indigo-500/40">
                  <div className="w-3 h-3 rounded-full bg-white" />
                </div>
              ) : (
                <div className="w-3 h-3 rounded-full bg-white/50" />
              )}
            </div>
            {/* label */}
            <span className={cn(
              'text-sm whitespace-nowrap',
              isActive ? 'text-white font-bold' : 'text-white/50'
            )}>
              {stage.label}
            </span>
          </button>
        )
      })}
    </div>
  )
}

/* ─────────────────────────────────────────
   Shared: log panel wrapper
───────────────────────────────────────── */
function LogPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex-1 bg-white/10 backdrop-blur-sm rounded-2xl flex flex-col overflow-hidden min-h-0">
      {/* header */}
      <div className="flex items-center gap-3 px-6 py-5 shrink-0 border-b border-white/10">
        <div className="w-5 h-8 bg-blue-500 rounded-sm shrink-0" />
        <h2 className="text-white font-bold text-xl">{title}</h2>
      </div>
      {/* entries */}
      <div className="flex-1 overflow-y-auto divide-y divide-white/10">
        {children}
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Shared: left sidebar card
───────────────────────────────────────── */
function SideCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-72 shrink-0 bg-white/30 backdrop-blur-sm rounded-2xl overflow-hidden flex flex-col">
      {children}
    </div>
  )
}

/* ─────────────────────────────────────────
   Shared: status icon (emoji-style)
───────────────────────────────────────── */
function StatusIcon({ status }: { status: 'success' | 'error' | 'working' }) {
  const src = status === 'success' ? successIcon : status === 'error' ? errorIcon : workingIcon
  return <img src={src} alt={status} className="w-7 h-7 shrink-0" />
}

/* ─────────────────────────────────────────
   1. Searching stage
───────────────────────────────────────── */
interface ImageLogEntry {
  id: string | number
  time: string
  apt: string
  desc: string
  tags: string[]
  pass: boolean
}

function SearchView({ imageLogs }: { imageLogs: ImageLogEntry[] }) {
  return (
    <div className="flex gap-4 h-full">
      {/* Left: two stacked cards */}
      <div className="w-72 shrink-0 flex flex-col gap-4">
        {/* Card 1 — stat */}
        <div className="bg-white/30 backdrop-blur-sm rounded-2xl p-6">
          <div className="text-8xl font-bold text-white leading-none tracking-tight">2801</div>
          <div className="text-white text-base font-medium mt-3">Apartments Found</div>
        </div>

        {/* Card 2 — sources */}
        <div className="flex-1 bg-white/30 backdrop-blur-sm rounded-2xl p-6 flex flex-col">
          <div className="text-white font-bold text-xl mb-4 text-center">Sources</div>
          <div className="flex-1 flex items-center justify-center">
            <img src={logosImg} alt="Sources" className="w-4/5 object-contain" />
          </div>
        </div>
      </div>

      <LogPanel title="Image Analysis Agent Log">
        {imageLogs.map(log => (
          <div key={log.id} className="px-6 py-4 flex items-start gap-3">
            <span className="text-xs text-white/40 font-mono shrink-0 mt-1">{log.time}</span>
            <StatusIcon status={log.pass ? 'success' : 'error'} />
            <div className="flex-1 min-w-0">
              <p className="text-white/80 text-sm leading-relaxed">
                <span className="text-white font-medium">{log.apt}: </span>
                {log.desc}
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                {log.tags.map(t => (
                  <span key={t} className="text-sm px-4 py-1 rounded-full bg-white/15 text-indigo-200 font-medium">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </LogPanel>
    </div>
  )
}

/* ─────────────────────────────────────────
   2. Filtering stage
───────────────────────────────────────── */
interface FilterLogEntry {
  id: string | number
  time: string
  apt: string
  desc: string
  pass: boolean
}

function FilterView({ filterLogs }: { filterLogs: FilterLogEntry[] }) {
  return (
    <div className="flex gap-4 h-full">
      <SideCard>
        <div className="p-6 flex flex-col h-full gap-5">
          <p className="text-white font-bold text-lg leading-snug">
            We are taking your subjective preferences in to consideration
          </p>

          {/* Bubble cloud */}
          <div className="flex-1 relative">
            <div
              className="absolute inset-0 flex flex-wrap content-center justify-center gap-2"
              style={{ alignContent: 'center' }}
            >
              {PREF_BUBBLES.map(b => (
                <div
                  key={b.label}
                  className={cn('rounded-full flex items-center justify-center text-white font-medium shrink-0', b.color)}
                  style={{ width: b.w, height: b.h, fontSize: b.w > 90 ? 14 : 12 }}
                >
                  {b.label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </SideCard>

      <LogPanel title="Filtering Agent Log">
        {filterLogs.map(log => (
          <div key={log.id} className="px-6 py-4 flex items-start gap-3">
            <span className="text-3xl shrink-0 leading-none select-none">{log.pass ? '😊' : '😟'}</span>
            <span className="text-xs text-white/40 font-mono shrink-0 mt-1">{log.time}</span>
            <p className="text-white/80 text-sm leading-relaxed flex-1 min-w-0">
              <span className="text-white font-medium">{log.apt}: </span>
              {log.desc}
            </p>
          </div>
        ))}
      </LogPanel>
    </div>
  )
}

/* ─────────────────────────────────────────
   3. Negotiation stage
───────────────────────────────────────── */
function NegotiateAptCard({ listing, onClick }: { listing: Listing; onClick: () => void }) {
  const bedNum = listing.bedrooms.replace(/\D/g, '')
  return (
    <button
      className="w-full flex rounded-2xl overflow-hidden bg-white shadow-sm text-left hover:shadow-md transition-shadow"
      onClick={onClick}
    >
      {/* Photo */}
      <img
        src={listing.images[0]}
        alt={listing.title}
        className="w-32 shrink-0 object-cover"
        onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${listing.id}/200/200` }}
      />
      {/* Info */}
      <div className="flex-1 min-w-0 p-4 flex flex-col justify-between">
        <div>
          <div className="text-gray-900 font-bold text-base leading-tight">{listing.title}</div>
          <div className="text-gray-400 text-xs mt-1">{listing.address}</div>
          <div className="text-[#6A5CFF] font-bold text-xl mt-2">{formatCurrency(listing.price)}</div>
        </div>
        <div className="flex items-center gap-2 text-gray-400 text-xs mt-3">
          <BedDouble size={13} className="shrink-0" />
          <span>{bedNum} beds</span>
          <span className="text-gray-200">|</span>
          <Bath size={13} className="shrink-0" />
          <span>{listing.bathrooms} baths</span>
          <span className="text-gray-200">|</span>
          <Maximize2 size={13} className="shrink-0" />
          <span>{listing.sqft} ft²</span>
        </div>
      </div>
    </button>
  )
}

interface NegLogEntry {
  id: string | number
  time: string
  apt: string
  thinking: string
  message: string
}

function NegotiateView({ listings, negLogs }: { listings: Listing[]; negLogs: NegLogEntry[] }) {
  const { setSelectedListing, setTopTab } = useStore()
  const inProgress = listings.filter(l =>
    l.negotiationStatus === 'negotiating' || l.negotiationStatus === 'pending'
  )
  const displayList = inProgress.length > 0 ? inProgress : listings.slice(0, 4)

  function handleAptClick(id: string) {
    setSelectedListing(id)
    setTopTab('match')
  }

  return (
    <div className="flex gap-4 h-full">
      <div className="w-[420px] shrink-0 bg-white/30 backdrop-blur-sm rounded-2xl p-5 flex flex-col gap-4 overflow-hidden">
        <div className="flex items-center justify-center gap-4 py-2">
          <span className="text-8xl font-bold text-white leading-none">{inProgress.length || 4}</span>
          <span className="text-white text-2xl font-semibold">In Progress</span>
        </div>
        <div className="flex-1 overflow-y-auto space-y-3">
          {displayList.map(l => (
            <NegotiateAptCard key={l.id} listing={l} onClick={() => handleAptClick(l.id)} />
          ))}
        </div>
      </div>

      <LogPanel title="Negotiation Agent Log">
        {negLogs.map(log => (
          <div key={log.id} className="px-6 py-5 space-y-3">
            <p className="text-xs text-white/50 font-mono">{log.time}</p>
            <p className="text-white/70 text-sm leading-relaxed">
              <span className="font-medium text-white">{log.apt}: </span>
              {log.thinking}
            </p>
            {log.message && (
              <div className="rounded-2xl rounded-tl-sm px-4 py-3" style={{ backgroundColor: '#A0BCE8' }}>
                <p className="text-black text-sm leading-relaxed">{log.message}</p>
              </div>
            )}
          </div>
        ))}
      </LogPanel>
    </div>
  )
}

/* ─────────────────────────────────────────
   4. Notification stage
───────────────────────────────────────── */
function NotifyView({ notifications }: { notifications: Notification[] }) {
  const t = (ts: string) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* top bar */}
      <div className="bg-white/30 backdrop-blur-sm rounded-2xl px-8 py-5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <span className="text-8xl font-bold text-white leading-none">3</span>
          <span className="text-white/80 text-lg font-medium">Appointment Arranged</span>
        </div>
        <a href="https://calendar.google.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-5 py-3 rounded-xl bg-[#5B4FEA] text-white font-semibold text-sm hover:bg-[#4A3FD9] transition-colors no-underline">
          <img src={googleCalendarImg} alt="Google Calendar" className="w-8 h-8 shrink-0" />
          <span className="leading-tight">Go Check<br />Google Calendar</span>
        </a>
      </div>

      {/* notification log */}
      <div className="flex-1 bg-white/10 backdrop-blur-sm rounded-2xl flex flex-col overflow-hidden min-h-0">
        <div className="flex items-center gap-3 px-6 py-5 shrink-0 border-b border-white/10">
          <div className="w-5 h-8 bg-blue-500 rounded-sm shrink-0" />
          <h2 className="text-white font-bold text-xl">Notification Log</h2>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-white/10">
          {notifications.map(n => (
            <div key={n.id} className="px-6 py-4 flex items-start gap-4">
              <img src={bellIcon} alt="bell" className="w-6 h-6 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-white/40 font-mono shrink-0">{t(n.timestamp)}</span>
                  <span className="text-white font-semibold text-sm">{n.title}</span>
                </div>
                <p className="text-white/60 text-sm mt-0.5">{n.message}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Main AgentLog
───────────────────────────────────────── */
export function AgentLog() {
  const { listings, notifications, agentStatus, loadAgentLogs, loadAgentStatus } = useStore()
  const [activeStage, setActiveStage] = useState<StageId>('filter')

  useEffect(() => {
    loadAgentStatus()
    loadAgentLogs()
  }, [loadAgentStatus, loadAgentLogs])

  // Build stage-specific log arrays from real logs, falling back to mock data
  const realSearchLogs = agentStatus.logs.filter(l => l.phase === 'search')
  const realFilterLogs = agentStatus.logs.filter(l => l.phase === 'filter')
  const realNegLogs    = agentStatus.logs.filter(l => l.phase === 'negotiate' || l.phase === 'negotiation')

  const searchImageLogs = realSearchLogs.length > 0
    ? realSearchLogs.map(l => ({
        id: l.id,
        time: new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        apt: l.message.split(':')[0] ?? l.message,
        desc: l.message,
        tags: [] as string[],
        pass: l.level !== 'error',
      }))
    : IMAGE_LOGS

  const filterDisplayLogs = realFilterLogs.length > 0
    ? realFilterLogs.map(l => ({
        id: l.id,
        time: new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        apt: l.message.split(':')[0] ?? l.message,
        desc: l.message,
        pass: l.level !== 'error',
      }))
    : FILTER_LOGS

  const negDisplayLogs = realNegLogs.length > 0
    ? realNegLogs.map(l => ({
        id: l.id,
        time: new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        apt: l.message.split(':')[0] ?? l.message,
        thinking: l.message,
        message: '',
      }))
    : NEG_LOGS

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <Timeline active={activeStage} onSelect={setActiveStage} />

      <div className="flex-1 overflow-hidden px-6 pb-6 pt-4 min-h-0">
        {activeStage === 'search'    && <SearchView imageLogs={searchImageLogs} />}
        {activeStage === 'filter'    && <FilterView filterLogs={filterDisplayLogs} />}
        {activeStage === 'negotiate' && <NegotiateView listings={listings} negLogs={negDisplayLogs} />}
        {activeStage === 'notify'    && <NotifyView notifications={notifications} />}
      </div>
    </div>
  )
}

import { useState } from 'react'
import {
  Search, Filter, MessageSquare, Bell, Play, Pause,
  CheckCircle2, Clock, Info, ChevronDown,
  Bot, Settings, Globe, Brain, Send, Image,
  ArrowRight, Building2, Sparkles,
  TrendingDown, XCircle,
} from 'lucide-react'
import { useStore } from '../../store/useStore'
import { Button } from '../../components/ui/button'
import { Slider } from '../../components/ui/slider'
import { Switch } from '../../components/ui/switch'
import { cn } from '../../lib/utils'

/* ─────────────────────────────────────────
   Mock data — Search stage
───────────────────────────────────────── */
const SOURCES = [
  { name: 'Zillow', icon: '🏠', count: 512, type: 'API' },
  { name: 'Apartments.com', icon: '🏢', count: 341, type: 'API' },
  { name: 'Craigslist SF', icon: '📋', count: 218, type: 'Scraper' },
  { name: 'Realtor.com', icon: '🔑', count: 169, type: 'API' },
]

const IMAGE_LOGS = [
  { id: 1, time: '09:00:01', apt: 'lst-001 · 450 Brannan St', tags: ['modern', 'spacious', 'industrial'], done: true },
  { id: 2, time: '09:00:03', apt: 'lst-002 · 2300 Mission St', tags: ['cozy', 'warm-toned', 'vintage'], done: true },
  { id: 3, time: '09:00:06', apt: 'lst-003 · 501 Fell St', tags: ['bright', 'minimal', 'airy'], done: true },
  { id: 4, time: '09:00:09', apt: 'lst-004 · 88 King St', tags: ['luxury', 'high-ceiling', 'contemporary'], done: true },
  { id: 5, time: '09:00:12', apt: 'lst-005 · 340 Fremont St', tags: ['dated', 'compact', 'functional'], done: true },
  { id: 6, time: '09:10:01', apt: 'lst-New-A · 222 2nd St', tags: ['open-plan', 'new-build'], done: false },
]

/* ─────────────────────────────────────────
   Mock data — Filtering stage
───────────────────────────────────────── */
type FilterEntry =
  | { kind: 'rule'; id: number; time: string; rule: string; input: string; output: string }
  | { kind: 'apt'; id: number; time: string; apt: string; reason: string; result: 'in' | 'out' }

const FILTER_LOGS: FilterEntry[] = [
  { kind: 'rule', id: 1, time: '09:00:07', rule: 'Budget $1,500–$3,500/mo', input: '1,240', output: '847' },
  { kind: 'rule', id: 2, time: '09:00:09', rule: 'Commute ≤30 min (transit)', input: '847', output: '312' },
  { kind: 'apt',  id: 3, time: '09:00:10', apt: 'lst-021', reason: '$4,200/mo exceeds budget by $700', result: 'out' },
  { kind: 'apt',  id: 4, time: '09:00:11', apt: 'lst-034', reason: '45 min commute — exceeds 30 min limit', result: 'out' },
  { kind: 'apt',  id: 5, time: '09:00:11', apt: 'lst-002 · Mission St', reason: '18 min BART, $2,400/mo, pet-friendly ✓', result: 'in' },
  { kind: 'apt',  id: 6, time: '09:00:12', apt: 'lst-003 · Fell St', reason: 'Studio, 12 min bus, recent $50 price drop', result: 'in' },
  { kind: 'rule', id: 7, time: '09:00:13', rule: 'Match score > 70%', input: '312', output: '7' },
]

const PREF_KEYWORDS = ['$1,500–$3,500', 'SF Bay Area', '≤30 min commute', 'Pets OK', 'In-unit laundry', '1–2 BR']

/* ─────────────────────────────────────────
   Mock data — Negotiation stage
───────────────────────────────────────── */
type NegEntry = {
  id: number
  time: string
  apt: string
  landlord: string
  thinking?: string
  message: string
  type: 'sent' | 'received'
  outcome?: string
}

const NEG_LOGS: NegEntry[] = [
  {
    id: 1, time: '09:01:02', apt: 'lst-003 · 501 Fell St', landlord: 'Hayes Valley Partners',
    thinking: 'Price dropped to $1,950 — well within $3,500 budget. Focus on lease flexibility and move-in date.',
    message: 'Hi! My client is highly interested in the studio at 501 Fell. Would you consider a 12-month lease starting April 1st?',
    type: 'sent',
  },
  {
    id: 2, time: '09:01:45', apt: 'lst-003 · 501 Fell St', landlord: 'Hayes Valley Partners',
    message: "Thanks for reaching out! We just dropped the price to $1,950. Is your client flexible on move-in?",
    type: 'received',
  },
  {
    id: 3, time: '09:02:10', apt: 'lst-002 · 2300 Mission St', landlord: 'Rosa M. Herrera',
    thinking: 'Asking $2,400/mo. Target $2,350. Waived pet deposit (~$500) is a better alternative to a direct discount.',
    message: 'Hello Rosa! My client loves the 1BR at 2300 Mission. Given a 12-month lease, could we discuss the pet deposit?',
    type: 'sent',
  },
  {
    id: 4, time: '09:03:30', apt: 'lst-002 · 2300 Mission St', landlord: 'Rosa M. Herrera',
    message: "I can do $2,350/mo with one month's deposit — and I'll waive the pet deposit if they're responsible.",
    type: 'received',
    outcome: '$2,350/mo · pet fee waived · saved ~$500',
  },
]

/* ─────────────────────────────────────────
   Shared: stage header
───────────────────────────────────────── */
function StageHeader({
  step, icon: Icon, label, sub, statLabel, statValue, color,
}: {
  step: number
  icon: React.ElementType
  label: string
  sub: string
  statLabel: string
  statValue: string
  color: 'indigo' | 'sky' | 'violet' | 'amber'
}) {
  const palette = {
    indigo: { bg: 'bg-indigo-50 dark:bg-indigo-900/20', border: 'border-indigo-200 dark:border-indigo-800', icon: 'bg-indigo-500', text: 'text-indigo-700 dark:text-indigo-300', badge: 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300' },
    sky:    { bg: 'bg-sky-50 dark:bg-sky-900/20',       border: 'border-sky-200 dark:border-sky-800',       icon: 'bg-sky-500',    text: 'text-sky-700 dark:text-sky-300',       badge: 'bg-sky-100 dark:bg-sky-900/50 text-sky-700 dark:text-sky-300' },
    violet: { bg: 'bg-violet-50 dark:bg-violet-900/20', border: 'border-violet-200 dark:border-violet-800', icon: 'bg-violet-500', text: 'text-violet-700 dark:text-violet-300', badge: 'bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300' },
    amber:  { bg: 'bg-amber-50 dark:bg-amber-900/20',   border: 'border-amber-200 dark:border-amber-800',   icon: 'bg-amber-500',  text: 'text-amber-700 dark:text-amber-300',   badge: 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300' },
  }[color]

  return (
    <div className={cn('shrink-0 px-4 py-3 border-b', palette.bg, palette.border)}>
      <div className="flex items-center gap-2.5">
        <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center shrink-0', palette.icon)}>
          <Icon size={14} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={cn('text-[10px] font-bold', palette.text)}>STEP {step}</span>
            <span className="font-semibold text-sm text-slate-800 dark:text-slate-100">{label}</span>
          </div>
          <p className="text-[10px] text-slate-400 leading-none mt-0.5">{sub}</p>
        </div>
        <div className={cn('shrink-0 px-2 py-0.5 rounded-full text-[10px] font-bold', palette.badge)}>
          {statValue}
          <span className="font-normal ml-0.5 opacity-70">{statLabel}</span>
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Shared: log timestamp
───────────────────────────────────────── */
function Ts({ v }: { v: string }) {
  return <span className="text-[9px] text-slate-400 font-mono shrink-0 mt-px">{v.slice(0, 5)}</span>
}

/* ─────────────────────────────────────────
   1. Search Stage
───────────────────────────────────────── */
function SearchStage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StageHeader
        step={1} icon={Search} label="Search" sub="Data collection &amp; ingestion"
        statLabel=" apts" statValue="1,240" color="indigo"
      />
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-3">

        {/* Data coverage */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Data Coverage</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Scanned', value: '1,240', sub: 'active listings', color: 'text-indigo-600 dark:text-indigo-400' },
              { label: 'New today', value: '+38', sub: 'since last scan', color: 'text-emerald-600 dark:text-emerald-400' },
              { label: 'Updated', value: '91', sub: 'price changes', color: 'text-amber-600 dark:text-amber-400' },
              { label: 'Removed', value: '14', sub: 'no longer listed', color: 'text-red-500' },
            ].map(({ label, value, sub, color }) => (
              <div key={label} className="bg-slate-50 dark:bg-slate-700/40 rounded-lg p-2">
                <div className={cn('text-lg font-bold leading-tight', color)}>{value}</div>
                <div className="text-[10px] font-medium text-slate-600 dark:text-slate-300 leading-tight">{label}</div>
                <div className="text-[9px] text-slate-400 leading-tight">{sub}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Sources */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Globe size={11} className="text-slate-400" />
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Sources</p>
          </div>
          <div className="space-y-1.5">
            {SOURCES.map(s => (
              <div key={s.name} className="flex items-center gap-2">
                <span className="text-sm">{s.icon}</span>
                <span className="flex-1 text-xs text-slate-700 dark:text-slate-300 font-medium">{s.name}</span>
                <span className={cn(
                  'text-[9px] px-1.5 py-0.5 rounded-full font-medium',
                  s.type === 'API' ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400' : 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400'
                )}>{s.type}</span>
                <span className="text-[10px] text-slate-400 w-10 text-right">{s.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Image Analysis Agent Log */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
            <Image size={11} className="text-indigo-500" />
            <p className="text-[10px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Image Analysis Agent</p>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {IMAGE_LOGS.map(log => (
              <div key={log.id} className="px-3 py-2">
                <div className="flex items-start gap-1.5 mb-1">
                  <Ts v={log.time} />
                  {log.done
                    ? <CheckCircle2 size={10} className="text-emerald-500 mt-0.5 shrink-0" />
                    : <Clock size={10} className="text-amber-400 mt-0.5 shrink-0 animate-pulse" />
                  }
                  <span className="text-[10px] text-slate-600 dark:text-slate-400 leading-tight font-medium">{log.apt}</span>
                </div>
                <div className="flex flex-wrap gap-1 pl-8">
                  {log.tags.map(tag => (
                    <span key={tag} className="text-[9px] px-1.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-medium">{tag}</span>
                  ))}
                  {!log.done && <span className="text-[9px] text-amber-500 animate-pulse">analyzing…</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   2. Filtering Stage
───────────────────────────────────────── */
function FilteringStage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StageHeader
        step={2} icon={Filter} label="Filtering" sub="Preference-based screening"
        statLabel=" passed" statValue="7" color="sky"
      />
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-3">

        {/* Preference status */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <div className="flex items-start gap-1.5 mb-2.5">
            <Sparkles size={11} className="text-sky-500 mt-0.5 shrink-0" />
            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed italic">
              Taking your preferences into consideration…
            </p>
          </div>
          <div className="flex flex-wrap gap-1">
            {PREF_KEYWORDS.map(kw => (
              <span key={kw} className="text-[9px] px-2 py-0.5 rounded-full bg-sky-50 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 font-medium border border-sky-200 dark:border-sky-700">{kw}</span>
            ))}
          </div>
        </div>

        {/* Filter log */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
            <Filter size={11} className="text-sky-500" />
            <p className="text-[10px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Filtering Log</p>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {FILTER_LOGS.map(entry => (
              <div key={entry.id} className="px-3 py-2">
                {entry.kind === 'rule' ? (
                  <div>
                    <div className="flex items-center gap-1.5">
                      <Ts v={entry.time} />
                      <Info size={9} className="text-sky-400 shrink-0" />
                      <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-300">{entry.rule}</span>
                    </div>
                    <div className="flex items-center gap-1 pl-8 mt-0.5">
                      <span className="text-[9px] text-slate-400">{entry.input}</span>
                      <ArrowRight size={8} className="text-slate-300" />
                      <span className="text-[9px] font-bold text-sky-600 dark:text-sky-400">{entry.output}</span>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-1.5">
                    <Ts v={entry.time} />
                    {entry.result === 'in'
                      ? <CheckCircle2 size={10} className="text-emerald-500 mt-0.5 shrink-0" />
                      : <XCircle size={10} className="text-red-400 mt-0.5 shrink-0" />
                    }
                    <div>
                      <span className={cn(
                        'text-[10px] font-semibold',
                        entry.result === 'in' ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                      )}>
                        {entry.result === 'in' ? '✓ Selected · ' : '✗ Filtered · '}{entry.apt}
                      </span>
                      <p className="text-[9px] text-slate-400 leading-tight mt-0.5">{entry.reason}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   3. Negotiation Stage
───────────────────────────────────────── */
function NegotiationStage() {
  const [expandThinking, setExpandThinking] = useState<number | null>(null)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StageHeader
        step={3} icon={MessageSquare} label="Negotiation" sub="Automated landlord outreach"
        statLabel=" active" statValue="3" color="violet"
      />
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-3">

        {/* Overview stats */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Overview</p>
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'Ongoing', value: '3', color: 'text-violet-600 dark:text-violet-400' },
              { label: 'Success', value: '87%', color: 'text-emerald-600 dark:text-emerald-400' },
              { label: 'Avg. reply', value: '41m', color: 'text-slate-600 dark:text-slate-300' },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-slate-50 dark:bg-slate-700/40 rounded-lg p-2 text-center">
                <div className={cn('text-base font-bold', color)}>{value}</div>
                <div className="text-[9px] text-slate-400">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Negotiation log */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
            <MessageSquare size={11} className="text-violet-500" />
            <p className="text-[10px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Negotiation Log</p>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {NEG_LOGS.map(entry => (
              <div key={entry.id} className="p-3 space-y-1.5">
                {/* Header */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Ts v={entry.time} />
                  <Building2 size={9} className="text-slate-400 shrink-0" />
                  <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 leading-tight">{entry.apt}</span>
                </div>
                <div className="text-[9px] text-slate-400">Landlord: {entry.landlord}</div>

                {/* Thinking (collapsible) */}
                {entry.thinking && (
                  <button
                    onClick={() => setExpandThinking(expandThinking === entry.id ? null : entry.id)}
                    className="w-full flex items-start gap-1.5 text-left"
                  >
                    <Brain size={9} className="text-violet-400 mt-0.5 shrink-0" />
                    <span className={cn(
                      'text-[9px] text-violet-600 dark:text-violet-400 italic leading-relaxed',
                      expandThinking !== entry.id && 'line-clamp-1'
                    )}>
                      {entry.thinking}
                    </span>
                  </button>
                )}

                {/* Message bubble */}
                <div className={cn(
                  'rounded-xl px-2.5 py-2 text-[10px] leading-relaxed',
                  entry.type === 'sent'
                    ? 'bg-violet-50 dark:bg-violet-900/30 text-violet-900 dark:text-violet-100 rounded-tl-sm'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-tr-sm'
                )}>
                  <div className="flex items-center gap-1 mb-0.5 opacity-60">
                    {entry.type === 'sent'
                      ? <><Send size={8} /><span>Agent sent</span></>
                      : <><MessageSquare size={8} /><span>Landlord replied</span></>
                    }
                  </div>
                  {entry.message}
                </div>

                {/* Outcome badge */}
                {entry.outcome && (
                  <div className="flex items-center gap-1 pt-0.5">
                    <CheckCircle2 size={10} className="text-emerald-500 shrink-0" />
                    <span className="text-[9px] font-semibold text-emerald-700 dark:text-emerald-400">{entry.outcome}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   4. Notification Stage
───────────────────────────────────────── */
function NotificationStage() {
  const { notifications } = useStore()

  const iconFor = (type: string) => {
    if (type === 'Landlord replies') return { icon: MessageSquare, color: 'text-violet-500', bg: 'bg-violet-50 dark:bg-violet-900/30' }
    if (type === 'Price drops') return { icon: TrendingDown, color: 'text-amber-500', bg: 'bg-amber-50 dark:bg-amber-900/30' }
    if (type === 'New matches') return { icon: Sparkles, color: 'text-indigo-500', bg: 'bg-indigo-50 dark:bg-indigo-900/30' }
    return { icon: Bell, color: 'text-slate-400', bg: 'bg-slate-100 dark:bg-slate-700' }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StageHeader
        step={4} icon={Bell} label="Notification" sub="User communication"
        statLabel=" unread" statValue={String(notifications.filter(n => !n.read).length)} color="amber"
      />
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-3">

        {/* Summary pills */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Summary</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Delivered', value: '13', color: 'text-emerald-600 dark:text-emerald-400' },
              { label: 'Unread', value: String(notifications.filter(n => !n.read).length), color: 'text-amber-600 dark:text-amber-400' },
              { label: 'Channels', value: '2', color: 'text-slate-600 dark:text-slate-300' },
              { label: 'Events', value: '4', color: 'text-indigo-600 dark:text-indigo-400' },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-slate-50 dark:bg-slate-700/40 rounded-lg p-2">
                <div className={cn('text-base font-bold', color)}>{value}</div>
                <div className="text-[9px] text-slate-400">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Notification list */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
            <Bell size={11} className="text-amber-500" />
            <p className="text-[10px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Notification Log</p>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {notifications.map(n => {
              const { icon: Icon, color, bg } = iconFor(n.type)
              const t = new Date(n.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              return (
                <div key={n.id} className={cn('p-3 flex items-start gap-2.5', !n.read && 'bg-amber-50/40 dark:bg-amber-900/10')}>
                  <div className={cn('w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5', bg)}>
                    <Icon size={11} className={color} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-1">
                      <p className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 leading-tight">{n.title}</p>
                      {!n.read && <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-amber-500 mt-1" />}
                    </div>
                    <p className="text-[9px] text-slate-400 mt-0.5 leading-relaxed">{n.message}</p>
                    <p className="text-[9px] text-slate-300 dark:text-slate-600 mt-1 font-mono">{t}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   Stage id type + palette (shared)
───────────────────────────────────────── */
type StageId = 'search' | 'filter' | 'negotiate' | 'notify'

const STAGES: { id: StageId; label: string; icon: React.ElementType; color: 'indigo' | 'sky' | 'violet' | 'amber' }[] = [
  { id: 'search',    label: 'Search',       icon: Search,         color: 'indigo' },
  { id: 'filter',    label: 'Filtering',    icon: Filter,         color: 'sky'    },
  { id: 'negotiate', label: 'Negotiation',  icon: MessageSquare,  color: 'violet' },
  { id: 'notify',    label: 'Notification', icon: Bell,           color: 'amber'  },
]

const PALETTE = {
  indigo: { pill: 'bg-indigo-500 text-white', ring: 'ring-2 ring-indigo-400 dark:ring-indigo-500', glow: 'shadow-indigo-100 dark:shadow-indigo-900/50' },
  sky:    { pill: 'bg-sky-500 text-white',    ring: 'ring-2 ring-sky-400 dark:ring-sky-500',       glow: 'shadow-sky-100 dark:shadow-sky-900/50'     },
  violet: { pill: 'bg-violet-500 text-white', ring: 'ring-2 ring-violet-400 dark:ring-violet-500', glow: 'shadow-violet-100 dark:shadow-violet-900/50'},
  amber:  { pill: 'bg-amber-500 text-white',  ring: 'ring-2 ring-amber-400 dark:ring-amber-500',   glow: 'shadow-amber-100 dark:shadow-amber-900/50'  },
}

/* ─────────────────────────────────────────
   Pipeline connector bar — interactive tabs
───────────────────────────────────────── */
function PipelineBar({
  currentPhase, selected, onSelect,
}: {
  currentPhase: string
  selected: StageId | null
  onSelect: (id: StageId) => void
}) {
  const runningIdx = STAGES.findIndex(s => currentPhase.startsWith(s.id.slice(0, 4)))
  const effectiveRunning = runningIdx === -1 ? 1 : runningIdx

  return (
    <div className="shrink-0 flex items-center justify-center gap-0 px-6 py-2 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
      {STAGES.map((stage, i) => {
        const Icon = stage.icon
        const isRunning = i === effectiveRunning
        const isDone = i < effectiveRunning
        const isSelected = selected === stage.id
        return (
          <div key={stage.id} className="flex items-center">
            <button
              onClick={() => onSelect(stage.id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all duration-150',
                isSelected
                  ? PALETTE[stage.color].pill + ' shadow-md scale-105'
                  : isRunning
                  ? PALETTE[stage.color].pill + ' opacity-70'
                  : isDone
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 hover:opacity-80'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              )}
            >
              {isDone && !isSelected
                ? <CheckCircle2 size={11} />
                : <Icon size={11} className={isRunning && !isSelected ? 'opacity-70' : ''} />
              }
              {stage.label}
              {isRunning && !isSelected && <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60 animate-pulse" />}
            </button>
            {i < STAGES.length - 1 && (
              <ArrowRight size={12} className="mx-1 text-slate-300 dark:text-slate-600" />
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ─────────────────────────────────────────
   Main PanelAgent
───────────────────────────────────────── */
export function PanelAgent() {
  const { agentStatus, toggleAgent, preferences, updateNegotiation } = useStore()
  const [showConfig, setShowConfig] = useState(false)
  const [selectedStage, setSelectedStage] = useState<StageId | null>(null)

  function handleSelectStage(id: StageId) {
    setSelectedStage(prev => prev === id ? null : id)
  }

  // Column visibility: all visible, but selected one is highlighted, others dimmed
  function colClass(id: StageId) {
    if (!selectedStage) return 'transition-all duration-200'
    const color = STAGES.find(s => s.id === id)!.color
    return selectedStage === id
      ? cn('transition-all duration-200 shadow-lg', PALETTE[color].ring, PALETTE[color].glow)
      : 'transition-all duration-200 opacity-40'
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">

      {/* ── Agent control bar ── */}
      <div className="shrink-0 flex items-center gap-3 px-4 py-2 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
        <div className={cn(
          'flex items-center gap-2 flex-1 px-3 py-1.5 rounded-xl border text-xs font-medium',
          agentStatus.isRunning
            ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
            : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-400'
        )}>
          <span className={cn('w-2 h-2 rounded-full shrink-0', agentStatus.isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400')} />
          <Bot size={12} />
          <span className={agentStatus.isRunning ? '' : 'text-slate-400'}>
            {agentStatus.isRunning ? 'Running' : 'Paused'}
          </span>
          <span className="ml-auto flex items-center gap-3 text-[10px] opacity-70">
            <span>{agentStatus.matchesFound} matches found</span>
            <span>{agentStatus.negotiationsActive} negotiating</span>
            <span>{agentStatus.toursScheduled} tour{agentStatus.toursScheduled !== 1 ? 's' : ''} scheduled</span>
          </span>
        </div>
        <Button
          variant={agentStatus.isRunning ? 'outline' : 'default'}
          size="sm"
          onClick={toggleAgent}
          className="gap-1.5 shrink-0 h-8 text-xs"
        >
          {agentStatus.isRunning ? <><Pause size={12} />Pause</> : <><Play size={12} />Resume</>}
        </Button>
      </div>

      {/* ── Pipeline bar — clickable tabs ── */}
      <PipelineBar
        currentPhase={agentStatus.phase}
        selected={selectedStage}
        onSelect={handleSelectStage}
      />

      {/* ── 4-column pipeline (main content) ── */}
      <div className="flex-1 overflow-hidden grid grid-cols-4 divide-x divide-slate-200 dark:divide-slate-700">
        <div className={cn('h-full overflow-hidden', colClass('search'))}><SearchStage /></div>
        <div className={cn('h-full overflow-hidden', colClass('filter'))}><FilteringStage /></div>
        <div className={cn('h-full overflow-hidden', colClass('negotiate'))}><NegotiationStage /></div>
        <div className={cn('h-full overflow-hidden', colClass('notify'))}><NotificationStage /></div>
      </div>

      {/* ── Agent config (collapsible footer) ── */}
      <div className="shrink-0 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setShowConfig(v => !v)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Settings size={13} className="text-slate-400" />
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Agent Configuration</span>
          </div>
          <ChevronDown size={13} className={cn('text-slate-400 transition-transform', showConfig && 'rotate-180')} />
        </button>

        {showConfig && (
          <div className="px-4 pb-4 grid grid-cols-2 gap-4 border-t border-slate-100 dark:border-slate-700 pt-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs text-slate-600 dark:text-slate-400">Max follow-ups per landlord</label>
                <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">{preferences.negotiation.maxFollowUps}</span>
              </div>
              <Slider
                min={1} max={10} step={1}
                value={[preferences.negotiation.maxFollowUps]}
                onValueChange={([v]) => updateNegotiation({ maxFollowUps: v })}
              />
            </div>
            <div className="space-y-2">
              {([
                { key: 'canScheduleTours' as const, label: 'Auto-schedule tours' },
                { key: 'canSubmitApplications' as const, label: 'Auto-submit applications' },
                { key: 'canConfirmLeaseTerms' as const, label: 'Auto-confirm lease terms' },
              ]).map(({ key, label }) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-xs text-slate-600 dark:text-slate-400">{label}</span>
                  <Switch
                    checked={preferences.negotiation[key]}
                    onCheckedChange={v => updateNegotiation({ [key]: v })}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

    </div>
  )
}

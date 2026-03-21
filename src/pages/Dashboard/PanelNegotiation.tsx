import { useState } from 'react'
import {
  MessageSquare, Clock, CheckCircle2, XCircle,
  Send, ChevronDown, ChevronUp, Bot, AlertCircle,
  User, Sparkles, RefreshCw,
} from 'lucide-react'
import { useStore } from '../../store/useStore'
import type { Listing, NegotiationStatus } from '../../types'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { cn, formatCurrency } from '../../lib/utils'

const negotiationStatusConfig: Record<
  NegotiationStatus,
  { label: string; variant: 'default' | 'success' | 'warning' | 'destructive' | 'secondary'; icon: React.ElementType }
> = {
  pending: { label: 'Pending', variant: 'warning', icon: Clock },
  negotiating: { label: 'Active', variant: 'default', icon: RefreshCw },
  responded: { label: 'Replied', variant: 'success', icon: MessageSquare },
  accepted: { label: 'Accepted', variant: 'success', icon: CheckCircle2 },
  rejected: { label: 'Rejected', variant: 'destructive', icon: XCircle },
}

interface MessageThread {
  listingId: string
  messages: {
    id: string
    sender: 'agent' | 'landlord' | 'user'
    text: string
    timestamp: string
    isAISuggestion?: boolean
  }[]
  pendingApproval?: {
    type: string
    description: string
    action: string
  }
}

const mockThreads: MessageThread[] = [
  {
    listingId: 'lst-002',
    messages: [
      {
        id: 'm1',
        sender: 'agent',
        text: 'Hi Rosa, I\'m reaching out on behalf of a highly qualified tenant interested in your 1BR at 2300 Mission St. They\'ve been pre-screened with excellent rental history and stable income at 4x the rent. Would you be open to a brief chat about availability and terms?',
        timestamp: '2026-03-21T08:00:00',
      },
      {
        id: 'm2',
        sender: 'landlord',
        text: 'Hi! Yes, the unit is available April 1st. We\'re asking $2,400/mo with a $4,800 deposit. No large dogs, but small pets are fine with a $500 deposit.',
        timestamp: '2026-03-21T09:00:00',
      },
      {
        id: 'm3',
        sender: 'agent',
        text: 'Thank you for the quick response! My client is very interested. Given they\'re looking at a 12-month lease with potential renewal, would you consider $2,350/mo? They\'re also flexible on move-in if that helps.',
        timestamp: '2026-03-21T09:02:00',
      },
      {
        id: 'm4',
        sender: 'landlord',
        text: 'I can do $2,350 with the standard deposit of $2,350 (one month). I\'ll also waive the pet deposit if they take good care of the place. When can they view?',
        timestamp: '2026-03-21T09:03:30',
      },
    ],
    pendingApproval: {
      type: 'counter-offer',
      description: 'Landlord accepted $2,350/mo with waived pet deposit. Ready to confirm terms.',
      action: 'Confirm terms',
    },
  },
  {
    listingId: 'lst-003',
    messages: [
      {
        id: 'm5',
        sender: 'agent',
        text: 'Hello Hayes Valley Partners team, I have a client interested in the studio at 501 Fell St listed at $1,950. They are a young professional, non-smoker, and looking for a 12-month lease starting April 15th. Can we discuss the terms?',
        timestamp: '2026-03-21T08:30:00',
      },
      {
        id: 'm6',
        sender: 'landlord',
        text: 'We\'d be happy to discuss. The unit was recently renovated. Would your client be able to do a showing this week?',
        timestamp: '2026-03-21T09:01:45',
      },
    ],
  },
]

function NegotiationCard({
  listing,
  thread,
}: {
  listing: Listing
  thread?: MessageThread
}) {
  const { removeFromNegotiation } = useStore()
  const [expanded, setExpanded] = useState(listing.negotiationStatus === 'responded')
  const [replyText, setReplyText] = useState('')

  const statusCfg = listing.negotiationStatus
    ? negotiationStatusConfig[listing.negotiationStatus]
    : negotiationStatusConfig['pending']

  const StatusIcon = statusCfg.icon

  const aiSuggestions = [
    'Accept the $2,350 offer — it\'s within your budget and the waived pet deposit saves ~$500',
    'Counter-offer at $2,300 — landlord seems motivated',
    'Request 14-month lease for additional stability',
  ]

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-750 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-slate-100 dark:bg-slate-700">
          <img
            src={listing.images[0]}
            alt={listing.title}
            className="w-full h-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${listing.id}/100/100`
            }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100 truncate">
            {listing.title}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {formatCurrency(listing.price)}/mo · {listing.neighborhood}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={statusCfg.variant}>
            <StatusIcon size={10} />
            {statusCfg.label}
          </Badge>
          {expanded ? (
            <ChevronUp size={16} className="text-slate-400" />
          ) : (
            <ChevronDown size={16} className="text-slate-400" />
          )}
        </div>
      </div>

      {expanded && thread && (
        <div className="border-t border-slate-100 dark:border-slate-700">
          {/* Messages */}
          <div className="p-4 space-y-3 max-h-64 overflow-y-auto scrollbar-thin">
            {thread.messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  'flex gap-2.5',
                  msg.sender === 'agent' || msg.sender === 'user'
                    ? 'flex-row-reverse'
                    : 'flex-row'
                )}
              >
                <div
                  className={cn(
                    'w-7 h-7 rounded-full flex items-center justify-center shrink-0',
                    msg.sender === 'agent'
                      ? 'bg-indigo-100 dark:bg-indigo-900/50'
                      : msg.sender === 'landlord'
                      ? 'bg-slate-100 dark:bg-slate-700'
                      : 'bg-emerald-100 dark:bg-emerald-900/50'
                  )}
                >
                  {msg.sender === 'agent' ? (
                    <Bot size={13} className="text-indigo-600 dark:text-indigo-400" />
                  ) : msg.sender === 'landlord' ? (
                    <User size={13} className="text-slate-500" />
                  ) : (
                    <User size={13} className="text-emerald-600" />
                  )}
                </div>
                <div className={cn('max-w-[75%]', msg.sender !== 'landlord' && 'items-end flex flex-col')}>
                  <div
                    className={cn(
                      'rounded-xl px-3 py-2 text-xs leading-relaxed',
                      msg.sender === 'agent'
                        ? 'bg-indigo-600 text-white rounded-tr-sm'
                        : msg.sender === 'landlord'
                        ? 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-tl-sm'
                        : 'bg-emerald-500 text-white rounded-tr-sm'
                    )}
                  >
                    {msg.text}
                  </div>
                  <span className="text-[10px] text-slate-400 mt-0.5 px-1">
                    {msg.sender === 'agent' ? 'AI Agent' : msg.sender === 'landlord' ? 'Landlord' : 'You'} ·{' '}
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Pending Approval */}
          {thread.pendingApproval && (
            <div className="mx-4 mb-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800">
              <div className="flex items-start gap-2">
                <AlertCircle size={14} className="text-amber-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">
                    Your approval needed
                  </p>
                  <p className="text-xs text-amber-600 dark:text-amber-400/80">
                    {thread.pendingApproval.description}
                  </p>
                </div>
              </div>
              <div className="flex gap-2 mt-3">
                <Button size="sm" variant="success" className="flex-1 text-xs h-7">
                  <CheckCircle2 size={12} />
                  Accept
                </Button>
                <Button size="sm" variant="outline" className="flex-1 text-xs h-7">
                  Counter
                </Button>
                <Button size="sm" variant="destructive" className="text-xs h-7 px-2">
                  <XCircle size={12} />
                </Button>
              </div>
            </div>
          )}

          {/* AI Suggestions */}
          <div className="mx-4 mb-3 p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl border border-indigo-100 dark:border-indigo-800">
            <div className="flex items-center gap-1.5 mb-2">
              <Sparkles size={12} className="text-indigo-500" />
              <span className="text-xs font-semibold text-indigo-700 dark:text-indigo-300">
                AI Suggestions
              </span>
            </div>
            <div className="space-y-1.5">
              {aiSuggestions.slice(0, 2).map((s, i) => (
                <button
                  key={i}
                  className="w-full text-left text-xs text-indigo-600 dark:text-indigo-400 bg-white dark:bg-slate-800 rounded-lg px-2.5 py-2 border border-indigo-100 dark:border-indigo-800 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Reply box */}
          <div className="px-4 pb-4">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Send a message or instruction to agent..."
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                className="flex-1 px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <Button size="sm" className="h-8 px-3">
                <Send size={13} />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Remove button */}
      <div className="px-4 pb-3 flex justify-end">
        <button
          onClick={() => removeFromNegotiation(listing.id)}
          className="text-xs text-red-400 hover:text-red-500 transition-colors"
        >
          Remove from negotiation
        </button>
      </div>
    </div>
  )
}

export function PanelNegotiation() {
  const { listings, negotiationCart, agentStatus } = useStore()
  const cartListings = listings.filter((l) => negotiationCart.includes(l.id))

  const stats = [
    { label: 'In negotiation', value: cartListings.length, color: 'text-indigo-600 dark:text-indigo-400' },
    { label: 'Active responses', value: cartListings.filter((l) => l.negotiationStatus === 'responded').length, color: 'text-emerald-600 dark:text-emerald-400' },
    { label: 'Pending approval', value: cartListings.filter((l) => l.negotiationStatus === 'responded').length, color: 'text-amber-600 dark:text-amber-400' },
  ]

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4">
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Negotiation Center</h2>
          <div className={cn(
            'flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-full',
            agentStatus.isRunning
              ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400'
              : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
          )}>
            <Bot size={13} />
            {agentStatus.currentAction}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {stats.map(({ label, value, color }) => (
            <div
              key={label}
              className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3 text-center"
            >
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-slate-400 mt-0.5">{label}</div>
            </div>
          ))}
        </div>

        {/* Negotiation cards */}
        {cartListings.length === 0 ? (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-8 text-center">
            <div className="text-4xl mb-3">💬</div>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
              No properties in negotiation
            </p>
            <p className="text-xs text-slate-400">
              Add listings from the Match panel to start negotiating
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {cartListings.map((listing) => {
              const thread = mockThreads.find((t) => t.listingId === listing.id)
              return (
                <NegotiationCard key={listing.id} listing={listing} thread={thread} />
              )
            })}
          </div>
        )}

        {/* Approval Center */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center gap-2">
            <AlertCircle size={15} className="text-amber-500" />
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Approval Center
            </h3>
            <Badge variant="warning" className="ml-auto">1 pending</Badge>
          </div>
          <div className="p-4">
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                    2300 Mission St — Lease Terms
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Landlord agreed to $2,350/mo with waived pet deposit. Ready to confirm.
                  </p>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <Button size="sm" variant="success" className="h-7 px-2 text-xs">
                    <CheckCircle2 size={12} />
                    OK
                  </Button>
                  <Button size="sm" variant="destructive" className="h-7 px-2 text-xs">
                    <XCircle size={12} />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

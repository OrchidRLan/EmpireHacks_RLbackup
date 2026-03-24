import { X, Home, MessageSquare, Bell, Check } from 'lucide-react'
import { useState } from 'react'
import { useStore } from '../../store/useStore'
import { Slider } from '../ui/slider'
import { Switch } from '../ui/switch'
import { cn, formatCurrency } from '../../lib/utils'
import type {
  BedroomType, Amenity, TransportMode,
  NegotiableItem, NegotiationGoal, AgentTone,
  NotificationChannel, NotificationEvent, NotificationFrequency,
} from '../../types'

/* ── Reusable primitives ── */
function Chip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-3 py-1.5 rounded-full text-xs font-medium border transition-all',
        selected
          ? 'bg-indigo-600 text-white border-indigo-600'
          : 'bg-zinc-900 text-slate-600 dark:text-slate-300 border-zinc-700 hover:border-indigo-300'
      )}
    >
      {label}
    </button>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</label>
      {children}
    </div>
  )
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-zinc-700 rounded-xl overflow-hidden">
      <div className="px-4 py-2.5 bg-zinc-800/60 border-b border-zinc-700">
        <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{title}</h4>
      </div>
      <div className="p-4 space-y-4 bg-zinc-900">{children}</div>
    </div>
  )
}

/* ── Tab contents ── */
function HousingTab() {
  const { preferences, updateHousing } = useStore()
  const { housing } = preferences
  const beds: BedroomType[] = ['Studio', '1BR', '2BR', '3BR+']
  const amenities: { label: Amenity; emoji: string }[] = [
    { label: 'Hardwood floors', emoji: '🪵' },
    { label: 'Dishwasher', emoji: '🍽️' },
    { label: 'Air conditioning', emoji: '❄️' },
    { label: 'Balcony', emoji: '🏙️' },
    { label: 'Pool', emoji: '🏊' },
    { label: 'Gym', emoji: '💪' },
  ]
  const transports: { mode: TransportMode; label: string }[] = [
    { mode: 'Drive', label: '🚗 Drive' },
    { mode: 'Transit', label: '🚇 Transit' },
    { mode: 'Bike', label: '🚲 Bike' },
  ]

  const toggleBed = (b: BedroomType) => {
    const next = housing.bedrooms.includes(b) ? housing.bedrooms.filter(x => x !== b) : [...housing.bedrooms, b]
    updateHousing({ bedrooms: next })
  }
  const toggleAmenity = (a: Amenity) => {
    const next = housing.amenities.includes(a) ? housing.amenities.filter(x => x !== a) : [...housing.amenities, a]
    updateHousing({ amenities: next })
  }
  const toggleTransport = (t: TransportMode) => {
    const next = housing.transportModes.includes(t) ? housing.transportModes.filter(x => x !== t) : [...housing.transportModes, t]
    updateHousing({ transportModes: next })
  }

  return (
    <div className="space-y-4">
      <SectionCard title="Basic">
        <Field label="Bedrooms">
          <div className="flex flex-wrap gap-1.5">
            {beds.map(b => <Chip key={b} label={b} selected={housing.bedrooms.includes(b)} onClick={() => toggleBed(b)} />)}
          </div>
        </Field>
        <Field label="Monthly budget">
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-500">
              <span>{formatCurrency(housing.budgetMin)}</span>
              <span className="font-semibold text-indigo-600 dark:text-indigo-400">{formatCurrency(housing.budgetMax)}</span>
            </div>
            <Slider
              min={500} max={8000} step={50}
              value={[housing.budgetMin, housing.budgetMax]}
              onValueChange={([min, max]) => updateHousing({ budgetMin: min, budgetMax: max })}
            />
          </div>
        </Field>
        <Field label="Location">
          <input
            type="text"
            value={housing.location}
            onChange={e => updateHousing({ location: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-700 bg-zinc-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </Field>
      </SectionCard>

      <SectionCard title="Commute">
        <Field label="Work / school address">
          <input
            type="text"
            value={housing.commuteAddress}
            onChange={e => updateHousing({ commuteAddress: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-700 bg-zinc-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </Field>
        <Field label="Transport mode">
          <div className="flex gap-1.5">
            {transports.map(({ mode, label }) => (
              <Chip key={mode} label={label} selected={housing.transportModes.includes(mode)} onClick={() => toggleTransport(mode)} />
            ))}
          </div>
        </Field>
        <Field label={`Max commute — ${housing.maxCommuteTime} min`}>
          <Slider
            min={5} max={90} step={5}
            value={[housing.maxCommuteTime]}
            onValueChange={([v]) => updateHousing({ maxCommuteTime: v })}
          />
        </Field>
      </SectionCard>

      <SectionCard title="Amenities">
        <div className="flex flex-wrap gap-1.5">
          {amenities.map(({ label, emoji }) => (
            <Chip
              key={label}
              label={`${emoji} ${label}`}
              selected={housing.amenities.includes(label)}
              onClick={() => toggleAmenity(label)}
            />
          ))}
        </div>
        <Field label="Pets">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-700 dark:text-slate-300">Pet-friendly required</span>
            <Switch checked={!!housing.pets} onCheckedChange={v => updateHousing({ pets: v })} />
          </div>
        </Field>
      </SectionCard>
    </div>
  )
}

function NegotiationTab() {
  const { preferences, updateNegotiation } = useStore()
  const { negotiation } = preferences

  const items: NegotiableItem[] = ['Rent', 'Move-in date', 'Lease length', 'Deposit', 'Parking fee', 'Pet fee', 'Utilities', 'Promotions']
  const goals: { goal: NegotiationGoal; label: string }[] = [
    { goal: 'Lowest price', label: '💰 Lowest price' },
    { goal: 'Best value', label: '⚖️ Best value' },
    { goal: 'Fastest approval', label: '🏃 Fastest' },
    { goal: 'Flexible move-in', label: '📅 Flexible' },
    { goal: 'Lowest upfront cost', label: '💾 Low upfront' },
  ]
  const tones: { tone: AgentTone; emoji: string }[] = [
    { tone: 'Polite', emoji: '🕊️' },
    { tone: 'Professional', emoji: '💼' },
    { tone: 'Assertive', emoji: '💪' },
    { tone: 'Flexible', emoji: '🔄' },
  ]

  const toggleItem = (item: NegotiableItem) => {
    const next = negotiation.negotiableItems.includes(item)
      ? negotiation.negotiableItems.filter(x => x !== item)
      : [...negotiation.negotiableItems, item]
    updateNegotiation({ negotiableItems: next })
  }

  return (
    <div className="space-y-4">
      <SectionCard title="Enable">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">AI Negotiation</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Let the agent negotiate on your behalf</p>
          </div>
          <Switch checked={negotiation.enabled} onCheckedChange={v => updateNegotiation({ enabled: v })} />
        </div>
      </SectionCard>

      <div className={cn('space-y-4', !negotiation.enabled && 'opacity-40 pointer-events-none')}>
        <SectionCard title="What can be negotiated">
          <div className="flex flex-wrap gap-1.5">
            {items.map(item => (
              <Chip key={item} label={item} selected={negotiation.negotiableItems.includes(item)} onClick={() => toggleItem(item)} />
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Goal">
          <div className="flex flex-wrap gap-1.5">
            {goals.map(({ goal, label }) => (
              <Chip key={goal} label={label} selected={negotiation.goal === goal} onClick={() => updateNegotiation({ goal })} />
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Limits">
          <div className="grid grid-cols-2 gap-3">
            {[
              { key: 'idealRent' as const, label: 'Ideal rent ($)' },
              { key: 'absoluteMaxRent' as const, label: 'Max rent ($)' },
              { key: 'maxDeposit' as const, label: 'Max deposit ($)' },
            ].map(({ key, label }) => (
              <Field key={key} label={label}>
                <input
                  type="number"
                  value={negotiation[key] as number}
                  onChange={e => updateNegotiation({ [key]: Number(e.target.value) })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-700 bg-zinc-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </Field>
            ))}
          </div>
          <Field label={`Lease length — ${negotiation.leaseLengthMin}–${negotiation.leaseLengthMax} months`}>
            <Slider
              min={1} max={36} step={1}
              value={[negotiation.leaseLengthMin, negotiation.leaseLengthMax]}
              onValueChange={([min, max]) => updateNegotiation({ leaseLengthMin: min, leaseLengthMax: max })}
            />
          </Field>
        </SectionCard>

        <SectionCard title="Agent tone">
          <div className="grid grid-cols-4 gap-2">
            {tones.map(({ tone, emoji }) => (
              <button
                key={tone}
                onClick={() => updateNegotiation({ agentTone: tone })}
                className={cn(
                  'flex flex-col items-center gap-1 p-2 rounded-lg border text-xs font-medium transition-all',
                  negotiation.agentTone === tone
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                    : 'border-zinc-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                )}
              >
                <span className="text-lg">{emoji}</span>
                {tone}
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Permissions">
          {([
            { key: 'canScheduleTours' as const, label: 'Schedule tours' },
            { key: 'canSubmitApplications' as const, label: 'Submit applications' },
            { key: 'canConfirmLeaseTerms' as const, label: 'Confirm lease terms' },
          ]).map(({ key, label }) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm text-slate-700 dark:text-slate-300">{label}</span>
              <Switch checked={negotiation[key]} onCheckedChange={v => updateNegotiation({ [key]: v })} />
            </div>
          ))}
        </SectionCard>
      </div>
    </div>
  )
}

function NotificationsTab() {
  const { preferences, updateNotifications } = useStore()
  const { notifications } = preferences

  const channels: { channel: NotificationChannel; emoji: string }[] = [
    { channel: 'Email', emoji: '📧' },
    { channel: 'SMS', emoji: '💬' },
    { channel: 'Push', emoji: '📱' },
    { channel: 'WhatsApp', emoji: '💚' },
    { channel: 'In-app', emoji: '🖥️' },
  ]
  const events: NotificationEvent[] = [
    'New matches', 'Price drops', 'Landlord replies',
    'Negotiation updates', 'Tour scheduled', 'Application updates',
    'Documents required', 'Lease offers',
  ]
  const freqs: { freq: NotificationFrequency; label: string }[] = [
    { freq: 'Real-time', label: '⚡ Real-time' },
    { freq: 'Daily', label: '☀️ Daily digest' },
    { freq: 'Twice daily', label: '🔔 Twice daily' },
    { freq: 'Weekly', label: '📅 Weekly' },
  ]

  const toggleChannel = (ch: NotificationChannel) => {
    const next = notifications.channels.includes(ch)
      ? notifications.channels.filter(x => x !== ch)
      : [...notifications.channels, ch]
    updateNotifications({ channels: next })
  }
  const toggleEvent = (ev: NotificationEvent) => {
    const next = notifications.events.includes(ev)
      ? notifications.events.filter(x => x !== ev)
      : [...notifications.events, ev]
    updateNotifications({ events: next })
  }

  return (
    <div className="space-y-4">
      <SectionCard title="Channels">
        <div className="space-y-2">
          {channels.map(({ channel, emoji }) => (
            <div key={channel} className="flex items-center justify-between">
              <span className="text-sm text-slate-700 dark:text-slate-300">{emoji} {channel}</span>
              <Switch checked={notifications.channels.includes(channel)} onCheckedChange={() => toggleChannel(channel)} />
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Notify me about">
        <div className="flex flex-wrap gap-1.5">
          {events.map(ev => (
            <Chip key={ev} label={ev} selected={notifications.events.includes(ev)} onClick={() => toggleEvent(ev)} />
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Frequency">
        <div className="grid grid-cols-2 gap-2">
          {freqs.map(({ freq, label }) => (
            <button
              key={freq}
              onClick={() => updateNotifications({ frequency: freq })}
              className={cn(
                'px-3 py-2 rounded-lg border text-xs font-medium text-left transition-all',
                notifications.frequency === freq
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                  : 'border-zinc-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Thresholds">
        <Field label={`Price drop alert — ${notifications.priceDropThreshold}%`}>
          <Slider
            min={1} max={30} step={1}
            value={[notifications.priceDropThreshold]}
            onValueChange={([v]) => updateNotifications({ priceDropThreshold: v })}
          />
        </Field>
        <Field label={`Min match score — ${notifications.matchScoreThreshold}%`}>
          <Slider
            min={50} max={100} step={5}
            value={[notifications.matchScoreThreshold]}
            onValueChange={([v]) => updateNotifications({ matchScoreThreshold: v })}
          />
        </Field>
      </SectionCard>

      <SectionCard title="Quiet hours">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Start">
            <input type="time" value={notifications.quietHoursStart}
              onChange={e => updateNotifications({ quietHoursStart: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-700 bg-zinc-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </Field>
          <Field label="End">
            <input type="time" value={notifications.quietHoursEnd}
              onChange={e => updateNotifications({ quietHoursEnd: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-700 bg-zinc-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </Field>
        </div>
      </SectionCard>
    </div>
  )
}

/* ── Modal shell ── */
const TABS = [
  { key: 'housing' as const, icon: Home, label: 'Housing' },
  { key: 'negotiation' as const, icon: MessageSquare, label: 'Negotiation' },
  { key: 'notifications' as const, icon: Bell, label: 'Notifications' },
]

export function PreferencesModal() {
  const { prefModalOpen, prefModalTab, setPrefModal } = useStore()
  const [saved, setSaved] = useState(false)

  if (!prefModalOpen) return null

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => { setSaved(false); setPrefModal(false) }, 900)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={() => setPrefModal(false)}
      />

      {/* Modal */}
      <div className="relative w-full max-w-xl bg-zinc-900 rounded-2xl shadow-2xl border border-zinc-700 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-700 shrink-0">
          <h2 className="font-bold text-slate-900 dark:text-slate-100">Preferences</h2>
          <button
            onClick={() => setPrefModal(false)}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-zinc-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex px-5 pt-3 gap-1 shrink-0">
          {TABS.map(({ key, icon: Icon, label }) => (
            <button
              key={key}
              onClick={() => setPrefModal(true, key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all',
                prefModalTab === key
                  ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
              )}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-4">
          {prefModalTab === 'housing' && <HousingTab />}
          {prefModalTab === 'negotiation' && <NegotiationTab />}
          {prefModalTab === 'notifications' && <NotificationsTab />}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-zinc-700 shrink-0">
          <button
            onClick={() => setPrefModal(false)}
            className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all',
              saved ? 'bg-emerald-500' : 'bg-indigo-600 hover:bg-indigo-700'
            )}
          >
            {saved ? <><Check size={14} /> Saved!</> : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

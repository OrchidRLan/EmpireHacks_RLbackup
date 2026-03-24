import { useState } from 'react'
import { useStore } from '../../store/useStore'
import type {
  BedroomType, Amenity, MoveInUrgency, TransportMode,
  NegotiableItem, NegotiationGoal, AgentTone,
  NotificationChannel, NotificationEvent, NotificationFrequency,
} from '../../types'

/* ══════════════════════════════════════════════
   Shared primitives
══════════════════════════════════════════════ */

function Chip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return <button className={`ob-chip${selected ? ' ob-selected' : ''}`} onClick={onClick}>{label}</button>
}

function RadioCard({
  icon, label, sub, selected, onClick,
}: { icon: string; label: string; sub?: string; selected: boolean; onClick: () => void }) {
  return (
    <button className={`ob-radio-card${selected ? ' ob-selected' : ''}`} onClick={onClick}>
      <span className="ob-radio-card-icon">{icon}</span>
      <span className="ob-radio-card-label">{label}</span>
      {sub && <span className="ob-radio-card-sub">{sub}</span>}
    </button>
  )
}

function NotifItem({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button className={`ob-notif-item${selected ? ' ob-selected' : ''}`} onClick={onClick}>
      <span className="ob-notif-check">{selected ? '✓' : ''}</span>
      {label}
    </button>
  )
}

function ToggleRow({ label, desc, checked, onChange }: {
  label: string; desc: string; checked: boolean; onChange: (v: boolean) => void
}) {
  return (
    <div className="ob-toggle-row" onClick={() => onChange(!checked)}>
      <div className="ob-toggle-info">
        <span className="ob-toggle-label">{label}</span>
        <span className="ob-toggle-desc">{desc}</span>
      </div>
      <div className={`ob-toggle${checked ? ' ob-on' : ''}`} />
    </div>
  )
}

function RangeField({
  label, min, max, value, unit = '', onChange,
}: { label: string; min: number; max: number; value: number; unit?: string; onChange: (v: number) => void }) {
  return (
    <div className="ob-field">
      <label>{label}</label>
      <div className="ob-range-wrap">
        <div className="ob-range-display">
          <span className="ob-range-hint">{min}{unit}</span>
          <span className="ob-range-val">{value}{unit}</span>
          <span className="ob-range-hint">{max}{unit}</span>
        </div>
        <input type="range" min={min} max={max} value={value} onChange={e => onChange(Number(e.target.value))} />
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════
   Housing data
══════════════════════════════════════════════ */

const BEDROOMS: BedroomType[] = ['Studio', '1BR', '2BR', '3BR+']
const BEDROOM_LABELS: Record<BedroomType, string> = {
  Studio: 'Studio', '1BR': '1 Bed', '2BR': '2 Beds', '3BR+': '3+ Beds',
}
const URGENCY: MoveInUrgency[] = ['Just browsing', 'Flexible', 'Soon', 'Urgent']
const URGENCY_ICONS: Record<MoveInUrgency, string> = {
  'Just browsing': '🧭', 'Flexible': '🗓️', 'Soon': '⚡', 'Urgent': '🔥',
}
const LAUNDRY = ['In-unit', 'On-site', 'W/D hookups'] as const
const PARKING_OPTS = ['Garage', 'Parking space', 'Not needed'] as const
const AMENITIES: { label: Amenity; emoji: string }[] = [
  { label: 'Hardwood floors', emoji: '🪵' },
  { label: 'Dishwasher', emoji: '🍽️' },
  { label: 'Air conditioning', emoji: '❄️' },
  { label: 'Balcony', emoji: '🏙️' },
  { label: 'Pool', emoji: '🏊' },
  { label: 'Gym', emoji: '💪' },
]
const PET_OPTS = ['No pets', '🐶 Dog', '🐱 Cat'] as const
const COMMUTE_OPTS: { mode: TransportMode; label: string }[] = [
  { mode: 'Drive', label: '🚗 Drive (no traffic)' },
  { mode: 'Drive', label: '🚙 Drive (with traffic)' },
  { mode: 'Transit', label: '🚇 Public transit' },
  { mode: 'Bike', label: '🚲 Bike' },
]
const PRIORITY_OPTS = [
  { icon: '⭐', label: 'All features', sub: 'Features over price' },
  { icon: '📍', label: 'Location', sub: 'Neighborhood first' },
  { icon: '💰', label: 'Lowest price', sub: 'Best value wins' },
]
const HOUSEHOLD_OPTS = ['Living alone', 'With roommate(s)', 'With partner', 'With co-signer']

/* ══════════════════════════════════════════════
   Negotiation data
══════════════════════════════════════════════ */

const NEG_ITEMS: NegotiableItem[] = [
  'Rent', 'Move-in date', 'Lease length', 'Deposit',
  'Parking fee', 'Pet fee', 'Utilities', 'Furnishing',
  'Application fee', 'Promotions',
]
const NEG_ITEM_LABELS: Record<NegotiableItem, string> = {
  'Rent': 'Rent price',
  'Move-in date': 'Move-in date',
  'Lease length': 'Lease length',
  'Deposit': 'Deposit',
  'Parking fee': 'Parking fee',
  'Pet fee': 'Pet fee',
  'Utilities': 'Utilities included',
  'Furnishing': 'Furnishing',
  'Application fee': 'Application fee waiver',
  'Promotions': 'Free month promo',
}
const GOALS: { goal: NegotiationGoal; icon: string; label: string }[] = [
  { goal: 'Lowest price', icon: '💰', label: 'Lowest price' },
  { goal: 'Best value', icon: '⚖️', label: 'Best overall value' },
  { goal: 'Fastest approval', icon: '🏃', label: 'Fastest approval' },
  { goal: 'Flexible move-in', icon: '📅', label: 'Flexible move-in' },
  { goal: 'Lowest upfront cost', icon: '💾', label: 'Low upfront cost' },
]
const APPROVAL_CONDITIONS = [
  'Rent exceeds budget',
  'High deposit',
  'Cosigner required',
  'Additional fees',
  'Lease changes',
  'Pet restrictions',
  'Documents required',
  'Credit / background issues',
]
const TONES: { tone: AgentTone; icon: string; label: string }[] = [
  { tone: 'Polite', icon: '🕊️', label: 'Polite & soft' },
  { tone: 'Professional', icon: '💼', label: 'Professional & direct' },
  { tone: 'Assertive', icon: '💪', label: 'Assertive' },
  { tone: 'Flexible', icon: '🔄', label: 'Friendly & flexible' },
]
const TIMING_OPTS = ['Anytime', 'Business hours only', 'Weekdays only']

/* ══════════════════════════════════════════════
   Notifications data
══════════════════════════════════════════════ */

const CHANNELS: { channel: NotificationChannel; emoji: string }[] = [
  { channel: 'Email', emoji: '📧' },
  { channel: 'SMS', emoji: '💬' },
  { channel: 'Push', emoji: '📱' },
  { channel: 'WhatsApp', emoji: '💚' },
  { channel: 'In-app', emoji: '🖥️' },
]
const EVENT_TYPES: { event: NotificationEvent; label: string }[] = [
  { event: 'New matches', label: 'New matching listings' },
  { event: 'Price drops', label: 'Price drops' },
  { event: 'Landlord replies', label: 'Landlord replies' },
  { event: 'Negotiation updates', label: 'Negotiation updates' },
  { event: 'Tour scheduled', label: 'Tour scheduled' },
  { event: 'Application updates', label: 'Application status' },
  { event: 'Documents required', label: 'Documents required' },
  { event: 'Lease offers', label: 'Lease offer received' },
]
const FREQ_OPTS: { freq: NotificationFrequency; icon: string; label: string }[] = [
  { freq: 'Real-time', icon: '⚡', label: 'Real-time' },
  { freq: 'Daily', icon: '☀️', label: 'Daily digest' },
  { freq: 'Weekly', icon: '📅', label: 'Weekly summary' },
  { freq: 'Twice daily', icon: '🚨', label: 'Urgent only' },
]
const TIMEZONES = [
  { value: 'America/New_York', label: 'America/New_York (UTC−5)' },
  { value: 'America/Chicago', label: 'America/Chicago (UTC−6)' },
  { value: 'America/Denver', label: 'America/Denver (UTC−7)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (UTC−8)' },
  { value: 'Europe/London', label: 'Europe/London (UTC+0)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (UTC+1)' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo (UTC+9)' },
  { value: 'Asia/Shanghai', label: 'Asia/Shanghai (UTC+8)' },
]

/* ══════════════════════════════════════════════
   Tab definitions
══════════════════════════════════════════════ */

type Tab = 'housing' | 'negotiation' | 'notifications'

const TABS: { id: Tab; label: string }[] = [
  { id: 'housing', label: 'House Preference' },
  { id: 'negotiation', label: 'Negotiation' },
  { id: 'notifications', label: 'Notifications' },
]

/* ══════════════════════════════════════════════
   Housing panel
══════════════════════════════════════════════ */

function HousingPanel() {
  const { preferences, updateHousing } = useStore()
  const { housing } = preferences

  const [laundry, setLaundry] = useState('In-unit')
  const [parking, setParking] = useState('Parking space')
  const [pet, setPet] = useState('No pets')
  const [commuteLabel, setCommuteLabel] = useState('🚇 Public transit')
  const [priority, setPriority] = useState('All features')
  const [household, setHousehold] = useState('Living alone')
  const [leaseLength, setLeaseLength] = useState(12)
  const [maxRent, setMaxRent] = useState(housing.budgetMax)

  const toggleBed = (b: BedroomType) => {
    const next = housing.bedrooms.includes(b)
      ? housing.bedrooms.filter(x => x !== b)
      : [...housing.bedrooms, b]
    updateHousing({ bedrooms: next })
  }

  const toggleAmenity = (a: Amenity) => {
    const next = housing.amenities.includes(a)
      ? housing.amenities.filter(x => x !== a)
      : [...housing.amenities, a]
    updateHousing({ amenities: next })
  }

  return (
    <div>
      <div className="ob-section">
        <div className="ob-section-title">🏠 Basic Search Criteria</div>

        <div className="ob-field" style={{ marginBottom: 18 }}>
          <label>Bedrooms</label>
          <div className="ob-chips">
            {BEDROOMS.map(b => (
              <Chip key={b} label={BEDROOM_LABELS[b]} selected={housing.bedrooms.includes(b)} onClick={() => toggleBed(b)} />
            ))}
          </div>
        </div>

        <div className="ob-grid-2" style={{ marginBottom: 18 }}>
          <div className="ob-field" style={{ gridColumn: '1/-1' }}>
            <label>Target City / Neighborhood</label>
            <input
              type="text"
              placeholder="e.g. Brooklyn, New York"
              value={housing.location}
              onChange={e => updateHousing({ location: e.target.value })}
            />
          </div>
        </div>

        <div className="ob-grid-2" style={{ marginBottom: 18 }}>
          <div className="ob-field">
            <label>Max Monthly Rent</label>
            <div className="ob-input-prefix-wrap">
              <span className="ob-input-prefix">$</span>
              <input
                type="number"
                value={maxRent}
                onChange={e => {
                  setMaxRent(Number(e.target.value))
                  updateHousing({ budgetMax: Number(e.target.value) })
                }}
              />
            </div>
          </div>
          <div className="ob-field">
            <label>Move-in Date</label>
            <input
              type="date"
              value={housing.moveInDate}
              onChange={e => updateHousing({ moveInDate: e.target.value })}
            />
          </div>
        </div>

        <div className="ob-field" style={{ marginBottom: 18 }}>
          <label>Move-in Urgency</label>
          <div className="ob-radio-cards">
            {URGENCY.map(u => (
              <RadioCard key={u} icon={URGENCY_ICONS[u]} label={u} selected={housing.moveInUrgency === u} onClick={() => updateHousing({ moveInUrgency: u })} />
            ))}
          </div>
        </div>

        <div className="ob-grid-2">
          <div className="ob-field">
            <label>Lease Length (months)</label>
            <input type="number" value={leaseLength} onChange={e => setLeaseLength(Number(e.target.value))} />
          </div>
          <div className="ob-field">
            <label>Household</label>
            <select value={household} onChange={e => setHousehold(e.target.value)}>
              {HOUSEHOLD_OPTS.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">✨ Property Preferences</div>

        <div className="ob-field" style={{ marginBottom: 16 }}>
          <label>Laundry</label>
          <div className="ob-chips">
            {LAUNDRY.map(o => <Chip key={o} label={o} selected={laundry === o} onClick={() => setLaundry(o)} />)}
          </div>
        </div>

        <div className="ob-field" style={{ marginBottom: 16 }}>
          <label>Parking</label>
          <div className="ob-chips">
            {PARKING_OPTS.map(o => <Chip key={o} label={o} selected={parking === o} onClick={() => setParking(o)} />)}
          </div>
        </div>

        <div className="ob-field" style={{ marginBottom: 16 }}>
          <label>Amenities (select all that apply)</label>
          <div className="ob-chips">
            {AMENITIES.map(({ label, emoji }) => (
              <Chip
                key={label}
                label={`${emoji} ${label}`}
                selected={housing.amenities.includes(label)}
                onClick={() => toggleAmenity(label)}
              />
            ))}
          </div>
        </div>

        <div className="ob-field">
          <label>Pets</label>
          <div className="ob-chips">
            {PET_OPTS.map(o => <Chip key={o} label={o} selected={pet === o} onClick={() => setPet(o)} />)}
          </div>
        </div>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">🎯 What Matters Most</div>

        <div className="ob-field" style={{ marginBottom: 20 }}>
          <label>Top priority</label>
          <div className="ob-radio-cards">
            {PRIORITY_OPTS.map(p => (
              <RadioCard key={p.label} icon={p.icon} label={p.label} sub={p.sub} selected={priority === p.label} onClick={() => setPriority(p.label)} />
            ))}
          </div>
        </div>

        <div className="ob-grid-2" style={{ marginBottom: 16 }}>
          <div className="ob-field" style={{ gridColumn: '1/-1' }}>
            <label>Work / School Address (for commute calculation)</label>
            <input
              type="text"
              placeholder="e.g. 1 World Trade Center, New York"
              value={housing.commuteAddress}
              onChange={e => updateHousing({ commuteAddress: e.target.value })}
            />
          </div>
        </div>

        <div className="ob-field" style={{ marginBottom: 16 }}>
          <label>Commute Method</label>
          <div className="ob-chips">
            {COMMUTE_OPTS.map(({ label }) => (
              <Chip key={label} label={label} selected={commuteLabel === label} onClick={() => setCommuteLabel(label)} />
            ))}
          </div>
        </div>

        <RangeField
          label="Max Commute Time"
          min={5} max={90} unit=" min"
          value={housing.maxCommuteTime}
          onChange={v => updateHousing({ maxCommuteTime: v })}
        />
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════
   Negotiation panel
══════════════════════════════════════════════ */

function NegotiationPanel() {
  const { preferences, updateNegotiation } = useStore()
  const { negotiation } = preferences

  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [payFees, setPayFees] = useState(false)
  const [timing, setTiming] = useState('Anytime')
  const [followUps, setFollowUps] = useState(3)

  const toggleItem = (item: NegotiableItem) => {
    const next = negotiation.negotiableItems.includes(item)
      ? negotiation.negotiableItems.filter(x => x !== item)
      : [...negotiation.negotiableItems, item]
    updateNegotiation({ negotiableItems: next })
  }

  const toggleCondition = (cond: string) => {
    const next = negotiation.approvalConditions.includes(cond)
      ? negotiation.approvalConditions.filter(x => x !== cond)
      : [...negotiation.approvalConditions, cond]
    updateNegotiation({ approvalConditions: next })
  }

  return (
    <div>
      <div className="ob-callout">
        <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>🤝</span>
        <span>
          Your AI agent will contact landlords and negotiate on your behalf.{' '}
          <strong style={{ color: '#f0f0f8' }}>You always have final approval on major decisions.</strong>
        </span>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">⚡ Enable Automation</div>
        <ToggleRow
          label="Allow agent to negotiate for me"
          desc="AI will contact landlords automatically, within your rules"
          checked={negotiation.enabled}
          onChange={v => updateNegotiation({ enabled: v })}
        />
      </div>

      <div style={!negotiation.enabled ? { opacity: 0.4, pointerEvents: 'none' } : undefined}>
        <div className="ob-section">
          <div className="ob-section-title">📋 Negotiable Items</div>
          <div className="ob-chips">
            {NEG_ITEMS.map(item => (
              <Chip
                key={item}
                label={NEG_ITEM_LABELS[item]}
                selected={negotiation.negotiableItems.includes(item)}
                onClick={() => toggleItem(item)}
              />
            ))}
          </div>
        </div>

        <div className="ob-section">
          <div className="ob-section-title">🎯 Negotiation Goal</div>
          <div className="ob-radio-cards">
            {GOALS.map(({ goal, icon, label }) => (
              <RadioCard key={goal} icon={icon} label={label} selected={negotiation.goal === goal} onClick={() => updateNegotiation({ goal })} />
            ))}
          </div>
        </div>

        <div className="ob-section">
          <div className="ob-section-title">🛡️ Hard Limits</div>
          <div className="ob-grid-2">
            <div className="ob-field">
              <label>Max rent agent can accept</label>
              <div className="ob-input-prefix-wrap">
                <span className="ob-input-prefix">$</span>
                <input type="number" value={negotiation.absoluteMaxRent} onChange={e => updateNegotiation({ absoluteMaxRent: Number(e.target.value) })} />
              </div>
            </div>
            <div className="ob-field">
              <label>Max deposit agent can accept</label>
              <div className="ob-input-prefix-wrap">
                <span className="ob-input-prefix">$</span>
                <input type="number" value={negotiation.maxDeposit} onChange={e => updateNegotiation({ maxDeposit: Number(e.target.value) })} />
              </div>
            </div>
            <div className="ob-field">
              <label>Latest acceptable move-in</label>
              <input type="date" value={negotiation.latestMoveIn} onChange={e => updateNegotiation({ latestMoveIn: e.target.value })} />
            </div>
            <div className="ob-field">
              <label>Min lease length (months)</label>
              <input type="number" placeholder={`${negotiation.leaseLengthMin}`} value={negotiation.leaseLengthMin} onChange={e => updateNegotiation({ leaseLengthMin: Number(e.target.value) })} />
            </div>
            <div className="ob-field">
              <label>Max lease length (months)</label>
              <input type="number" placeholder={`${negotiation.leaseLengthMax}`} value={negotiation.leaseLengthMax} onChange={e => updateNegotiation({ leaseLengthMax: Number(e.target.value) })} />
            </div>
          </div>
        </div>

        <div className="ob-section">
          <div className="ob-section-title">📌 Require My Approval When</div>
          <div className="ob-notif-grid">
            {APPROVAL_CONDITIONS.map(cond => (
              <NotifItem key={cond} label={cond} selected={negotiation.approvalConditions.includes(cond)} onClick={() => toggleCondition(cond)} />
            ))}
          </div>
        </div>

        <button className="ob-advanced-toggle" onClick={() => setAdvancedOpen(o => !o)}>
          <span className={`ob-advanced-arrow${advancedOpen ? ' ob-open' : ''}`}>▶</span>
          Advanced settings — negotiation style, outreach behavior &amp; agent permissions
        </button>

        <div className={`ob-advanced-section${advancedOpen ? ' ob-open' : ''}`}>
          <div className="ob-section">
            <div className="ob-section-title">🎭 Negotiation Style</div>
            <div className="ob-radio-cards">
              {TONES.map(({ tone, icon, label }) => (
                <RadioCard key={tone} icon={icon} label={label} selected={negotiation.agentTone === tone} onClick={() => updateNegotiation({ agentTone: tone })} />
              ))}
            </div>
          </div>

          <div className="ob-section">
            <div className="ob-section-title">💬 Outreach Behavior</div>
            <div className="ob-grid-2">
              <div className="ob-field">
                <label>Contact timing</label>
                <select value={timing} onChange={e => setTiming(e.target.value)}>
                  {TIMING_OPTS.map(o => <option key={o}>{o}</option>)}
                </select>
              </div>
              <div className="ob-field">
                <label>Max follow-ups per listing</label>
                <input type="number" value={followUps} onChange={e => setFollowUps(Number(e.target.value))} />
              </div>
            </div>
          </div>

          <div className="ob-section">
            <div className="ob-section-title">🔑 Agent Permissions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <ToggleRow
                label="Schedule tours automatically"
                desc="Agent can book viewings on your behalf"
                checked={negotiation.canScheduleTours}
                onChange={v => updateNegotiation({ canScheduleTours: v })}
              />
              <ToggleRow
                label="Submit applications"
                desc="Agent can submit rental applications"
                checked={negotiation.canSubmitApplications}
                onChange={v => updateNegotiation({ canSubmitApplications: v })}
              />
              <ToggleRow
                label="Pay fees"
                desc="Agent can pay deposits and application fees"
                checked={payFees}
                onChange={setPayFees}
              />
              <ToggleRow
                label="Confirm lease terms"
                desc="Agent can confirm non-critical clauses"
                checked={negotiation.canConfirmLeaseTerms}
                onChange={v => updateNegotiation({ canConfirmLeaseTerms: v })}
              />
            </div>
          </div>

          <div className="ob-section">
            <div className="ob-section-title">💡 Intent Anchors</div>
            <div className="ob-grid-2">
              <div className="ob-field">
                <label>Ideal rent (target)</label>
                <div className="ob-input-prefix-wrap">
                  <span className="ob-input-prefix">$</span>
                  <input type="number" value={negotiation.idealRent} onChange={e => updateNegotiation({ idealRent: Number(e.target.value) })} />
                </div>
              </div>
              <div className="ob-field">
                <label>Maximum rent (hard limit)</label>
                <div className="ob-input-prefix-wrap">
                  <span className="ob-input-prefix">$</span>
                  <input type="number" value={negotiation.absoluteMaxRent} onChange={e => updateNegotiation({ absoluteMaxRent: Number(e.target.value) })} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════
   Notifications panel
══════════════════════════════════════════════ */

function NotificationsPanel() {
  const { preferences, updateNotifications } = useStore()
  const { notifications } = preferences

  const [priceDrop, setPriceDrop] = useState(notifications.priceDropThreshold)
  const [matchScore, setMatchScore] = useState(notifications.matchScoreThreshold)
  const [commuteImprove, setCommuteImprove] = useState(10)

  const toggleChannel = (channel: NotificationChannel) => {
    const next = notifications.channels.includes(channel)
      ? notifications.channels.filter(x => x !== channel)
      : [...notifications.channels, channel]
    updateNotifications({ channels: next })
  }

  const toggleEvent = (event: NotificationEvent) => {
    const next = notifications.events.includes(event)
      ? notifications.events.filter(x => x !== event)
      : [...notifications.events, event]
    updateNotifications({ events: next })
  }

  return (
    <div>
      <div className="ob-section">
        <div className="ob-section-title">📢 Notification Channels</div>
        <div className="ob-chips">
          {CHANNELS.map(({ channel, emoji }) => (
            <Chip key={channel} label={`${emoji} ${channel}`} selected={notifications.channels.includes(channel)} onClick={() => toggleChannel(channel)} />
          ))}
        </div>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">🗓️ Notification Types</div>
        <div className="ob-notif-grid">
          {EVENT_TYPES.map(({ event, label }) => (
            <NotifItem key={event} label={label} selected={notifications.events.includes(event)} onClick={() => toggleEvent(event)} />
          ))}
          <NotifItem key="better-matches" label="Better matches found" selected={false} onClick={() => { }} />
          <NotifItem key="suspicious" label="Suspicious listing alert" selected={notifications.events.includes('New matches')} onClick={() => { }} />
        </div>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">⏱️ Notification Frequency</div>
        <div className="ob-radio-cards">
          {FREQ_OPTS.map(({ freq, icon, label }) => (
            <RadioCard key={freq} icon={icon} label={label} selected={notifications.frequency === freq} onClick={() => updateNotifications({ frequency: freq })} />
          ))}
        </div>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">🌙 Do Not Disturb</div>
        <div className="ob-grid-2">
          <div className="ob-field">
            <label>Start time</label>
            <input type="time" value={notifications.quietHoursStart} onChange={e => updateNotifications({ quietHoursStart: e.target.value })} />
          </div>
          <div className="ob-field">
            <label>End time</label>
            <input type="time" value={notifications.quietHoursEnd} onChange={e => updateNotifications({ quietHoursEnd: e.target.value })} />
          </div>
          <div className="ob-field" style={{ gridColumn: '1/-1' }}>
            <label>Time zone</label>
            <select value={notifications.timezone} onChange={e => updateNotifications({ timezone: e.target.value })}>
              {TIMEZONES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">🏷️ Alert Thresholds</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="ob-field">
            <label>Notify me when price drops ≥ X%</label>
            <div className="ob-range-wrap">
              <div className="ob-range-display">
                <span className="ob-range-hint">1%</span>
                <span className="ob-range-val">{priceDrop}%</span>
                <span className="ob-range-hint">20%</span>
              </div>
              <input type="range" min={1} max={20} value={priceDrop} onChange={e => { setPriceDrop(Number(e.target.value)); updateNotifications({ priceDropThreshold: Number(e.target.value) }) }} />
            </div>
          </div>
          <div className="ob-field">
            <label>Notify me when match score ≥ X</label>
            <div className="ob-range-wrap">
              <div className="ob-range-display">
                <span className="ob-range-hint">60</span>
                <span className="ob-range-val">{matchScore}</span>
                <span className="ob-range-hint">100</span>
              </div>
              <input type="range" min={60} max={100} value={matchScore} onChange={e => { setMatchScore(Number(e.target.value)); updateNotifications({ matchScoreThreshold: Number(e.target.value) }) }} />
            </div>
          </div>
          <div className="ob-field">
            <label>Notify me when commute improves ≥ X minutes</label>
            <div className="ob-range-wrap">
              <div className="ob-range-display">
                <span className="ob-range-hint">1 min</span>
                <span className="ob-range-val">{commuteImprove} min</span>
                <span className="ob-range-hint">30 min</span>
              </div>
              <input type="range" min={1} max={30} value={commuteImprove} onChange={e => setCommuteImprove(Number(e.target.value))} />
            </div>
          </div>
        </div>
      </div>

      <div className="ob-section">
        <div className="ob-section-title">⏰ Reminder Behavior</div>
        <div className="ob-grid-2">
          <div className="ob-field">
            <label>Max reminders per listing</label>
            <input type="number" value={notifications.reminderCount} onChange={e => updateNotifications({ reminderCount: Number(e.target.value) })} />
          </div>
          <div className="ob-field">
            <label>Reminder interval (hours)</label>
            <input type="number" value={notifications.reminderIntervalHours} onChange={e => updateNotifications({ reminderIntervalHours: Number(e.target.value) })} />
          </div>
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════
   PreferenceSetting — main export
══════════════════════════════════════════════ */

interface Props {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  onBack: () => void
  onNext: () => void
  isFirstTab: boolean
  isLastTab: boolean
}

export function PreferenceSetting({ activeTab, onTabChange, onBack, onNext, isFirstTab, isLastTab }: Props) {
  return (
    <>
      {/* Heading */}
      <h2 className="text-white text-center font-semibold text-5xl leading-[130%] tracking-[-1.44px] max-w-[700px] mx-auto mb-10">
        Three quick steps&nbsp;— then let AI match, negotiate, and keep you posted.
      </h2>

      {/* Tab pills */}
      <div className="flex items-center justify-center gap-2.5 mb-8 flex-wrap">
        {TABS.map(({ id, label }) => {
          const tabIndex = TABS.findIndex(t => t.id === id)
          const activeIndex = TABS.findIndex(t => t.id === activeTab)
          const isActive = id === activeTab
          const isDone = tabIndex < activeIndex
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className={[
                'rounded-full font-semibold text-[13px] tracking-[0.02em] transition-all duration-200 cursor-pointer',
                isActive
                  ? 'border-0 px-[23.5px] py-[10.5px] text-white shadow-[0_4px_20px_rgba(106,92,255,0.35)]'
                  : isDone
                    ? 'border-[1.5px] px-[22px] py-[9px] border-white/35 text-white/65 bg-transparent'
                    : 'border-[1.5px] px-[22px] py-[9px] border-white/20 text-white/40 bg-transparent',
              ].join(' ')}
              style={isActive ? { background: 'linear-gradient(135deg, #6A5CFF 0%, #4A6CFF 40%, #8A5CFF 70%, #FFB6A3 100%)' } : undefined}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Glass card */}
      <div className="max-w-[760px] mx-auto bg-white/[0.04] border border-white/[0.09] rounded-[20px] px-9 py-8 backdrop-blur-xl">
        <div className="ob ob-glass">
          {activeTab === 'housing' && <HousingPanel />}
          {activeTab === 'negotiation' && <NegotiationPanel />}
          {activeTab === 'notifications' && <NotificationsPanel />}
        </div>
      </div>

      {/* Navigation */}
      <div className="max-w-[760px] mt-6 mx-auto flex justify-between items-center">
        <button
          onClick={onBack}
          disabled={isFirstTab}
          className={[
            'px-7 py-[11px] rounded-full border border-white/20 bg-transparent text-white/55 text-[13px] font-medium transition-opacity duration-200',
            isFirstTab ? 'opacity-0 cursor-default' : 'opacity-100 cursor-pointer',
          ].join(' ')}
        >
          ← Back
        </button>

        <button
          onClick={onNext}
          className="px-8 py-[11px] rounded-full border-0 text-white text-[13px] font-bold cursor-pointer tracking-[0.02em] shadow-[0_6px_24px_rgba(106,92,255,0.4)] transition-[transform,box-shadow] duration-150 hover:-translate-y-px hover:shadow-[0_10px_30px_rgba(106,92,255,0.5)]"
          style={{ background: 'linear-gradient(135deg, #6A5CFF 0%, #4A6CFF 100%)' }}
        >
          {isLastTab ? 'Finish setup →' : 'Next →'}
        </button>
      </div>
    </>
  )
}

export type { Tab }

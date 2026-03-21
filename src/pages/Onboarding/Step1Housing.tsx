import { useState } from 'react'
import { useStore } from '../../store/useStore'
import type { BedroomType, Amenity, MoveInUrgency, TransportMode } from '../../types'

/* ── reusable primitives ── */

function Chip({
  label, selected, onClick,
}: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button className={`ob-chip${selected ? ' ob-selected' : ''}`} onClick={onClick}>
      {label}
    </button>
  )
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

function RangeField({
  label, min, max, value, unit = '',
  onChange,
}: {
  label: string; min: number; max: number; value: number; unit?: string
  onChange: (v: number) => void
}) {
  return (
    <div className="ob-field">
      <label>{label}</label>
      <div className="ob-range-wrap">
        <div className="ob-range-display">
          <span className="ob-range-hint">{min}{unit}</span>
          <span className="ob-range-val">{value}{unit}</span>
          <span className="ob-range-hint">{max}{unit}</span>
        </div>
        <input
          type="range" min={min} max={max} value={value}
          onChange={e => onChange(Number(e.target.value))}
        />
      </div>
    </div>
  )
}

/* ── data ── */
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

export function Step1Housing() {
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
      {/* ── Basic Search ── */}
      <div className="ob-section">
        <div className="ob-section-title">🏠 Basic Search Criteria</div>

        <div className="ob-field" style={{ marginBottom: 18 }}>
          <label>Bedrooms</label>
          <div className="ob-chips">
            {BEDROOMS.map(b => (
              <Chip
                key={b}
                label={BEDROOM_LABELS[b]}
                selected={housing.bedrooms.includes(b)}
                onClick={() => toggleBed(b)}
              />
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
              <RadioCard
                key={u}
                icon={URGENCY_ICONS[u]}
                label={u}
                selected={housing.moveInUrgency === u}
                onClick={() => updateHousing({ moveInUrgency: u })}
              />
            ))}
          </div>
        </div>

        <div className="ob-grid-2">
          <div className="ob-field">
            <label>Lease Length (months)</label>
            <input
              type="number"
              value={leaseLength}
              onChange={e => setLeaseLength(Number(e.target.value))}
            />
          </div>
          <div className="ob-field">
            <label>Household</label>
            <select value={household} onChange={e => setHousehold(e.target.value)}>
              {HOUSEHOLD_OPTS.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* ── Property Preferences ── */}
      <div className="ob-section">
        <div className="ob-section-title">✨ Property Preferences</div>

        <div className="ob-field" style={{ marginBottom: 16 }}>
          <label>Laundry</label>
          <div className="ob-chips">
            {LAUNDRY.map(o => (
              <Chip key={o} label={o} selected={laundry === o} onClick={() => setLaundry(o)} />
            ))}
          </div>
        </div>

        <div className="ob-field" style={{ marginBottom: 16 }}>
          <label>Parking</label>
          <div className="ob-chips">
            {PARKING_OPTS.map(o => (
              <Chip key={o} label={o} selected={parking === o} onClick={() => setParking(o)} />
            ))}
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
            {PET_OPTS.map(o => (
              <Chip key={o} label={o} selected={pet === o} onClick={() => setPet(o)} />
            ))}
          </div>
        </div>
      </div>

      {/* ── Lifestyle ── */}
      <div className="ob-section">
        <div className="ob-section-title">🎯 What Matters Most</div>

        <div className="ob-field" style={{ marginBottom: 20 }}>
          <label>Top priority</label>
          <div className="ob-radio-cards">
            {PRIORITY_OPTS.map(p => (
              <RadioCard
                key={p.label}
                icon={p.icon}
                label={p.label}
                sub={p.sub}
                selected={priority === p.label}
                onClick={() => setPriority(p.label)}
              />
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
              <Chip
                key={label}
                label={label}
                selected={commuteLabel === label}
                onClick={() => setCommuteLabel(label)}
              />
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

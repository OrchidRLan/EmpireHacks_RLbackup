import { useState } from 'react'
import { useStore } from '../../store/useStore'
import type { NotificationChannel, NotificationEvent, NotificationFrequency } from '../../types'

/* ── primitives ── */
function Chip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return <button className={`ob-chip${selected ? ' ob-selected' : ''}`} onClick={onClick}>{label}</button>
}

function NotifItem({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button className={`ob-notif-item${selected ? ' ob-selected' : ''}`} onClick={onClick}>
      <span className="ob-notif-check">{selected ? '✓' : ''}</span>
      {label}
    </button>
  )
}

function RadioCard({ icon, label, selected, onClick }: { icon: string; label: string; selected: boolean; onClick: () => void }) {
  return (
    <button className={`ob-radio-card${selected ? ' ob-selected' : ''}`} onClick={onClick}>
      <span className="ob-radio-card-icon">{icon}</span>
      <span className="ob-radio-card-label">{label}</span>
    </button>
  )
}

/* ── data ── */
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

export function Step3Notifications() {
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
      {/* Channels */}
      <div className="ob-section">
        <div className="ob-section-title">📢 Notification Channels</div>
        <div className="ob-chips">
          {CHANNELS.map(({ channel, emoji }) => (
            <Chip
              key={channel}
              label={`${emoji} ${channel}`}
              selected={notifications.channels.includes(channel)}
              onClick={() => toggleChannel(channel)}
            />
          ))}
        </div>
      </div>

      {/* Event types */}
      <div className="ob-section">
        <div className="ob-section-title">🗓️ Notification Types</div>
        <div className="ob-notif-grid">
          {EVENT_TYPES.map(({ event, label }) => (
            <NotifItem
              key={event}
              label={label}
              selected={notifications.events.includes(event)}
              onClick={() => toggleEvent(event)}
            />
          ))}
          {/* Extra items from HTML */}
          <NotifItem
            key="better-matches"
            label="Better matches found"
            selected={false}
            onClick={() => {}}
          />
          <NotifItem
            key="suspicious"
            label="Suspicious listing alert"
            selected={notifications.events.includes('New matches')}
            onClick={() => {}}
          />
        </div>
      </div>

      {/* Frequency */}
      <div className="ob-section">
        <div className="ob-section-title">⏱️ Notification Frequency</div>
        <div className="ob-radio-cards">
          {FREQ_OPTS.map(({ freq, icon, label }) => (
            <RadioCard
              key={freq}
              icon={icon}
              label={label}
              selected={notifications.frequency === freq}
              onClick={() => updateNotifications({ frequency: freq })}
            />
          ))}
        </div>
      </div>

      {/* Do Not Disturb */}
      <div className="ob-section">
        <div className="ob-section-title">🌙 Do Not Disturb</div>
        <div className="ob-grid-2">
          <div className="ob-field">
            <label>Start time</label>
            <input
              type="time"
              value={notifications.quietHoursStart}
              onChange={e => updateNotifications({ quietHoursStart: e.target.value })}
            />
          </div>
          <div className="ob-field">
            <label>End time</label>
            <input
              type="time"
              value={notifications.quietHoursEnd}
              onChange={e => updateNotifications({ quietHoursEnd: e.target.value })}
            />
          </div>
          <div className="ob-field" style={{ gridColumn: '1/-1' }}>
            <label>Time zone</label>
            <select
              value={notifications.timezone}
              onChange={e => updateNotifications({ timezone: e.target.value })}
            >
              {TIMEZONES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Thresholds */}
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
              <input
                type="range" min={1} max={20} value={priceDrop}
                onChange={e => {
                  setPriceDrop(Number(e.target.value))
                  updateNotifications({ priceDropThreshold: Number(e.target.value) })
                }}
              />
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
              <input
                type="range" min={60} max={100} value={matchScore}
                onChange={e => {
                  setMatchScore(Number(e.target.value))
                  updateNotifications({ matchScoreThreshold: Number(e.target.value) })
                }}
              />
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
              <input
                type="range" min={1} max={30} value={commuteImprove}
                onChange={e => setCommuteImprove(Number(e.target.value))}
              />
            </div>
          </div>

        </div>
      </div>

      {/* Reminder Behavior */}
      <div className="ob-section">
        <div className="ob-section-title">⏰ Reminder Behavior</div>
        <div className="ob-grid-2">
          <div className="ob-field">
            <label>Max reminders per listing</label>
            <input
              type="number"
              value={notifications.reminderCount}
              onChange={e => updateNotifications({ reminderCount: Number(e.target.value) })}
            />
          </div>
          <div className="ob-field">
            <label>Reminder interval (hours)</label>
            <input
              type="number"
              value={notifications.reminderIntervalHours}
              onChange={e => updateNotifications({ reminderIntervalHours: Number(e.target.value) })}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

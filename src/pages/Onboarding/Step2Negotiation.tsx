import { useState } from 'react'
import { useStore } from '../../store/useStore'
import type { NegotiableItem, NegotiationGoal, AgentTone } from '../../types'

/* ── primitives ── */

function Chip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return <button className={`ob-chip${selected ? ' ob-selected' : ''}`} onClick={onClick}>{label}</button>
}

function RadioCard({ icon, label, selected, onClick }: { icon: string; label: string; selected: boolean; onClick: () => void }) {
  return (
    <button className={`ob-radio-card${selected ? ' ob-selected' : ''}`} onClick={onClick}>
      <span className="ob-radio-card-icon">{icon}</span>
      <span className="ob-radio-card-label">{label}</span>
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

/* ── data ── */
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

export function Step2Negotiation() {
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
      {/* Callout */}
      <div className="ob-callout">
        <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>🤝</span>
        <span>
          Your AI agent will contact landlords and negotiate on your behalf.{' '}
          <strong style={{ color: '#f0f0f8' }}>You always have final approval on major decisions.</strong>
        </span>
      </div>

      {/* Enable toggle */}
      <div className="ob-section">
        <div className="ob-section-title">⚡ Enable Automation</div>
        <ToggleRow
          label="Allow agent to negotiate for me"
          desc="AI will contact landlords automatically, within your rules"
          checked={negotiation.enabled}
          onChange={v => updateNegotiation({ enabled: v })}
        />
      </div>

      {/* Sub-modules — disabled when off */}
      <div style={!negotiation.enabled ? { opacity: 0.4, pointerEvents: 'none' } : undefined}>

        {/* Negotiable Items */}
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

        {/* Goal */}
        <div className="ob-section">
          <div className="ob-section-title">🎯 Negotiation Goal</div>
          <div className="ob-radio-cards">
            {GOALS.map(({ goal, icon, label }) => (
              <RadioCard
                key={goal}
                icon={icon}
                label={label}
                selected={negotiation.goal === goal}
                onClick={() => updateNegotiation({ goal })}
              />
            ))}
          </div>
        </div>

        {/* Hard Limits */}
        <div className="ob-section">
          <div className="ob-section-title">🛡️ Hard Limits</div>
          <div className="ob-grid-2">
            <div className="ob-field">
              <label>Max rent agent can accept</label>
              <div className="ob-input-prefix-wrap">
                <span className="ob-input-prefix">$</span>
                <input
                  type="number"
                  value={negotiation.absoluteMaxRent}
                  onChange={e => updateNegotiation({ absoluteMaxRent: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="ob-field">
              <label>Max deposit agent can accept</label>
              <div className="ob-input-prefix-wrap">
                <span className="ob-input-prefix">$</span>
                <input
                  type="number"
                  value={negotiation.maxDeposit}
                  onChange={e => updateNegotiation({ maxDeposit: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="ob-field">
              <label>Latest acceptable move-in</label>
              <input
                type="date"
                value={negotiation.latestMoveIn}
                onChange={e => updateNegotiation({ latestMoveIn: e.target.value })}
              />
            </div>
            <div className="ob-field">
              <label>Lease length range (months)</label>
              <input
                type="text"
                placeholder={`${negotiation.leaseLengthMin} – ${negotiation.leaseLengthMax}`}
                readOnly
              />
            </div>
          </div>
        </div>

        {/* Approval Conditions */}
        <div className="ob-section">
          <div className="ob-section-title">📌 Require My Approval When</div>
          <div className="ob-notif-grid">
            {APPROVAL_CONDITIONS.map(cond => (
              <NotifItem
                key={cond}
                label={cond}
                selected={negotiation.approvalConditions.includes(cond)}
                onClick={() => toggleCondition(cond)}
              />
            ))}
          </div>
        </div>

        {/* Advanced toggle */}
        <button className="ob-advanced-toggle" onClick={() => setAdvancedOpen(o => !o)}>
          <span className={`ob-advanced-arrow${advancedOpen ? ' ob-open' : ''}`}>▶</span>
          Advanced settings — negotiation style, outreach behavior &amp; agent permissions
        </button>

        <div className={`ob-advanced-section${advancedOpen ? ' ob-open' : ''}`}>

          {/* Style */}
          <div className="ob-section">
            <div className="ob-section-title">🎭 Negotiation Style</div>
            <div className="ob-radio-cards">
              {TONES.map(({ tone, icon, label }) => (
                <RadioCard
                  key={tone}
                  icon={icon}
                  label={label}
                  selected={negotiation.agentTone === tone}
                  onClick={() => updateNegotiation({ agentTone: tone })}
                />
              ))}
            </div>
          </div>

          {/* Outreach Behavior */}
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
                <input
                  type="number"
                  value={followUps}
                  onChange={e => setFollowUps(Number(e.target.value))}
                />
              </div>
            </div>
          </div>

          {/* Permissions */}
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

          {/* Intent Anchors */}
          <div className="ob-section">
            <div className="ob-section-title">💡 Intent Anchors</div>
            <div className="ob-grid-2">
              <div className="ob-field">
                <label>Ideal rent (target)</label>
                <div className="ob-input-prefix-wrap">
                  <span className="ob-input-prefix">$</span>
                  <input
                    type="number"
                    value={negotiation.idealRent}
                    onChange={e => updateNegotiation({ idealRent: Number(e.target.value) })}
                  />
                </div>
              </div>
              <div className="ob-field">
                <label>Maximum rent (hard limit)</label>
                <div className="ob-input-prefix-wrap">
                  <span className="ob-input-prefix">$</span>
                  <input
                    type="number"
                    value={negotiation.absoluteMaxRent}
                    onChange={e => updateNegotiation({ absoluteMaxRent: Number(e.target.value) })}
                  />
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

import { useNavigate } from 'react-router-dom'
import { useStore } from '../../store/useStore'
import { formatCurrency } from '../../lib/utils'

export function CompletionScreen() {
  const navigate = useNavigate()
  const { preferences, setOnboardingComplete, setOnboardingStep } = useStore()
  const { housing, negotiation, notifications } = preferences

  const handleStart = () => {
    setOnboardingComplete(true)
    navigate('/dashboard')
  }

  // Build dynamic summary pills
  const purplePills: string[] = []
  const tealPills: string[] = []

  if (housing.bedrooms.length > 0) {
    purplePills.push(
      housing.bedrooms.map(b => b === '1BR' ? '1 Bed' : b === '2BR' ? '2 Beds' : b === '3BR+' ? '3+ Beds' : b).join(' / ')
    )
  }
  if (housing.budgetMax) purplePills.push(`Up to ${formatCurrency(housing.budgetMax)}/mo`)
  if (housing.amenities.length > 0) purplePills.push(housing.amenities.slice(0, 3).join(' · '))

  if (negotiation.enabled) {
    tealPills.push('AI Negotiation ON')
    if (negotiation.agentTone) tealPills.push(`${negotiation.agentTone} style`)
  } else {
    purplePills.push('Negotiation OFF')
  }

  if (notifications.frequency) purplePills.push(`${notifications.frequency} alerts`)
  if (notifications.priceDropThreshold) tealPills.push(`Price drop ≥ ${notifications.priceDropThreshold}%`)
  if (notifications.channels.length > 0) tealPills.push(notifications.channels.slice(0, 2).join(' · '))

  return (
    <div style={{ textAlign: 'center', padding: '60px 20px' }} className="ob-anim-fade-up">

      <div className="ob-finish-icon">🏠</div>

      <div className="ob-finish-title">You're all set!</div>
      <p className="ob-finish-sub">
        Your AI rental agent is ready to go. We'll match listings, negotiate terms, and keep you
        informed — without the stress.
      </p>

      {/* Summary pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8, marginBottom: 32 }}>
        {purplePills.map((p, i) => (
          <span key={i} className="ob-badge ob-badge-purple">{p}</span>
        ))}
        {tealPills.map((p, i) => (
          <span key={i} className="ob-badge ob-badge-teal">{p}</span>
        ))}
      </div>

      {/* CTA buttons */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        <button className="ob-btn ob-btn-ghost" onClick={() => setOnboardingStep(1)}>
          ← Edit preferences
        </button>
        <button className="ob-btn ob-btn-success" onClick={handleStart}>
          🚀 Start searching
        </button>
      </div>

    </div>
  )
}

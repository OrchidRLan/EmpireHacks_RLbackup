import { Sparkles, MapPin, Home, Bell, MessageSquare } from 'lucide-react'
import { useStore } from '../../store/useStore'
import { formatCurrency } from '../../lib/utils'

interface Props {
  step: number
}

export function AIPreviewPanel({ step }: Props) {
  const { preferences } = useStore()
  const { housing, negotiation, notifications } = preferences

  const summaries: Record<number, { icon: React.ElementType; color: string; lines: string[] }> = {
    1: {
      icon: Home,
      color: 'text-indigo-600 dark:text-indigo-400',
      lines: [
        housing.bedrooms.length
          ? `Looking for ${housing.bedrooms.join(', ')} in ${housing.location || 'your area'}`
          : 'Tell me your bedroom preference to get started',
        housing.budgetMax
          ? `Budget up to ${formatCurrency(housing.budgetMax)}/mo`
          : 'Set your budget range',
        housing.moveInUrgency ? `Move-in urgency: ${housing.moveInUrgency}` : 'Add your move-in timeline',
        housing.amenities.length
          ? `Priority amenities: ${housing.amenities.slice(0, 3).join(', ')}`
          : 'Select your preferred amenities',
      ],
    },
    2: {
      icon: MessageSquare,
      color: 'text-purple-600 dark:text-purple-400',
      lines: negotiation.enabled
        ? [
            `Negotiation ${negotiation.enabled ? 'enabled' : 'disabled'}`,
            negotiation.goal ? `Goal: ${negotiation.goal}` : 'Set your negotiation goal',
            negotiation.agentTone ? `Agent tone: ${negotiation.agentTone}` : 'Choose your agent tone',
            `Max rent the agent can accept: ${formatCurrency(negotiation.absoluteMaxRent)}/mo`,
          ]
        : ['Negotiation is turned off — agent will find matches only'],
    },
    3: {
      icon: Bell,
      color: 'text-amber-600 dark:text-amber-400',
      lines: [
        notifications.mode ? `Mode: ${notifications.mode}` : 'Set your notification mode',
        notifications.channels.length
          ? `Channels: ${notifications.channels.join(', ')}`
          : 'Choose notification channels',
        notifications.frequency ? `Frequency: ${notifications.frequency}` : 'Set update frequency',
        `Quiet hours: ${notifications.quietHoursStart} – ${notifications.quietHoursEnd}`,
      ],
    },
  }

  const current = summaries[step]
  const Icon = current.icon

  return (
    <div className="w-full rounded-xl border border-indigo-100 dark:border-indigo-900/40 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 p-4 mb-6">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 w-8 h-8 rounded-lg bg-white dark:bg-slate-800 shadow-sm flex items-center justify-center shrink-0">
          <Sparkles size={16} className="text-indigo-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-2">
            <Icon size={14} className={current.color} />
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
              AI Preview
            </span>
          </div>
          <ul className="space-y-1">
            {current.lines.map((line, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm text-slate-700 dark:text-slate-300">
                <span className="mt-1 w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
                {line}
              </li>
            ))}
          </ul>
        </div>
      </div>
      {step === 1 && housing.budgetMin && housing.budgetMax && (
        <div className="mt-3 pt-3 border-t border-indigo-100 dark:border-indigo-900/40 flex items-center gap-2">
          <MapPin size={12} className="text-indigo-500" />
          <span className="text-xs text-indigo-600 dark:text-indigo-400 font-medium">
            Estimated ~312 matching listings in this range
          </span>
        </div>
      )}
    </div>
  )
}

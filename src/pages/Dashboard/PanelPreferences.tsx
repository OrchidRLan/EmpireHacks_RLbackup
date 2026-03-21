import { useState } from 'react'
import {
  Home, MapPin, Clock, Star, Bell, Edit2, Check,
  Car, Train, Bike,
} from 'lucide-react'
import { useStore } from '../../store/useStore'
import { Slider } from '../../components/ui/slider'
import { Switch } from '../../components/ui/switch'
import { Badge } from '../../components/ui/badge'
import { cn, formatCurrency } from '../../lib/utils'
import type { BedroomType, TransportMode, Amenity, NotificationChannel } from '../../types'

function EditableSection({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: React.ElementType
  children: (editing: boolean) => React.ReactNode
}) {
  const [editing, setEditing] = useState(false)

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-700/70">
        <div className="flex items-center gap-2">
          <Icon size={15} className="text-indigo-500" />
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{title}</h3>
        </div>
        <button
          onClick={() => setEditing((v) => !v)}
          className={cn(
            'flex items-center gap-1 text-xs px-2 py-1 rounded-md transition-colors',
            editing
              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
              : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:text-slate-300 dark:hover:bg-slate-700'
          )}
        >
          {editing ? <Check size={12} /> : <Edit2 size={12} />}
          {editing ? 'Done' : 'Edit'}
        </button>
      </div>
      <div className="p-4">{children(editing)}</div>
    </div>
  )
}

const bedroomOptions: BedroomType[] = ['Studio', '1BR', '2BR', '3BR+']
const amenityOptions: { label: Amenity; emoji: string }[] = [
  { label: 'Hardwood floors', emoji: '🪵' },
  { label: 'Dishwasher', emoji: '🍽️' },
  { label: 'Air conditioning', emoji: '❄️' },
  { label: 'Balcony', emoji: '🏙️' },
  { label: 'Pool', emoji: '🏊' },
  { label: 'Gym', emoji: '💪' },
]

export function PanelPreferences() {
  const { preferences, updateHousing, updateNotifications } = useStore()
  const { housing, notifications } = preferences

  const toggleBedroom = (b: BedroomType) => {
    const next = housing.bedrooms.includes(b)
      ? housing.bedrooms.filter((x) => x !== b)
      : [...housing.bedrooms, b]
    updateHousing({ bedrooms: next })
  }

  const toggleAmenity = (a: Amenity) => {
    const next = housing.amenities.includes(a)
      ? housing.amenities.filter((x) => x !== a)
      : [...housing.amenities, a]
    updateHousing({ amenities: next })
  }

  const toggleTransport = (t: TransportMode) => {
    const next = housing.transportModes.includes(t)
      ? housing.transportModes.filter((x) => x !== t)
      : [...housing.transportModes, t]
    updateHousing({ transportModes: next })
  }

  const toggleChannel = (ch: NotificationChannel) => {
    const next = notifications.channels.includes(ch)
      ? notifications.channels.filter((x) => x !== ch)
      : [...notifications.channels, ch]
    updateNotifications({ channels: next })
  }

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4">
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Your Preferences</h2>
          <Badge variant="default">Live sync</Badge>
        </div>

        {/* Housing Summary */}
        <EditableSection title="Housing" icon={Home}>
          {(editing) => (
            <div className="space-y-4">
              {/* Bedrooms */}
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide">
                  Bedrooms
                </p>
                {editing ? (
                  <div className="flex flex-wrap gap-2">
                    {bedroomOptions.map((b) => (
                      <button
                        key={b}
                        onClick={() => toggleBedroom(b)}
                        className={cn(
                          'px-3 py-1.5 rounded-full text-sm font-medium border transition-all',
                          housing.bedrooms.includes(b)
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-600'
                        )}
                      >
                        {b}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {housing.bedrooms.map((b) => (
                      <Badge key={b} variant="secondary">{b}</Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Budget */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    Budget
                  </p>
                  <span className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">
                    {formatCurrency(housing.budgetMin)} – {formatCurrency(housing.budgetMax)}/mo
                  </span>
                </div>
                {editing ? (
                  <Slider
                    min={500}
                    max={8000}
                    step={50}
                    value={[housing.budgetMin, housing.budgetMax]}
                    onValueChange={([min, max]) => updateHousing({ budgetMin: min, budgetMax: max })}
                  />
                ) : (
                  <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                    <div
                      className="h-full bg-indigo-200 dark:bg-indigo-800 rounded-full relative"
                      style={{
                        marginLeft: `${((housing.budgetMin - 500) / 7500) * 100}%`,
                        width: `${((housing.budgetMax - housing.budgetMin) / 7500) * 100}%`,
                      }}
                    >
                      <div className="absolute inset-0 bg-indigo-500/40 rounded-full" />
                    </div>
                  </div>
                )}
              </div>

              {/* Location */}
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide">
                  Location
                </p>
                {editing ? (
                  <div className="relative">
                    <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      value={housing.location}
                      onChange={(e) => updateHousing({ location: e.target.value })}
                      className="w-full pl-8 pr-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                ) : (
                  <p className="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-1">
                    <MapPin size={13} className="text-slate-400" />
                    {housing.location}
                  </p>
                )}
              </div>
            </div>
          )}
        </EditableSection>

        {/* Commute */}
        <EditableSection title="Commute" icon={Clock}>
          {(editing) => (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Max commute</span>
                <span className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">
                  {housing.maxCommuteTime} min
                </span>
              </div>
              {editing ? (
                <>
                  <Slider
                    min={5}
                    max={60}
                    step={5}
                    value={[housing.maxCommuteTime]}
                    onValueChange={([v]) => updateHousing({ maxCommuteTime: v })}
                  />
                  <div className="flex gap-2 mt-3">
                    {([
                      { mode: 'Drive' as TransportMode, icon: Car },
                      { mode: 'Transit' as TransportMode, icon: Train },
                      { mode: 'Bike' as TransportMode, icon: Bike },
                    ]).map(({ mode, icon: Icon }) => (
                      <button
                        key={mode}
                        onClick={() => toggleTransport(mode)}
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-all',
                          housing.transportModes.includes(mode)
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-600'
                        )}
                      >
                        <Icon size={13} />
                        {mode}
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {housing.transportModes.map((t) => (
                    <Badge key={t} variant="secondary">{t}</Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </EditableSection>

        {/* Amenities */}
        <EditableSection title="Amenities" icon={Star}>
          {(editing) => (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {amenityOptions.map(({ label, emoji }) => (
                <button
                  key={label}
                  onClick={() => editing && toggleAmenity(label)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-all text-left',
                    housing.amenities.includes(label)
                      ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-700'
                      : 'bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600',
                    !editing && 'cursor-default'
                  )}
                >
                  <span>{emoji}</span>
                  <span className="truncate">{label}</span>
                  {housing.amenities.includes(label) && (
                    <Check size={12} className="ml-auto shrink-0" />
                  )}
                </button>
              ))}
            </div>
          )}
        </EditableSection>

        {/* Notifications Quick */}
        <EditableSection title="Notifications" icon={Bell}>
          {(editing) => (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Mode</span>
                <Badge variant="secondary">{notifications.mode}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Frequency</span>
                <Badge variant="secondary">{notifications.frequency}</Badge>
              </div>
              {editing && (
                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    Channels
                  </p>
                  {(['Email', 'SMS', 'Push', 'In-app'] as NotificationChannel[]).map((ch) => (
                    <div key={ch} className="flex items-center justify-between">
                      <span className="text-sm text-slate-700 dark:text-slate-300">{ch}</span>
                      <Switch
                        checked={notifications.channels.includes(ch)}
                        onCheckedChange={() => toggleChannel(ch)}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </EditableSection>
      </div>
    </div>
  )
}

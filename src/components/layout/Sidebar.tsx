import {
  Search,
  Settings,
  MessageSquare,
  Bot,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
} from 'lucide-react'
import { useStore } from '../../store/useStore'
import type { DashboardPanel } from '../../types'
import { cn } from '../../lib/utils'

const navItems: { panel: DashboardPanel; icon: React.ElementType; label: string; description: string }[] = [
  { panel: 'match', icon: Search, label: 'Match', description: 'Find properties' },
  { panel: 'preferences', icon: Settings, label: 'Preferences', description: 'Your settings' },
  { panel: 'negotiation', icon: MessageSquare, label: 'Negotiation', description: 'Manage offers' },
  { panel: 'agent', icon: Bot, label: 'Agent', description: 'AI activity' },
]

export function Sidebar() {
  const { activePanel, setActivePanel, sidebarOpen, toggleSidebar, agentStatus, negotiationCart } =
    useStore()

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 transition-all duration-300 shrink-0 z-20',
        sidebarOpen ? 'w-56' : 'w-16'
      )}
    >
      {/* Toggle button */}
      <div className="flex items-center justify-end p-2 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:text-slate-300 dark:hover:bg-slate-800 transition-colors"
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map(({ panel, icon: Icon, label, description }) => {
          const isActive = activePanel === panel
          const badge =
            panel === 'negotiation'
              ? negotiationCart.length
              : panel === 'agent' && agentStatus.isRunning
              ? '●'
              : null

          return (
            <button
              key={panel}
              onClick={() => setActivePanel(panel)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group relative',
                isActive
                  ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
              )}
            >
              <div className="relative shrink-0">
                <Icon size={20} />
                {badge !== null && (
                  <span
                    className={cn(
                      'absolute -top-1 -right-1 min-w-[14px] h-3.5 rounded-full text-[9px] font-bold flex items-center justify-center px-0.5',
                      panel === 'negotiation'
                        ? 'bg-indigo-500 text-white'
                        : 'bg-emerald-500 text-white'
                    )}
                  >
                    {badge}
                  </span>
                )}
              </div>

              {sidebarOpen && (
                <div className="flex-1 text-left overflow-hidden">
                  <div className="text-sm font-medium leading-tight">{label}</div>
                  <div className="text-xs text-slate-400 dark:text-slate-500 truncate">
                    {description}
                  </div>
                </div>
              )}

              {!sidebarOpen && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-xs rounded-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                  {label}
                </div>
              )}
            </button>
          )
        })}
      </nav>

      {/* Stats at bottom when expanded */}
      {sidebarOpen && (
        <div className="p-3 border-t border-slate-200 dark:border-slate-700">
          <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3 space-y-2">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium">
              <TrendingUp size={12} />
              Session Stats
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Matches', value: agentStatus.matchesFound },
                { label: 'Nego.', value: agentStatus.negotiationsActive },
              ].map(({ label, value }) => (
                <div key={label} className="text-center">
                  <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400">
                    {value}
                  </div>
                  <div className="text-[10px] text-slate-400">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}

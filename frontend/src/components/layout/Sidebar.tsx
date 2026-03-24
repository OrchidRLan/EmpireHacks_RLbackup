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
        'flex flex-col border-r border-[rgba(1,2,5,0.10)] dark:border-[rgba(255,215,0,0.15)] bg-white dark:bg-[#0F0F0F] transition-all duration-300 shrink-0 z-20',
        sidebarOpen ? 'w-56' : 'w-16'
      )}
    >
      {/* Toggle button */}
      <div className="flex items-center justify-end p-2 border-b border-[rgba(1,2,5,0.10)] dark:border-[rgba(255,215,0,0.15)]">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg text-[#6B6B6B] dark:text-yellow-400/60 hover:text-[#010205] dark:hover:text-yellow-400 hover:bg-[#F0F0F1] dark:hover:bg-[#1A1A1A] transition-colors"
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
                  ? 'bg-[#010205]/8 text-[#010205] dark:bg-yellow-400/10 dark:text-yellow-400'
                  : 'text-[#6B6B6B] dark:text-yellow-400/50 hover:bg-[#F0F0F1] dark:hover:bg-[#1A1A1A] hover:text-[#010205] dark:hover:text-yellow-400'
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
                  <div className="text-xs text-[#9A9A9A] dark:text-yellow-400/40 truncate">
                    {description}
                  </div>
                </div>
              )}

              {!sidebarOpen && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-[#010205] dark:bg-yellow-400 text-white dark:text-black text-xs rounded-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                  {label}
                </div>
              )}
            </button>
          )
        })}
      </nav>

      {/* Stats at bottom when expanded */}
      {sidebarOpen && (
        <div className="p-3 border-t border-[rgba(1,2,5,0.10)] dark:border-[rgba(255,215,0,0.15)]">
          <div className="rounded-lg bg-[#F0F0F1] dark:bg-[#1A1A1A] p-3 space-y-2">
            <div className="flex items-center gap-1.5 text-xs text-[#6B6B6B] dark:text-yellow-400/60 font-medium">
              <TrendingUp size={12} />
              Session Stats
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Matches', value: agentStatus.matchesFound },
                { label: 'Nego.', value: agentStatus.negotiationsActive },
              ].map(({ label, value }) => (
                <div key={label} className="text-center">
                  <div className="text-lg font-bold text-[#6A5CFF] dark:text-yellow-400">
                    {value}
                  </div>
                  <div className="text-[10px] text-[#9A9A9A] dark:text-yellow-400/40">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}

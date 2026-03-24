import { useState, useRef, useEffect } from 'react'
import { LogOut, Settings, ChevronDown } from 'lucide-react'
import rentoLogo from '../../assets/image/rento_logo.png'
import { useStore } from '../../store/useStore'
import { clearToken } from '../../lib/api'
import { cn } from '../../lib/utils'
import { useNavigate } from 'react-router-dom'

export function Navbar() {
  const {
    topTab, setTopTab,
    setPrefModal,
    userName, userEmail,
  } = useStore()

  const [userOpen, setUserOpen] = useState(false)
  const userRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (userRef.current && !userRef.current.contains(e.target as Node)) setUserOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <header className="h-16 flex items-center justify-between px-6 shrink-0 z-30 relative">
      {/* Logo */}
      <div
        className="flex items-center gap-2 cursor-pointer"
        onClick={() => navigate('/dashboard')}
      >
        <img src={rentoLogo} alt="Rento" style={{ height: 28 }} />
        <span
          className="font-bold text-base text-white tracking-widest uppercase"
          style={{ fontFamily: "'Sakana', sans-serif" }}
        >
          RENTO
        </span>
      </div>

      {/* Center — top-level tabs */}
      <nav className="flex items-center gap-10 absolute left-1/2 -translate-x-1/2">
        {(['match', 'agent'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setTopTab(tab)}
            className={cn(
              'relative pb-1.5 text-sm font-semibold transition-all duration-150',
              topTab === tab
                ? 'text-white'
                : 'text-white/45 hover:text-white/70'
            )}
          >
            {tab === 'match' ? 'Match' : 'Agent Log'}
            {topTab === tab && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-white rounded-full" />
            )}
          </button>
        ))}
      </nav>

      {/* Right: avatar */}
      <div className="relative" ref={userRef}>
        <button
          onClick={() => setUserOpen(v => !v)}
          className="flex items-center gap-1.5"
        >
          <div className="w-9 h-9 rounded-full bg-[#6A5CFF] flex items-center justify-center text-white font-semibold text-sm shadow-lg shadow-[#6A5CFF]/30">
            {(userName ?? 'A').charAt(0).toUpperCase()}
          </div>
          <ChevronDown size={13} className="text-white/40" />
        </button>

        {userOpen && (
          <div className="absolute right-0 top-11 w-56 bg-[#0F1428] rounded-xl shadow-xl border border-white/10 z-50 overflow-hidden">
            {/* User info */}
            <div className="px-4 py-3 border-b border-white/10">
              <p className="text-sm font-semibold text-white">{userName ?? 'Alex Kim'}</p>
              <p className="text-xs text-white/40">{userEmail ?? 'alex@example.com'}</p>
            </div>

            {/* Preferences */}
            <div className="py-1">
              <p className="px-4 pt-2 pb-1 text-[10px] font-semibold text-white/30 uppercase tracking-wider">
                Preferences
              </p>
              {([
                { tab: 'housing', label: '🏠 Housing' },
                { tab: 'negotiation', label: '🤝 Negotiation' },
                { tab: 'notifications', label: '🔔 Notifications' },
              ] as const).map(({ tab, label }) => (
                <button
                  key={tab}
                  onClick={() => { setPrefModal(true, tab); setUserOpen(false) }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-white/60 hover:bg-white/10 hover:text-white transition-colors"
                >
                  <Settings size={13} className="text-white/30" />
                  {label}
                </button>
              ))}
            </div>

            <div className="border-t border-white/10 py-1">
              <button
                onClick={() => { clearToken(); navigate('/onboarding') }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <LogOut size={13} />
                Sign out
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

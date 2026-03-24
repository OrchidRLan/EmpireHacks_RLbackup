import { useStore } from '../../store/useStore'
import { Navbar } from '../../components/layout/Navbar'
import { PreferencesModal } from '../../components/layout/PreferencesModal'
import { Match } from './Match'
import { AgentLog } from './AgentLog'
import bgBlue from '../../assets/image/bg_blue.png'

export function DashboardPage() {
  const { topTab } = useStore()

  return (
    <div
      className="h-screen flex flex-col overflow-hidden relative"
      style={{
        backgroundImage: `url(${bgBlue})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
      }}
    >
      <div className="flex-1 flex flex-col overflow-hidden px-10">
        <Navbar />
        <main className="flex-1 overflow-hidden relative z-10">
          {topTab === 'match' && <Match />}
          {topTab === 'agent' && <AgentLog />}
        </main>
      </div>
      <PreferencesModal />
    </div>
  )
}

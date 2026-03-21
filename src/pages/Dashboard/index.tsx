import { useStore } from '../../store/useStore'
import { Navbar } from '../../components/layout/Navbar'
import { PreferencesModal } from '../../components/layout/PreferencesModal'
import { PanelMatch } from './PanelMatch'
import { PanelAgent } from './PanelAgent'

export function DashboardPage() {
  const { topTab } = useStore()

  return (
    <div className="h-screen flex flex-col bg-slate-50 dark:bg-slate-900 overflow-hidden">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        {topTab === 'match' && <PanelMatch />}
        {topTab === 'agent' && <PanelAgent />}
      </main>
      <PreferencesModal />
    </div>
  )
}

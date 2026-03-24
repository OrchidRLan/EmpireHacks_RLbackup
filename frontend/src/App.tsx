import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useStore } from './store/useStore'
import { OnboardingPage } from './pages/Onboarding'
import { DashboardPage } from './pages/Dashboard'

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { darkMode } = useStore()

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  return <>{children}</>
}

function App() {
  const { initAuth, authLoading, loadAgentStatus, loadNotifications } = useStore()

  // Initialize authentication on mount
  useEffect(() => {
    initAuth()
  }, [initAuth])

  // Poll agent status and notifications every 15 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadAgentStatus()
      loadNotifications()
    }, 15_000)
    return () => clearInterval(interval)
  }, [loadAgentStatus, loadNotifications])

  if (authLoading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: '#0A0F23',
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            border: '3px solid rgba(106, 92, 255, 0.3)',
            borderTopColor: '#6A5CFF',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <ThemeProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/onboarding" replace />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="*" element={<Navigate to="/onboarding" replace />} />
        </Routes>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App

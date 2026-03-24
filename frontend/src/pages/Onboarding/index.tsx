import { useState } from 'react'
import { useStore } from '../../store/useStore'
import { Hero } from './Hero'
import { PreferenceSetting, type Tab } from './PreferenceSetting'
import { CompletionScreen } from './CompletionScreen'

const TABS: Tab[] = ['housing', 'negotiation', 'notifications']

export function OnboardingPage() {
  const { onboardingStep, setOnboardingStep } = useStore()
  const [activeTab, setActiveTab] = useState<Tab>('housing')
  const isComplete = onboardingStep > 3

  const scrollToForm = () => {
    document.getElementById('ob-form-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  const scrollToTop = () => {
    document.getElementById('ob-form-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleNext = () => {
    const idx = TABS.indexOf(activeTab)
    if (idx < TABS.length - 1) {
      setActiveTab(TABS[idx + 1])
      scrollToTop()
    } else {
      setOnboardingStep(4)
    }
  }

  const handleBack = () => {
    const idx = TABS.indexOf(activeTab)
    if (idx > 0) {
      setActiveTab(TABS[idx - 1])
      scrollToTop()
    }
  }

  return (
    <div style={{ overflowX: 'hidden' }}>
      <Hero onGetStarted={scrollToForm} />

      {/* ════════════════════════════════════════
          PREFERENCES DARK SECTION
      ════════════════════════════════════════ */}
      <section
        id="ob-form-section"
        style={{
          background: 'linear-gradient(160deg, #0B1627 0%, #101e38 60%, #0d1a30 100%)',
          padding: '72px 24px 96px',
          minHeight: '60vh',
        }}
      >
        {isComplete ? (
          <div
            style={{
              maxWidth: 720,
              margin: '0 auto',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.09)',
              borderRadius: 20,
              padding: 40,
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
            }}
          >
            <div className="ob ob-glass">
              <CompletionScreen />
            </div>
          </div>
        ) : (
          <>
            <PreferenceSetting
              activeTab={activeTab}
              onTabChange={setActiveTab}
              onBack={handleBack}
              onNext={handleNext}
              isFirstTab={activeTab === 'housing'}
              isLastTab={activeTab === 'notifications'}
            />
          </>
        )}
      </section>
    </div>
  )
}

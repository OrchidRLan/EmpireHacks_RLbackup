import { useStore } from '../../store/useStore'
import { Step1Housing } from './Step1Housing'
import { Step2Negotiation } from './Step2Negotiation'
import { Step3Notifications } from './Step3Notifications'
import { CompletionScreen } from './CompletionScreen'

const STEPS = [
  { num: 1, label: 'My Preferences' },
  { num: 2, label: 'AI Negotiation' },
  { num: 3, label: 'Notifications' },
]

export function OnboardingPage() {
  const { onboardingStep, setOnboardingStep } = useStore()

  const isComplete = onboardingStep > 3
  const progressPct = isComplete ? 100 : Math.round((onboardingStep / 3) * 100)

  const goStep = (n: number) => {
    setOnboardingStep(Math.min(4, Math.max(1, n)))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="ob">
      <div className="ob-inner">

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 48 }} className="ob-anim-fade-down">
          <div className="ob-logo">
            <span className="ob-logo-dot" />
            FINDHOME AI
            <span className="ob-logo-dot" />
          </div>
          <h1 className="ob-h1">Find your perfect home</h1>
          <p className="ob-subtitle">
            Three quick steps — then let AI match, negotiate, and keep you posted.
          </p>
        </div>

        {/* Progress bar */}
        <div className="ob-progress-track ob-anim-fade-down">
          <div className="ob-progress-fill" style={{ width: `${progressPct}%` }} />
        </div>

        {/* Step nav */}
        {!isComplete && (
          <div className="ob-steps-nav ob-anim-fade-down">
            {STEPS.map(({ num, label }) => {
              const isDone = num < onboardingStep
              const isActive = num === onboardingStep
              return (
                <button
                  key={num}
                  className={`ob-step-btn${isActive ? ' ob-active' : isDone ? ' ob-done' : ''}`}
                  onClick={() => isDone ? goStep(num) : undefined}
                >
                  <span className="ob-step-num">{isDone ? '✓' : num}</span>
                  {label}
                </button>
              )
            })}
          </div>
        )}

        {/* Panel */}
        <div className="ob-anim-fade-up">
          {isComplete ? (
            <CompletionScreen />
          ) : onboardingStep === 1 ? (
            <Step1Housing />
          ) : onboardingStep === 2 ? (
            <Step2Negotiation />
          ) : (
            <Step3Notifications />
          )}
        </div>

        {/* Bottom nav */}
        {!isComplete && (
          <div className="ob-bottom-nav ob-anim-fade-up">
            <button
              className="ob-btn ob-btn-ghost"
              onClick={() => goStep(onboardingStep - 1)}
              disabled={onboardingStep === 1}
            >
              ← Back
            </button>
            <button
              className={`ob-btn ${onboardingStep === 3 ? 'ob-btn-success' : 'ob-btn-primary'}`}
              onClick={() => goStep(onboardingStep + 1)}
            >
              {onboardingStep === 3 ? 'Finish setup →' : 'Next →'}
            </button>
          </div>
        )}

      </div>
    </div>
  )
}

import { useState } from 'react'
import { api } from '../api'
import './OnboardingPage.css'

export default function OnboardingPage({ onComplete }) {
  const [step, setStep] = useState(0) // 0 = welcome, 1 = goal selection
  const [selectedGoal, setSelectedGoal] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const goals = [
    { label: 'Похудеть', calories: 1500, icon: '🔥', desc: '1500 ккал/день' },
    { label: 'Поддержать вес', calories: 2000, icon: '⚖️', desc: '2000 ккал/день' },
    { label: 'Набрать массу', calories: 2500, icon: '💪', desc: '2500 ккал/день' },
  ]

  const handleGoalSelect = async (calories) => {
    setSelectedGoal(calories)
    setSubmitting(true)
    try {
      await api.setGoal(calories)
      // небольшая задержка для UX
      setTimeout(() => onComplete(), 600)
    } catch (e) {
      console.error('Failed to set goal:', e)
    } finally {
      setSubmitting(false)
    }
  }

  if (step === 0) {
    return (
      <div className="onboarding">
        <div className="onboarding__welcome">
          <div className="onboarding__emoji">🥗</div>
          <h1 className="onboarding__title">Привет!</h1>
          <p className="onboarding__subtitle">
            Я помогу тебе считать калории.<br />
            Просто отправь фото еды, голосовое или напиши что съел — я всё посчитаю.
          </p>
          <button className="onboarding__start-btn" onClick={() => setStep(1)}>
            Начать
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="onboarding">
      <div className="onboarding__goals">
        <h2 className="onboarding__goals-title">Выбери свою цель</h2>
        <div className="onboarding__goals-list">
          {goals.map(goal => {
            const isActive = selectedGoal === goal.calories
            const isSubmitting = submitting && isActive
            return (
              <button
                key={goal.calories}
                className={`onboarding__goal-card ${isActive ? 'onboarding__goal-card--active' : ''}`}
                onClick={() => handleGoalSelect(goal.calories)}
                disabled={submitting}
              >
                <div className="onboarding__goal-icon">{goal.icon}</div>
                <div className="onboarding__goal-info">
                  <div className="onboarding__goal-label">{goal.label}</div>
                  <div className="onboarding__goal-desc">{goal.desc}</div>
                </div>
                {isSubmitting && <div className="onboarding__goal-spinner">⏳</div>}
                {isActive && !submitting && <div className="onboarding__goal-check">✓</div>}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

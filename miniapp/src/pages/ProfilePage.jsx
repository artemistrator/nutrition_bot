import { useState, useEffect } from 'react'
import { api } from '../api'
import './ProfilePage.css'

const GOALS = [
  { label: 'Похудеть', calories: 1500, icon: '🔥' },
  { label: 'Поддержать вес', calories: 2000, icon: '⚖️' },
  { label: 'Набрать массу', calories: 2500, icon: '💪' },
]

export default function ProfilePage() {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(null) // calories being updated

  const loadProfile = async () => {
    try {
      const { data } = await api.getProfile()
      setProfile(data)
    } catch (e) {
      console.error('Failed to load profile:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProfile() }, [])

  const handleGoalSelect = async (calories) => {
    setUpdating(calories)
    try {
      await api.setGoal(calories)
      await loadProfile()
    } catch (e) {
      console.error('Failed to update goal:', e)
    } finally {
      setUpdating(null)
    }
  }

  if (loading) return <div className="profile-page profile-page--loading">Загрузка...</div>

  const currentGoal = profile?.goal_calories || 0

  return (
    <div className="profile-page">
      <div className="profile-card">
        <div className="profile-card__avatar">👤</div>
        <div className="profile-card__name">
          {profile?.username || 'Пользователь'}
        </div>
        <div className="profile-card__subtitle">
          Цель: <strong>{currentGoal || 'не задана'}</strong> ккал/день
        </div>
      </div>

      <div className="goals-section">
        <h3 className="goals-section__title">Выбери цель</h3>
        <div className="goals-grid">
          {GOALS.map(goal => {
            const isActive = currentGoal === goal.calories
            const isUpdating = updating === goal.calories
            return (
              <button
                key={goal.calories}
                className={`goal-card ${isActive ? 'goal-card--active' : ''}`}
                onClick={() => handleGoalSelect(goal.calories)}
                disabled={updating !== null}
              >
                <div className="goal-card__icon">{goal.icon}</div>
                <div className="goal-card__label">{goal.label}</div>
                <div className="goal-card__value">
                  {isUpdating ? '⏳' : `${goal.calories} ккал`}
                </div>
                {isActive && !isUpdating && (
                  <div className="goal-card__badge">✓ Активна</div>
                )}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

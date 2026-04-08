import { useMemo, useState } from 'react'
import { api } from '../api'
import {
  ACTIVITY_OPTIONS,
  GOAL_OPTIONS,
  SEX_OPTIONS,
  createProfileForm,
} from '../profileOptions'
import './OnboardingPage.css'

export default function OnboardingPage({ profile, onComplete }) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(() => createProfileForm(profile))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const currentGoal = useMemo(() => {
    return GOAL_OPTIONS.find(option => option.value === form.goal_type)
  }, [form.goal_type])

  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        sex: form.sex || null,
        age: form.age === '' ? null : Number(form.age),
        height_cm: form.height_cm === '' ? null : Number(form.height_cm),
        weight_kg: form.weight_kg === '' ? null : Number(form.weight_kg),
        activity_level: form.activity_level || null,
        goal_type: form.goal_type || null,
      }
      const { data } = await api.updateProfile(payload)
      onComplete(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось сохранить профиль.')
      console.error('Failed to update profile:', e)
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
            Заполни короткий профиль, и я посчитаю твою персональную норму калорий.
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
      <div className="onboarding__form-card">
        <h2 className="onboarding__form-title">Настроим цель</h2>
        <p className="onboarding__form-subtitle">
          Всё посчитается на backend и сохранится в общий профиль.
        </p>

        <div className="profile-form">
          <div className="profile-form__section">
            <div className="profile-form__label">Пол</div>
            <div className="profile-form__chips">
              {SEX_OPTIONS.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={`profile-form__chip ${form.sex === option.value ? 'profile-form__chip--active' : ''}`}
                  onClick={() => updateField('sex', option.value)}
                >
                  <span>{option.icon}</span>
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="profile-form__grid">
            <label className="profile-form__field">
              <span>Возраст</span>
              <input
                type="number"
                min="10"
                max="100"
                value={form.age}
                onChange={e => updateField('age', e.target.value)}
                placeholder="28"
              />
            </label>
            <label className="profile-form__field">
              <span>Рост, см</span>
              <input
                type="number"
                min="100"
                max="250"
                value={form.height_cm}
                onChange={e => updateField('height_cm', e.target.value)}
                placeholder="178"
              />
            </label>
            <label className="profile-form__field">
              <span>Вес, кг</span>
              <input
                type="number"
                min="30"
                max="300"
                step="0.1"
                value={form.weight_kg}
                onChange={e => updateField('weight_kg', e.target.value)}
                placeholder="72.5"
              />
            </label>
          </div>

          <div className="profile-form__section">
            <div className="profile-form__label">Активность</div>
            <div className="profile-form__stack">
              {ACTIVITY_OPTIONS.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={`profile-form__choice ${form.activity_level === option.value ? 'profile-form__choice--active' : ''}`}
                  onClick={() => updateField('activity_level', option.value)}
                >
                  <strong>{option.label}</strong>
                  <span>{option.description}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="profile-form__section">
            <div className="profile-form__label">Цель</div>
            <div className="profile-form__chips">
              {GOAL_OPTIONS.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={`profile-form__chip ${form.goal_type === option.value ? 'profile-form__chip--active' : ''}`}
                  onClick={() => updateField('goal_type', option.value)}
                >
                  <span>{option.icon}</span>
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {currentGoal && (
          <div className="onboarding__hint">
            {currentGoal.icon} Цель: {currentGoal.label}
          </div>
        )}

        {error && <div className="onboarding__error">{error}</div>}

        <button className="onboarding__submit-btn" onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Сохраняю...' : 'Сохранить профиль'}
        </button>
      </div>
    </div>
  )
}

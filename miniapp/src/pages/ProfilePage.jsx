import { useEffect, useState } from 'react'
import { api } from '../api'
import {
  ACTIVITY_OPTIONS,
  GOAL_OPTIONS,
  SEX_OPTIONS,
  createProfileForm,
  profileGoalLabel,
} from '../profileOptions'
import './ProfilePage.css'

export default function ProfilePage() {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState(() => createProfileForm())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadProfile = async () => {
    try {
      const { data } = await api.getProfile()
      setProfile(data)
      setForm(createProfileForm(data))
    } catch (e) {
      console.error('Failed to load profile:', e)
      setError('Не удалось загрузить профиль.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProfile() }, [])

  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
    setSuccess('')
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSuccess('')
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
      setProfile(data)
      setForm(createProfileForm(data))
      setSuccess('Профиль обновлён.')
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось обновить профиль.')
      console.error('Failed to update profile:', e)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="profile-page profile-page--loading">Загрузка...</div>

  const goalCalories = profile?.goal_calories

  return (
    <div className="profile-page">
      <div className="profile-card">
        <div className="profile-card__avatar">👤</div>
        <div className="profile-card__name">{profile?.username || 'Пользователь'}</div>
        <div className="profile-card__subtitle">{profileGoalLabel(form.goal_type)}</div>
        <div className="profile-card__goal">
          {goalCalories ? `Твоя цель: ${goalCalories} ккал/день` : 'Заполни профиль, чтобы рассчитать цель'}
        </div>
      </div>

      <div className="profile-editor">
        <div className="profile-editor__section">
          <div className="profile-editor__label">Пол</div>
          <div className="profile-editor__chips">
            {SEX_OPTIONS.map(option => (
              <button
                key={option.value}
                type="button"
                className={`profile-chip ${form.sex === option.value ? 'profile-chip--active' : ''}`}
                onClick={() => updateField('sex', option.value)}
              >
                <span>{option.icon}</span>
                <span>{option.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="profile-editor__grid">
          <label className="profile-input">
            <span>Возраст</span>
            <input
              type="number"
              min="10"
              max="100"
              value={form.age}
              onChange={e => updateField('age', e.target.value)}
            />
          </label>
          <label className="profile-input">
            <span>Рост, см</span>
            <input
              type="number"
              min="100"
              max="250"
              value={form.height_cm}
              onChange={e => updateField('height_cm', e.target.value)}
            />
          </label>
          <label className="profile-input">
            <span>Вес, кг</span>
            <input
              type="number"
              min="30"
              max="300"
              step="0.1"
              value={form.weight_kg}
              onChange={e => updateField('weight_kg', e.target.value)}
            />
          </label>
        </div>

        <div className="profile-editor__section">
          <div className="profile-editor__label">Активность</div>
          <div className="profile-editor__stack">
            {ACTIVITY_OPTIONS.map(option => (
              <button
                key={option.value}
                type="button"
                className={`profile-choice ${form.activity_level === option.value ? 'profile-choice--active' : ''}`}
                onClick={() => updateField('activity_level', option.value)}
              >
                <strong>{option.label}</strong>
                <span>{option.description}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="profile-editor__section">
          <div className="profile-editor__label">Цель</div>
          <div className="profile-editor__chips">
            {GOAL_OPTIONS.map(option => (
              <button
                key={option.value}
                type="button"
                className={`profile-chip ${form.goal_type === option.value ? 'profile-chip--active' : ''}`}
                onClick={() => updateField('goal_type', option.value)}
              >
                <span>{option.icon}</span>
                <span>{option.label}</span>
              </button>
            ))}
          </div>
        </div>

        {error && <div className="profile-editor__error">{error}</div>}
        {success && <div className="profile-editor__success">{success}</div>}

        <button className="profile-editor__save" onClick={handleSave} disabled={saving}>
          {saving ? 'Сохраняю...' : 'Сохранить изменения'}
        </button>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { api } from '../api'
import './DiaryPage.css'

const QUICK_FOODS = [
  { label: '☕ Кофе', text: 'кофе с молоком 200мл' },
  { label: '🍌 Банан', text: 'банан 1 штука' },
  { label: '🥚 Яйцо', text: 'варёное яйцо 1 штука' },
  { label: '🍞 Хлеб', text: 'хлеб белый 1 кусок 30г' },
  { label: '🥛 Молоко', text: 'молоко 200мл' },
  { label: '🍚 Рис', text: 'рис варёный 150г' },
  { label: '🍗 Курица', text: 'куриная грудка варёная 150г' },
]

const QUICK_ACTIVITIES = [
  { label: '🚶 Ходьба', text: 'ходьба 30 минут' },
  { label: '🚴 Велосипед', text: 'велосипед 30 минут' },
  { label: '🏃 Бег', text: 'бег 20 минут' },
  { label: '🏋️ Зал', text: 'силовая тренировка 45 минут' },
  { label: '🧘 Йога', text: 'йога 40 минут' },
]

export default function DiaryPage() {
  const [todayData, setTodayData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [inputMode, setInputMode] = useState(null) // 'text' | 'photo' | 'quick-food' | 'quick-activity' | 'activity-text' | null
  const [inputValue, setInputValue] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [activeTab, setActiveTab] = useState('food') // 'food' | 'activity'
  const [activityResult, setActivityResult] = useState(null)

  const loadToday = async () => {
    try {
      const { data } = await api.getTodayMeals()
      setTodayData(data)
    } catch (e) {
      console.error('Failed to load today meals:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadToday() }, [])

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    await analyzePhoto(file)
  }

  const analyzePhoto = async (file) => {
    setAnalyzing(true)
    setAnalysisResult(null)
    try {
      const { data } = await api.analyzePhoto(file)
      setAnalysisResult(data)
    } catch (e) {
      console.error('Photo analysis failed:', e)
      setAnalysisResult({ description: 'Ошибка анализа', calories: 0, protein: 0, fat: 0, carbs: 0 })
    } finally {
      setAnalyzing(false)
    }
  }

  const analyzeText = async (text) => {
    const textToAnalyze = text || inputValue.trim()
    if (!textToAnalyze) return
    setAnalyzing(true)
    setAnalysisResult(null)
    try {
      const { data } = await api.analyzeText(textToAnalyze)
      setAnalysisResult(data)
    } catch (e) {
      console.error('Text analysis failed:', e)
      setAnalysisResult({ description: 'Ошибка анализа', calories: 0, protein: 0, fat: 0, carbs: 0 })
    } finally {
      setAnalyzing(false)
    }
  }

  const analyzeActivityText = async (text) => {
    const textToAnalyze = text || inputValue.trim()
    if (!textToAnalyze) return
    setAnalyzing(true)
    setActivityResult(null)
    try {
      const { data } = await api.analyzeActivity(textToAnalyze)
      setActivityResult(data)
    } catch (e) {
      console.error('Activity analysis failed:', e)
      setActivityResult({ description: 'Ошибка анализа', calories_burned: 0, duration_minutes: 0 })
    } finally {
      setAnalyzing(false)
    }
  }

  const saveMeal = async () => {
    if (!analysisResult) return
    try {
      await api.addMeal({
        description: analysisResult.description || 'Приём пищи',
        calories: analysisResult.calories || 0,
        protein: analysisResult.protein || 0,
        fat: analysisResult.fat || 0,
        carbs: analysisResult.carbs || 0,
      })
      setShowModal(false)
      resetModal()
      loadToday()
    } catch (e) {
      console.error('Failed to save meal:', e)
    }
  }

  const saveActivity = async () => {
    if (!activityResult) return
    try {
      await api.addActivity({
        description: activityResult.description || 'Активность',
        calories_burned: activityResult.calories_burned || 0,
        duration_minutes: activityResult.duration_minutes || null,
      })
      setShowModal(false)
      resetModal()
      loadToday()
    } catch (e) {
      console.error('Failed to save activity:', e)
    }
  }

  const resetModal = () => {
    setInputMode(null)
    setInputValue('')
    setAnalysisResult(null)
    setActivityResult(null)
    setAnalyzing(false)
  }

  const openModal = (mode) => {
    setInputMode(mode)
    setShowModal(true)
  }

  const handleQuickFood = (text) => {
    setInputMode('quick-food')
    setShowModal(true)
    analyzeText(text)
  }

  const handleQuickActivity = (text) => {
    setInputMode('quick-activity')
    setShowModal(true)
    analyzeActivityText(text)
  }

  const goal = todayData?.goal_calories || 0
  const totalCalories = todayData?.totals?.calories || 0
  const totalBurned = todayData?.total_burned || 0
  const netCalories = todayData?.net_calories ?? totalCalories
  const progress = goal > 0 ? Math.min((netCalories / goal) * 100, 100) : 0
  const remaining = Math.max(goal - netCalories, 0)
  const meals = todayData?.meals || []
  const activities = todayData?.activities || []
  const hasActivities = activities.length > 0

  if (loading) return <div className="diary-page diary-page--loading">Загрузка...</div>

  return (
    <div className="diary-page">
      {/* Calorie ring */}
      <div className="calorie-ring-card">
        <div className="calorie-ring">
          <svg viewBox="0 0 120 120" className="calorie-ring__svg">
            <circle cx="60" cy="60" r="52" fill="none" stroke="#e5e7eb" strokeWidth="10" />
            <circle
              cx="60" cy="60" r="52" fill="none" stroke="#3b82f6" strokeWidth="10"
              strokeDasharray={`${2 * Math.PI * 52}`}
              strokeDashoffset={`${2 * Math.PI * 52 * (1 - progress / 100)}`}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
              className="calorie-ring__progress"
            />
          </svg>
          <div className="calorie-ring__text">
            <div className="calorie-ring__value">{netCalories.toFixed(0)}</div>
            <div className="calorie-ring__goal">{goal ? `/ ${goal} ккал` : 'цель не задана'}</div>
          </div>
        </div>
        <div className="calorie-ring__macros">
          <span>Б: {todayData?.totals?.protein?.toFixed(0) || 0}г</span>
          <span>Ж: {todayData?.totals?.fat?.toFixed(0) || 0}г</span>
          <span>У: {todayData?.totals?.carbs?.toFixed(0) || 0}г</span>
        </div>
        {hasActivities && (
          <div className="calorie-ring__burned">
            🏃 Сожжено: {totalBurned.toFixed(0)} ккал
          </div>
        )}
        <div className="calorie-ring__remaining">
          {goal ? `Осталось: ${remaining.toFixed(0)} ккал` : 'Заполни профиль, чтобы увидеть цель'}
        </div>
      </div>

      {/* Quick actions */}
      <div className="quick-actions">
        <div className="quick-actions__tabs">
          <button
            className={`quick-actions__tab ${activeTab === 'food' ? 'quick-actions__tab--active' : ''}`}
            onClick={() => setActiveTab('food')}
          >
            🍽 Еда
          </button>
          <button
            className={`quick-actions__tab ${activeTab === 'activity' ? 'quick-actions__tab--active' : ''}`}
            onClick={() => setActiveTab('activity')}
          >
            🏃 Активность
          </button>
        </div>
        <div className="quick-actions__scroll">
          {(activeTab === 'food' ? QUICK_FOODS : QUICK_ACTIVITIES).map(qf => (
            <button
              key={qf.label}
              className="quick-actions__pill"
              onClick={() => activeTab === 'food' ? handleQuickFood(qf.text) : handleQuickActivity(qf.text)}
            >
              {qf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Meals list */}
      <div className="meals-section">
        <h3 className="meals-section__title">Приёмы пищи</h3>
        {meals.length === 0 ? (
          <div className="meals-section__empty">
            Ещё ничего не записано. Нажми + чтобы добавить!
          </div>
        ) : (
          meals.map((meal, i) => {
            const time = meal.created_at ? meal.created_at.slice(11, 16) : '--:--'
            return (
              <div key={meal.id || i} className="meal-card">
                <div className="meal-card__header">
                  <span className="meal-card__time">{time}</span>
                  <span className="meal-card__calories">{meal.calories.toFixed(0)} ккал</span>
                </div>
                <div className="meal-card__desc">{meal.description}</div>
                <div className="meal-card__macros">
                  Б {meal.protein.toFixed(0)} · Ж {meal.fat.toFixed(0)} · У {meal.carbs.toFixed(0)}
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Activities list */}
      {activities.length > 0 && (
        <div className="activities-section">
          <h3 className="activities-section__title">Активности</h3>
          {activities.map((act, i) => {
            const time = act.created_at ? act.created_at.slice(11, 16) : '--:--'
            return (
              <div key={act.id || i} className="activity-card">
                <div className="activity-card__header">
                  <span className="activity-card__time">{time}</span>
                  <span className="activity-card__burned">−{act.calories_burned.toFixed(0)} ккал</span>
                </div>
                <div className="activity-card__desc">{act.description}</div>
                {act.duration_minutes && (
                  <div className="activity-card__duration">⏱ {act.duration_minutes} мин</div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* FAB */}
      <button className="fab" onClick={() => openModal('choice')}>+</button>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => { setShowModal(false); resetModal() }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3 className="modal__title">
              {inputMode === 'quick-food' ? 'Быстрый ввод' :
               inputMode === 'quick-activity' ? 'Быстрая активность' :
               'Добавить'}
            </h3>

            {inputMode === 'choice' && (
              <div className="modal__choices">
                <button className="modal__choice-btn" onClick={() => openModal('text')}>
                  🍽 Добавить еду
                </button>
                <button className="modal__choice-btn" onClick={() => openModal('activity-text')}>
                  🏃 Добавить активность
                </button>
                <button className="modal__choice-btn" onClick={() => openModal('photo')}>
                  📷 Загрузить фото
                </button>
              </div>
            )}

            {inputMode === 'text' && !analysisResult && (
              <div className="modal__input-area">
                <textarea
                  className="modal__textarea"
                  placeholder="Опиши что ты съел, например: тарелка борща с хлебом"
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  rows={3}
                />
                <button className="modal__analyze-btn" onClick={() => analyzeText()} disabled={analyzing}>
                  {analyzing ? '⏳ Анализирую...' : 'Анализировать'}
                </button>
              </div>
            )}

            {inputMode === 'activity-text' && !activityResult && (
              <div className="modal__input-area">
                <textarea
                  className="modal__textarea"
                  placeholder="Опиши активность, например: 30 минут бега"
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  rows={3}
                />
                <button className="modal__analyze-btn" onClick={() => analyzeActivityText()} disabled={analyzing}>
                  {analyzing ? '⏳ Анализирую...' : 'Анализировать'}
                </button>
              </div>
            )}

            {inputMode === 'photo' && !analysisResult && (
              <div className="modal__photo-area">
                <label className="modal__photo-btn">
                  📷 Выбрать фото
                  <input type="file" accept="image/*" onChange={handleFileChange} hidden />
                </label>
                {analyzing && <p className="modal__loading">⏳ Анализирую фото...</p>}
              </div>
            )}

            {(inputMode === 'quick-food' || inputMode === 'quick-activity') && analyzing && (
              <p className="modal__loading">⏳ Анализирую...</p>
            )}

            {analysisResult && (
              <div className="modal__result">
                <div className="modal__result-name">{analysisResult.description}</div>
                <div className="modal__result-macros">
                  <span>🔥 {analysisResult.calories?.toFixed(0)} ккал</span>
                  <span>Б: {analysisResult.protein?.toFixed(0)}г</span>
                  <span>Ж: {analysisResult.fat?.toFixed(0)}г</span>
                  <span>У: {analysisResult.carbs?.toFixed(0)}г</span>
                </div>
                <div className="modal__result-actions">
                  <button className="modal__cancel-btn" onClick={() => { setShowModal(false); resetModal() }}>
                    Отмена
                  </button>
                  <button className="modal__save-btn" onClick={saveMeal}>
                    Сохранить
                  </button>
                </div>
              </div>
            )}

            {activityResult && (
              <div className="modal__result">
                <div className="modal__result-name">{activityResult.description}</div>
                <div className="modal__result-macros">
                  <span>🔥 −{activityResult.calories_burned?.toFixed(0)} ккал</span>
                  {activityResult.duration_minutes && (
                    <span>⏱ {activityResult.duration_minutes} мин</span>
                  )}
                </div>
                <div className="modal__result-actions">
                  <button className="modal__cancel-btn" onClick={() => { setShowModal(false); resetModal() }}>
                    Отмена
                  </button>
                  <button className="modal__save-btn modal__save-btn--green" onClick={saveActivity}>
                    Сохранить
                  </button>
                </div>
              </div>
            )}

            {!analysisResult && !activityResult && inputMode && inputMode !== 'choice' && inputMode !== 'quick-food' && inputMode !== 'quick-activity' && (
              <button className="modal__back-btn" onClick={resetModal}>← Назад</button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

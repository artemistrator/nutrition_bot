import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend } from 'recharts'
import { api } from '../api'
import './StatsPage.css'

export default function StatsPage() {
  const [days, setDays] = useState(7)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  const loadHistory = async () => {
    setLoading(true)
    try {
      const { data } = await api.getHistory(days)
      setHistory(data.days || [])
    } catch (e) {
      console.error('Failed to load history:', e)
      setHistory([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadHistory() }, [days])

  const avgCalories = history.length > 0
    ? Math.round(history.reduce((s, d) => s + (d.calories || 0), 0) / history.length)
    : 0

  const avgBurned = history.length > 0
    ? Math.round(history.reduce((s, d) => s + (d.calories_burned || 0), 0) / history.length)
    : 0

  // Reverse for chart (oldest first)
  const chartData = [...history].reverse().map(d => ({
    ...d,
    calories_burned: d.calories_burned || 0,
  }))

  return (
    <div className="stats-page">
      <div className="stats-page__header">
        <h2>Статистика</h2>
        <div className="stats-page__toggle">
          <button
            className={`stats-page__toggle-btn ${days === 7 ? 'stats-page__toggle-btn--active' : ''}`}
            onClick={() => setDays(7)}
          >
            7 дней
          </button>
          <button
            className={`stats-page__toggle-btn ${days === 30 ? 'stats-page__toggle-btn--active' : ''}`}
            onClick={() => setDays(30)}
          >
            30 дней
          </button>
        </div>
      </div>

      {loading ? (
        <div className="stats-page__loading">Загрузка...</div>
      ) : chartData.length === 0 ? (
        <div className="stats-page__empty">Нет данных за выбранный период</div>
      ) : (
        <>
          <div className="stats-page__chart-card">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(val, name) => {
                    const label = name === 'calories' ? 'Съедено' : 'Сожжено'
                    return [`${val} ккал`, label]
                  }}
                  labelFormatter={(label) => label}
                />
                <Legend
                  formatter={(value) => value === 'calories' ? 'Съедено' : 'Сожжено'}
                  wrapperStyle={{ fontSize: 13 }}
                />
                <Bar dataKey="calories" name="calories" radius={[4, 4, 0, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={`e${i}`} fill="#3b82f6" />
                  ))}
                </Bar>
                <Bar dataKey="calories_burned" name="calories_burned" radius={[4, 4, 0, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={`b${i}`} fill="#22c55e" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="stats-page__summary">
            <div className="stats-page__summary-item">
              <div className="stats-page__summary-value" style={{color: '#3b82f6'}}>{avgCalories}</div>
              <div className="stats-page__summary-label">Среднее съедено ккал/день</div>
            </div>
            <div className="stats-page__summary-item">
              <div className="stats-page__summary-value" style={{color: '#22c55e'}}>{avgBurned}</div>
              <div className="stats-page__summary-label">Среднее сожжено ккал/день</div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

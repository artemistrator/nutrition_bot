import './BottomNav.css'

export default function BottomNav({ activePage, onChange }) {
  const tabs = [
    { key: 'diary', icon: '📋', label: 'Дневник' },
    { key: 'stats', icon: '📊', label: 'Статистика' },
    { key: 'profile', icon: '👤', label: 'Профиль' },
  ]

  return (
    <nav className="bottom-nav">
      {tabs.map(tab => (
        <button
          key={tab.key}
          className={`bottom-nav__tab ${activePage === tab.key ? 'bottom-nav__tab--active' : ''}`}
          onClick={() => onChange(tab.key)}
        >
          <span className="bottom-nav__icon">{tab.icon}</span>
          <span className="bottom-nav__label">{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}

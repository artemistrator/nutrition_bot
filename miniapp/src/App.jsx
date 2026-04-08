import { useState, useEffect } from 'react'
import BottomNav from './components/BottomNav'
import DiaryPage from './pages/DiaryPage'
import StatsPage from './pages/StatsPage'
import ProfilePage from './pages/ProfilePage'
import OnboardingPage from './pages/OnboardingPage'
import { api } from './api'
import './App.css'

export default function App() {
  const [activePage, setActivePage] = useState('diary')
  const [appState, setAppState] = useState('loading') // 'loading' | 'onboarding' | 'app'
  const [initialProfile, setInitialProfile] = useState(null)

  useEffect(() => {
    api.getProfile()
      .then(({ data }) => {
        setInitialProfile(data)
        setAppState(data.profile_complete ? 'app' : 'onboarding')
      })
      .catch(err => {
        // 404 — юзер не создан, показываем онбординг
        if (err.response?.status === 404) {
          setAppState('onboarding')
        } else {
          // другая ошибка — всё равно показываем онбординг
          console.error('Profile check failed:', err)
          setAppState('onboarding')
        }
      })
  }, [])

  const handleOnboardingComplete = (profile) => {
    setInitialProfile(profile)
    setActivePage('profile')
    setAppState('app')
  }

  if (appState === 'loading') {
    return <div className="app app--loading">Загрузка...</div>
  }

  if (appState === 'onboarding') {
    return <OnboardingPage profile={initialProfile} onComplete={handleOnboardingComplete} />
  }

  return (
    <div className="app">
      <main className="app__content">
        {activePage === 'diary' && <DiaryPage />}
        {activePage === 'stats' && <StatsPage />}
        {activePage === 'profile' && <ProfilePage />}
      </main>
      <BottomNav activePage={activePage} onChange={setActivePage} />
    </div>
  )
}

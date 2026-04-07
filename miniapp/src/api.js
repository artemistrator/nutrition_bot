import axios from 'axios'

const BASE = 'http://localhost:8001'

function getInitData() {
  if (window.Telegram?.WebApp?.initData) {
    return window.Telegram.WebApp.initData
  }
  // В режиме разработки — вернуть 'dev' для тестирования
  return 'dev'
}

const client = axios.create({ baseURL: BASE })
client.interceptors.request.use(config => {
  config.headers['X-Init-Data'] = getInitData()
  return config
})

export const api = {
  getProfile: () => client.get('/profile'),
  setGoal: (calories) => client.post('/profile/goal', {goal_calories: calories}),
  getTodayMeals: () => client.get('/meals/today'),
  addMeal: (meal) => client.post('/meals', meal),
  getHistory: (days=7) => client.get(`/meals/history?days=${days}`),
  analyzeText: (text) => client.post('/analyze/text', {text}),
  analyzePhoto: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post('/analyze/photo', fd)
  },
  // Activities
  getTodayActivities: () => client.get('/activities/today'),
  addActivity: (activity) => client.post('/activities', activity),
  analyzeActivity: (text) => client.post('/analyze/activity', {text}),
}

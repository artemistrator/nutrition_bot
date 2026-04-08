export const SEX_OPTIONS = [
  { value: 'male', label: 'Мужской', icon: '👨' },
  { value: 'female', label: 'Женский', icon: '👩' },
]

export const ACTIVITY_OPTIONS = [
  { value: 'low', label: 'Низкая', description: 'Мало движения, в основном сидячий режим' },
  { value: 'medium', label: 'Средняя', description: 'Ходьба, тренировки 1-3 раза в неделю' },
  { value: 'high', label: 'Высокая', description: 'Активная работа или регулярные тренировки' },
]

export const GOAL_OPTIONS = [
  { value: 'lose', label: 'Похудеть', icon: '🔥' },
  { value: 'maintain', label: 'Поддержать вес', icon: '⚖️' },
  { value: 'gain', label: 'Набрать массу', icon: '💪' },
]

export function createProfileForm(profile = {}) {
  return {
    sex: profile.sex || '',
    age: profile.age ?? '',
    height_cm: profile.height_cm ?? '',
    weight_kg: profile.weight_kg ?? '',
    activity_level: profile.activity_level || '',
    goal_type: profile.goal_type || '',
  }
}

export function profileGoalLabel(goalType) {
  return GOAL_OPTIONS.find(option => option.value === goalType)?.label || 'Цель не выбрана'
}

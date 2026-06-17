import api from './index'

export function getSettings() {
  return api.get('/settings')
}

export function saveSettings(data) {
  return api.post('/settings', data)
}

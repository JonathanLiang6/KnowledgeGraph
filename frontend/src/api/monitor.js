import api from './index'

export function getTaskStatus(taskId) {
  return api.get(`/monitor/tasks/${taskId}`)
}

export function listTasks() {
  return api.get('/monitor/tasks')
}

export function getSystemStatus() {
  return api.get('/monitor/status')
}

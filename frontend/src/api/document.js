import api from './index'

export function getDocuments(params = {}) {
  return api.get('/documents', { params })
}

export function getDocument(id) {
  return api.get(`/documents/${id}`)
}

export function uploadDocument(formData) {
  // 不手动设置 Content-Type，让 Axios 自动处理 FormData 的 boundary
  return api.post('/documents/upload', formData)
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

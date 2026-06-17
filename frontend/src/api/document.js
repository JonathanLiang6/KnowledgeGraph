import api from './index'

export function getDocuments(params = {}) {
  return api.get('/documents', { params })
}

export function getDocument(id) {
  return api.get(`/documents/${id}`)
}

export function uploadDocument(formData) {
  return api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

export function getDocumentStats() {
  return api.get('/documents/stats/overview')
}

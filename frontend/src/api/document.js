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

export function uploadDocumentsBatch(formData) {
  // 批量上传 (v2.5: 支持多文件批量上传)
  return api.post('/documents/upload/batch', formData)
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

export function getDocumentStats() {
  return api.get('/documents/stats/overview')
}

export function checkDuplicate(fileHash, kbId) {
  return api.get('/documents/check-duplicate', { params: { file_hash: fileHash, kb_id: kbId } })
}

import api from './index'

export function getKnowledgeBases() {
  return api.get('/knowledge-bases')
}

export function getKnowledgeBase(id) {
  return api.get(`/knowledge-bases/${id}`)
}

export function createKnowledgeBase(data) {
  return api.post('/knowledge-bases', data)
}

export function updateKnowledgeBase(id, data) {
  return api.put(`/knowledge-bases/${id}`, data)
}

export function deleteKnowledgeBase(id) {
  // v4.1: 后端删除接口要求 confirm=true 二次确认
  return api.delete(`/knowledge-bases/${id}`, { params: { confirm: true } })
}

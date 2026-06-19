import api from './index'

export function getGraphData(params = {}) {
  return api.get('/graph/data', { params })
}

export function getEntityDetail(id) {
  return api.get(`/graph/entity/${id}`)
}

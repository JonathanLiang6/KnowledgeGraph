/**
 * 拓扑导航 API - v3.2 Q10
 */
import api from './index'

export function getTopology() {
  return api.get('/topology')
}

export function createTopologyNode(data) {
  return api.post('/topology/nodes', data)
}

export function updateTopologyNode(id, data) {
  return api.put(`/topology/nodes/${id}`, data)
}

export function deleteTopologyNode(id) {
  return api.delete(`/topology/nodes/${id}`)
}

export function createTopologyEdge(data) {
  return api.post('/topology/edges', data)
}

export function deleteTopologyEdge(id) {
  return api.delete(`/topology/edges/${id}`)
}

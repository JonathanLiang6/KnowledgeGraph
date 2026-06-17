// ============================================================
// Axios 实例 + API 基础配置
// 所有 API 请求统一由此管理
// ============================================================
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8013/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error(`[API Error] ${message}`)
    return Promise.reject(new Error(message))
  }
)

export default api

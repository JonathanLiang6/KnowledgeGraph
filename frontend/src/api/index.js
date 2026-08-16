// ============================================================
// Axios 实例 + API 基础配置
// 所有 API 请求统一由此管理
// ============================================================
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,  // v4.0: 120s — 适配大文档上传和 Agent 推理等长耗时操作
  headers: { 'Content-Type': 'application/json' },
})

// v4.1: 可选 API Token（后端设置 API_AUTH_TOKEN 后必填，通过 VITE_API_TOKEN 注入）
const apiToken = import.meta.env.VITE_API_TOKEN || ''

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // FormData 自动移除 Content-Type，让浏览器设置 boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    if (apiToken) {
      config.headers['X-API-Token'] = apiToken
    }
    return config
  },
  (error) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error(`[API Error] ${message}`, error.config?.url)
    return Promise.reject(new Error(message))
  }
)

export default api

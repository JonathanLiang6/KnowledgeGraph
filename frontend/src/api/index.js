// ============================================================
// Axios 实例 + API 基础配置
// 所有 API 请求统一由此管理
// v4.1 (#87): 请求生命周期管理 — 路由切换取消未完成请求 + 重复 GET 去次
// ============================================================
import axios from 'axios'
import router from '../router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,  // v4.0: 120s — 适配大文档上传和 Agent 推理等长耗时操作
  headers: { 'Content-Type': 'application/json' },
})

// v4.1: 可选 API Token（后端设置 API_AUTH_TOKEN 后必填，通过 VITE_API_TOKEN 注入）
const apiToken = import.meta.env.VITE_API_TOKEN || ''

// ── 请求生命周期管理 (#87) ─────────────────────────────
const pendingControllers = new Map()   // key -> AbortController

function requestKey(config) {
  const params = config.params ? JSON.stringify(config.params) : ''
  return `${config.method || 'get'}:${config.url}:${params}`
}

// 路由切换时取消全部未完成的幂等请求（GET），避免过期响应覆盖新页面数据
router.afterEach(() => {
  for (const [key, controller] of pendingControllers) {
    if (key.startsWith('get:')) {
      controller.abort()
      pendingControllers.delete(key)
    }
  }
})

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
    // GET 重复请求去次：同 key 未完成时取消上一个，保留最新
    const method = (config.method || 'get').toLowerCase()
    if (method === 'get') {
      const key = requestKey(config)
      const prev = pendingControllers.get(key)
      if (prev) prev.abort()
      const controller = new AbortController()
      config.signal = controller.signal
      pendingControllers.set(key, controller)
      config._requestKey = key
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
  (response) => {
    if (response.config?._requestKey) {
      pendingControllers.delete(response.config._requestKey)
    }
    return response.data
  },
  (error) => {
    if (error.config?._requestKey) {
      pendingControllers.delete(error.config._requestKey)
    }
    // 主动取消（路由切换/去重）静默处理，不作为错误冒泡
    if (axios.isCancel(error)) {
      return new Promise(() => {})  // 永不 resolve：调用方无需处理被取消的过期请求
    }
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error(`[API Error] ${message}`, error.config?.url)
    return Promise.reject(new Error(message))
  }
)

// v4.1 (#87): 防抖工具 — 搜索框/滑块等高频事件节流
export function debounce(fn, delay = 300) {
  let timer = null
  return function debounced(...args) {
    clearTimeout(timer)
    timer = setTimeout(() => fn.apply(this, args), delay)
  }
}

export default api

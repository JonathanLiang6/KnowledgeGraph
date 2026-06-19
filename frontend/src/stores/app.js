// ============================================================
// Pinia 全局状态 — 精简版（KB 上下文由路由参数管理）
// ============================================================
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 主题
  const theme = ref('light')

  function setTheme(val) {
    theme.value = val
  }

  return {
    theme,
    setTheme,
  }
})

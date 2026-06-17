// ============================================================
// Pinia 全局状态 - 知识库选择、主题等
// ============================================================
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 当前选中的知识库
  const currentKB = ref(null)
  const knowledgeBases = ref([])

  // 侧边栏折叠
  const sidebarCollapsed = ref(false)

  // 系统配置
  const systemSettings = ref({
    primary_color: '#4F8CF7',
    font_size: 'medium',
    animations: true,
  })

  // 统计信息
  const stats = ref({
    documents: 0,
    entities: 0,
    relationships: 0,
    knowledge_bases: 0,
    storage_used: '0 B',
  })

  // 计算属性
  const isKBSelected = computed(() => currentKB.value !== null)

  // 方法
  function setCurrentKB(kb) {
    currentKB.value = kb
  }

  function setKnowledgeBases(kbs) {
    knowledgeBases.value = kbs
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function updateSystemSettings(settings) {
    if (settings) {
      systemSettings.value = { ...systemSettings.value, ...settings }
    }
  }

  function updateStats(newStats) {
    if (newStats) {
      stats.value = { ...stats.value, ...newStats }
    }
  }

  return {
    currentKB,
    knowledgeBases,
    sidebarCollapsed,
    systemSettings,
    stats,
    isKBSelected,
    setCurrentKB,
    setKnowledgeBases,
    toggleSidebar,
    updateSystemSettings,
    updateStats,
  }
})

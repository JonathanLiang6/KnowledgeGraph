// ============================================================
// Pinia 聊天状态 - 消息、会话、历史
// ============================================================
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const sessions = ref([])
  const currentSessionId = ref(null)
  const isStreaming = ref(false)

  // 搜索模式
  const searchMode = ref('rag-hybrid')

  const lastMessage = computed(() =>
    messages.value.length > 0 ? messages.value[messages.value.length - 1] : null
  )

  function addMessage(role, content) {
    messages.value.push({
      role,
      content,
      timestamp: new Date().toISOString(),
    })
  }

  function updateLastMessage(chunk) {
    if (messages.value.length > 0) {
      messages.value[messages.value.length - 1].content += chunk
    }
  }

  function clearMessages() {
    messages.value = []
    currentSessionId.value = null
  }

  function setStreaming(val) {
    isStreaming.value = val
  }

  function setSearchMode(mode) {
    searchMode.value = mode
  }

  function addSession(session) {
    sessions.value.unshift(session)
  }

  // 从 localStorage 恢复
  function loadFromStorage() {
    try {
      const saved = localStorage.getItem('chatMessages')
      if (saved) messages.value = JSON.parse(saved)
      const sessionsSaved = localStorage.getItem('chatSessions')
      if (sessionsSaved) sessions.value = JSON.parse(sessionsSaved)
    } catch {}
  }

  // 保存到 localStorage
  function saveToStorage() {
    try {
      localStorage.setItem('chatMessages', JSON.stringify(messages.value.slice(-100)))
      localStorage.setItem('chatSessions', JSON.stringify(sessions.value.slice(-50)))
    } catch {}
  }

  return {
    messages,
    sessions,
    currentSessionId,
    isStreaming,
    searchMode,
    lastMessage,
    addMessage,
    updateLastMessage,
    clearMessages,
    setStreaming,
    setSearchMode,
    addSession,
    loadFromStorage,
    saveToStorage,
  }
})

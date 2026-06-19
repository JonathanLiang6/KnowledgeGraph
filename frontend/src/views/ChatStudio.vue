<template>
  <div class="chat-studio">
    <!-- 侧边栏：对话管理 -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <button class="btn-primary new-chat-btn" @click="clearChat">
          <el-icon :size="16"><Plus /></el-icon>
          <span>新对话</span>
        </button>
      </div>
      <!-- 快捷提示 -->
      <div class="quick-prompts" v-if="messages.length === 0">
        <p class="prompts-title">💡 试试这样问</p>
        <button
          v-for="(q, i) in suggestedQuestions"
          :key="i"
          class="prompt-chip"
          @click="sendPreset(q)"
        >{{ q }}</button>
      </div>
      <!-- 对话历史占位 -->
      <div class="chat-history" v-else>
        <p class="history-hint">对话进行中</p>
        <p class="history-sub">{{ messages.length }} 条消息</p>
      </div>
    </aside>

    <!-- 主聊天区 -->
    <div class="chat-main">
      <div class="chat-messages" ref="messagesContainer">
        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              <line x1="9" y1="10" x2="15" y2="10"/>
              <line x1="12" y1="7" x2="12" y2="13"/>
            </svg>
          </div>
          <h2>智能问答助手</h2>
          <p>基于知识库内容，提供精准的教学问答服务</p>
        </div>

        <!-- 消息列表 -->
        <div
          v-for="(msg, idx) in messages"
          :key="msg.id"
          :class="['message', msg.role]"
        >
          <div class="msg-avatar">
            <el-icon v-if="msg.role === 'assistant'" :size="18"><Cpu /></el-icon>
            <el-icon v-else :size="18"><User /></el-icon>
          </div>
          <div class="msg-body">
            <div class="msg-role-name">
              {{ msg.role === 'assistant' ? 'AI 助手' : '你' }}
            </div>
            <div class="msg-text" v-html="renderMarkdown(msg.content)" />
            <div v-if="msg.error" class="msg-error">
              <el-icon :size="14"><WarningFilled /></el-icon>
              {{ msg.error }}
            </div>
          </div>
        </div>

        <!-- 流式输出 -->
        <div v-if="isStreaming" class="streaming-indicator">
          <span class="streaming-dot" />
          <span class="streaming-text">AI 正在思考...</span>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="chat-footer">
        <div class="mode-bar">
          <el-radio-group v-model="searchMode" size="small">
            <el-radio-button value="rag-hybrid">混合检索</el-radio-button>
            <el-radio-button value="rag-local">向量检索</el-radio-button>
            <el-radio-button value="deepseek-chat">直接问答</el-radio-button>
          </el-radio-group>
        </div>
        <div class="input-row">
          <div class="input-wrapper">
            <textarea
              ref="inputRef"
              v-model="inputText"
              class="chat-input"
              placeholder="输入你的问题，Enter 发送，Shift+Enter 换行..."
              rows="1"
              @keydown="onKeydown"
              @input="autoResize"
              :disabled="isStreaming"
            />
          </div>
          <button
            v-if="!isStreaming"
            class="send-btn"
            :disabled="!inputText.trim()"
            @click="sendMessage"
          >
            <el-icon :size="18"><Promotion /></el-icon>
          </button>
          <button
            v-else
            class="stop-btn"
            @click="stopStreaming"
          >
            <el-icon :size="18"><Close /></el-icon>
          </button>
        </div>
        <p class="input-hint">Enter 发送 · Shift+Enter 换行</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { chatCompletionsStream } from '../api/chat'
import { Cpu, User, Plus, Promotion, Close, WarningFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const inputRef = ref(null)
const messagesContainer = ref(null)

const messages = ref([])
const inputText = ref('')
const isStreaming = ref(false)
const searchMode = ref('rag-hybrid')

let streamController = null
let msgIdCounter = 0

// 建议问题
const suggestedQuestions = [
  '这篇文章主要讲了什么内容？',
  '帮我梳理一下核心知识点',
  '请解释关键概念之间的关系',
  '给我出几道练习题',
]

// ─── 工具函数 ─────────────────────────────────────────
function genId() { return `msg-${Date.now()}-${++msgIdCounter}` }

function scrollToBottom() {
  nextTick(() => {
    const el = messagesContainer.value
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  })
}

function renderMarkdown(text) {
  if (!text) return ''
  const safe = text
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
    .replace(/\son\w+\s*=\s*'[^']*'/gi, '')
  return marked.parse(safe)
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function saveMessages() {
  try {
    localStorage.setItem(
      `chat_${route.params.id}`,
      JSON.stringify(messages.value.slice(-100))
    )
  } catch { /* quota exceeded, ignore */ }
}

function loadMessages() {
  try {
    const raw = localStorage.getItem(`chat_${route.params.id}`)
    if (raw) messages.value = JSON.parse(raw)
    msgIdCounter = messages.value.length
  } catch { messages.value = [] }
}

// ─── 核心操作 ─────────────────────────────────────────

function sendPreset(q) {
  inputText.value = q
  sendMessage()
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return

  // 添加用户消息
  messages.value.push({ id: genId(), role: 'user', content: text })
  inputText.value = ''
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
  scrollToBottom()

  // 创建 assistant 占位
  const assistantId = genId()
  const assistantMsg = { id: assistantId, role: 'assistant', content: '' }
  messages.value.push(assistantMsg)
  isStreaming.value = true

  // 构建请求消息列表
  const chatMessages = []
  for (const m of messages.value) {
    if (m.error) continue
    if (m === assistantMsg) continue
    chatMessages.push({ role: m.role, content: m.content })
  }

  streamController = chatCompletionsStream(
    {
      model: searchMode.value,
      messages: chatMessages,
      kb_id: route.params.id || null,
    },
    // onChunk
    (chunk) => {
      assistantMsg.content += chunk
      scrollToBottom()
    },
    // onDone
    () => {
      isStreaming.value = false
      streamController = null
      if (!assistantMsg.content) {
        assistantMsg.content = '(AI 未返回内容)'
      }
      saveMessages()
      scrollToBottom()
    },
    // onError
    (err) => {
      assistantMsg.error = err.message || '请求失败'
      isStreaming.value = false
      streamController = null
      saveMessages()
      ElMessage.error(`请求失败: ${err.message}`)
    }
  )
}

function stopStreaming() {
  if (streamController) {
    streamController.abort()
    streamController = null
  }
  isStreaming.value = false
  // 给最后一条 assistant 消息收尾
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant' && !last.content) {
    last.content = '(已中断)'
  }
  saveMessages()
  ElMessage.info('已停止生成')
}

async function clearChat() {
  if (messages.value.length > 0) {
    try {
      await ElMessageBox.confirm('确定要清空当前对话吗？', '新对话', {
        confirmButtonText: '清空',
        cancelButtonText: '取消',
        type: 'info',
      })
    } catch {
      return
    }
  }
  if (isStreaming.value) stopStreaming()
  messages.value = []
  try { localStorage.removeItem(`chat_${route.params.id}`) } catch { /* ignore */ }
  inputRef.value?.focus()
}

// ─── 生命周期 ─────────────────────────────────────────

onMounted(() => {
  loadMessages()
  nextTick(scrollToBottom)
})

// 切换知识库时重新加载对话
watch(() => route.params.id, (n, o) => {
  if (n !== o) {
    if (isStreaming.value) stopStreaming()
    messages.value = []
    loadMessages()
  }
})

onBeforeUnmount(() => {
  if (isStreaming.value) stopStreaming()
})
</script>

<style scoped lang="scss">
.chat-studio {
  height: calc(100vh - 56px - 44px - var(--spacing-lg) * 2);
  display: flex;
  gap: 0;
}

// ── 侧边栏 ──────────────────────────────────────────
.chat-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-light);
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  padding: var(--spacing-md);

  .sidebar-header {
    margin-bottom: var(--spacing-md);
  }

  .new-chat-btn {
    width: 100%;
    justify-content: center;
    padding: 10px 16px;
    font-size: 14px;
    border-radius: var(--radius-md);
  }

  .quick-prompts {
    flex: 1;

    .prompts-title {
      font-size: 12px;
      color: var(--text-tertiary);
      margin-bottom: var(--spacing-sm);
    }

    .prompt-chip {
      display: block;
      width: 100%;
      text-align: left;
      padding: 8px 12px;
      margin-bottom: 6px;
      font-size: 13px;
      color: var(--text-secondary);
      background: var(--bg-page);
      border: 1px solid var(--border-light);
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all var(--transition-fast);
      font-family: inherit;

      &:hover {
        color: var(--color-primary);
        border-color: var(--color-primary-light);
        background: var(--bg-hover);
        transform: translateX(3px);
      }
    }
  }

  .chat-history {
    flex: 1;

    .history-hint { font-size: 13px; color: var(--text-secondary); }
    .history-sub { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
  }
}

// ── 主聊天区 ────────────────────────────────────────
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

// 欢迎页
.welcome {
  text-align: center;
  padding: 80px 20px 40px;

  .welcome-icon {
    display: inline-block;
    margin-bottom: var(--spacing-lg);
    color: var(--color-primary);
    animation: float 3.5s ease-in-out infinite;
  }

  h2 {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: var(--spacing-sm);
    color: var(--text-primary);
  }
  p { color: var(--text-secondary); font-size: 14px; }
}

// 消息
.message {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  animation: fadeInUp 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;

  &.assistant {
    .msg-avatar {
      background: var(--color-primary-gradient);
      color: #fff;
      box-shadow: 0 2px 8px rgba(45, 140, 78, 0.25);
    }
  }

  &.user {
    flex-direction: row-reverse;

    .msg-avatar {
      background: var(--bg-active);
      color: var(--color-primary-dark);
    }

    .msg-body {
      align-items: flex-end;

      .msg-role-name { text-align: right; }

      .msg-text {
        background: var(--color-primary-gradient);
        color: #fff;

        :deep(pre) { background: rgba(255,255,255,0.12); }
        :deep(code) { color: rgba(255,255,255,0.9); }
      }
    }
  }
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.msg-body {
  display: flex;
  flex-direction: column;
  max-width: 72%;
}

.msg-role-name {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
  padding: 0 4px;
}

.msg-text {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: 14px;
  line-height: 1.75;
  box-shadow: var(--shadow-xs);
  border: 1px solid var(--border-light);

  :deep(p) { margin-bottom: 8px; &:last-child { margin-bottom: 0; } }
  :deep(pre) {
    background: #f5f7f5;
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    overflow-x: auto;
    margin: 8px 0;
  }
  :deep(code) {
    font-family: 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
  }
  :deep(ul), :deep(ol) { padding-left: 20px; margin: 4px 0; }
  :deep(blockquote) {
    border-left: 3px solid var(--color-primary-light);
    padding-left: 12px;
    color: var(--text-secondary);
    margin: 8px 0;
  }
  :deep(table) {
    border-collapse: collapse;
    margin: 8px 0;
    th, td { border: 1px solid var(--border-light); padding: 6px 12px; font-size: 13px; }
    th { background: var(--bg-page); font-weight: 600; }
  }
}

.msg-error {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-danger);
  display: flex;
  align-items: center;
  gap: 5px;
}

// 流式指示器
.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  animation: fadeInUp 0.3s ease both;

  .streaming-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-primary);
    animation: dot-pulse 1.2s ease-in-out infinite;
  }

  .streaming-text {
    font-size: 13px;
    color: var(--text-tertiary);
  }
}

// ── 底部 ────────────────────────────────────────────
.chat-footer {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-top: 1px solid var(--border-light);
}

.mode-bar {
  text-align: center;
  margin-bottom: var(--spacing-sm);
}

.input-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-end;
}

.input-wrapper {
  flex: 1;
}

.chat-input {
  width: 100%;
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.5;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  resize: none;
  outline: none;
  background: var(--bg-card);
  color: var(--text-primary);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);

  &::placeholder { color: var(--text-tertiary); }
  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(45, 140, 78, 0.1);
  }
  &:disabled {
    background: var(--bg-page);
    cursor: not-allowed;
  }
}

.send-btn {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--color-primary-gradient);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-normal);
  box-shadow: 0 2px 8px rgba(45, 140, 78, 0.3);

  &:hover:not(:disabled) {
    transform: scale(1.06);
    box-shadow: 0 4px 16px rgba(45, 140, 78, 0.45);
    .el-icon { transform: rotate(-45deg); }
  }
  &:active:not(:disabled) { transform: scale(0.94) !important; }
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .el-icon { transition: transform var(--transition-normal); }
}

.stop-btn {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--color-danger);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-fast);
  animation: glow-pulse 1.5s ease-in-out infinite;

  &:hover {
    background: #d43d3d;
    transform: scale(1.06);
  }
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 6px;
}

// ── 响应式 ──────────────────────────────────────────
@media (max-width: 768px) {
  .chat-sidebar { display: none; }
  .msg-body { max-width: 85%; }
}
</style>

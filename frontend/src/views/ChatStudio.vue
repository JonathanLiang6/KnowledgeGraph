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
      <!-- 顶部模式切换栏 -->
      <div class="chat-header">
        <div class="mode-switcher">
          <button
            class="mode-tab"
            :class="{ active: !useAgent }"
            @click="useAgent = false"
          >
            <el-icon :size="14"><ChatDotRound /></el-icon>
            知识库问答
          </button>
          <button
            class="mode-tab"
            :class="{ active: useAgent }"
            @click="useAgent = true"
          >
            <el-icon :size="14"><Cpu /></el-icon>
            Agent 推理
          </button>
          <el-tooltip v-if="useAgent" content="启用后，Agent 在本地知识库信息不足时可联网搜索" placement="bottom">
            <button
              class="web-toggle"
              :class="{ active: enableWeb }"
              @click="enableWeb = !enableWeb"
            >
              {{ enableWeb ? '联网' : '仅本地' }}
            </button>
          </el-tooltip>
        </div>
      </div>

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

        <!-- v4.1 (#87): 长会话分页渲染 — 先渲最近 50 条，更早的按需展开，降低长会话 DOM 压力 -->
        <button
          v-if="visibleCount < messages.length"
          class="load-earlier-btn"
          @click="visibleCount += VISIBLE_PAGE_SIZE"
        >
          加载更早的 {{ Math.min(VISIBLE_PAGE_SIZE, messages.length - visibleCount) }} 条消息（共 {{ messages.length }} 条）
        </button>

        <!-- 消息列表 -->
        <div
          v-for="(msg, idx) in visibleMessages"
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
            <!-- v4.0: Agent 推理步骤展示 -->
            <div v-if="msg.reasoningSteps && msg.reasoningSteps.length > 0" class="msg-reasoning">
              <details v-for="(step, si) in msg.reasoningSteps" :key="si" :open="si === msg.reasoningSteps.length - 1">
                <summary class="reasoning-summary">
                  <span class="reasoning-badge">{{ step.type === 'agent/thought' ? '💭 思考' : step.type === 'agent/action' ? '🔧 行动' : step.type === 'agent/observation' ? '👁 观察' : step.type }}</span>
                </summary>
                <div class="reasoning-content">
                  <template v-if="step.type === 'agent/action'">
                    <span class="reasoning-label">工具:</span> {{ step.tool }}<br>
                    <span class="reasoning-label">参数:</span> {{ step.input }}
                  </template>
                  <template v-else>
                    {{ step.content }}
                  </template>
                </div>
              </details>
            </div>
            <div
              class="msg-text"
              v-html="renderMessageContent(msg, idx)"
            />
            <div v-if="msg.error" class="msg-error">
              <el-icon :size="14"><WarningFilled /></el-icon>
              {{ msg.error }}
            </div>
          </div>
        </div>

        <!-- 流式等待指示（收到首字节前显示，之后由打字机光标接管） -->
        <div
          v-if="isStreaming && visibleMessages.length > 0 && !visibleMessages[visibleMessages.length - 1].content"
          class="streaming-indicator"
        >
          <div class="streaming-dots">
            <span class="streaming-dot" />
            <span class="streaming-dot" />
            <span class="streaming-dot" />
          </div>
          <span class="streaming-text">AI 正在思考...</span>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="chat-footer">
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
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { chatCompletionsStream } from '../api/chat'
import { Cpu, User, Plus, Promotion, Close, WarningFilled, ChatDotRound } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const inputRef = ref(null)
const messagesContainer = ref(null)

const messages = ref([])
const VISIBLE_PAGE_SIZE = 50
const visibleCount = ref(VISIBLE_PAGE_SIZE)
// 分页视图：始终包含最新的消息；渲染函数中 idx 相对可见列表计算
const visibleMessages = computed(() => messages.value.slice(-visibleCount.value))
const inputText = ref('')
const isStreaming = ref(false)
const useAgent = ref(false)       // v3.2: Agent vs 知识库问答 切换
const enableWeb = ref(false)      // v4.0: 联网搜索默认关闭，避免后端不支持时造成困惑

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

// v4.1 (#69): rAF 合并滚动调用；打字机高频场景用 instant 避免多次 smooth 相互打架；
// 仅当用户接近底部时自动跟随，向上翻阅历史不被打断
let scrollPending = false
function scrollToBottom(smooth = true) {
  if (scrollPending) return
  scrollPending = true
  requestAnimationFrame(() => {
    scrollPending = false
    const el = messagesContainer.value
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
    if (!nearBottom) return
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  })
}

function renderMarkdown(text) {
  if (!text) return ''
  const raw = marked.parse(text)
  if (typeof DOMPurify !== 'undefined') {
    return DOMPurify.sanitize(raw, {
      ALLOWED_TAGS: ['a', 'code', 'pre', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'ul', 'ol', 'li', 'strong', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'p', 'br', 'hr', 'img', 'del', 'sup', 'sub', 'span', 'div'],
      ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'target', 'rel'],
    })
  }
  return raw
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
    .replace(/\son\w+\s*=\s*'[^']*'/gi, '')
}

// v3.2: 流式 Markdown 渲染节流 — 避免逐字符调用 marked.parse()
let streamingMdCache = ''
const streamingMdRendered = ref('')       // v4.0: 使用 ref 让 Vue 自动追踪变化
let mdRenderPending = false

// v4.1 (#68): 历史消息渲染缓存 — 打字机逐字符重渲染期间，历史消息若 content
// 未变则直接复用渲染结果，避免对全部消息做 marked.parse + DOMPurify 全量重算
const historyMdCache = new Map()          // msgId -> { content, html }
const HISTORY_MD_CACHE_MAX = 200

function renderHistoryMarkdown(msg) {
  const cached = historyMdCache.get(msg.id)
  if (cached && cached.content === msg.content) return cached.html
  const html = renderMarkdown(msg.content)
  historyMdCache.set(msg.id, { content: msg.content, html })
  if (historyMdCache.size > HISTORY_MD_CACHE_MAX) {
    historyMdCache.delete(historyMdCache.keys().next().value)
  }
  return html
}

function renderMessageContent(msg, idx) {
  // 流式输出中或打字机队列仍在消耗 → 实时 Markdown 渲染 + 闪烁光标
  if (
    (isStreaming.value || typewriterRunning.value) &&
    idx === messages.value.length - 1 &&
    msg.role === 'assistant'
  ) {
    const display = msg.content || ''
    // 节流：内容未变则复用缓存
    if (display === streamingMdCache) {
      // v4.0: 读取 ref 让 Vue 自动追踪依赖，无需手动 messages hack
      return streamingMdRendered.value + '<span class="typewriter-cursor">|</span>'
    }
    streamingMdCache = display
    // 用 requestAnimationFrame 节流，避免高频 DOM 更新卡顿
    if (!mdRenderPending) {
      mdRenderPending = true
      requestAnimationFrame(() => {
        mdRenderPending = false
        // v4.0: 直接赋值 ref，Vue 响应式系统自动触发重新渲染
        streamingMdRendered.value = renderMarkdown(streamingMdCache)
      })
    }
    return streamingMdRendered.value + '<span class="typewriter-cursor">|</span>'
  }
  return renderHistoryMarkdown(msg)
}

// ─── 打字机队列系统 ────────────────────────────────────
const typewriterQueue = []        // {char, type} — 非响应式数组（性能优化）
const typewriterRunning = ref(false)
let typewriterTimeoutId = null
let lastAutoSave = 0
const MAX_QUEUE_SIZE = 2000       // v4.0: 队列长度上限，防止内存无限增长

// 速度映射表
const TYPE_SPEEDS = {
  chinese:     { baseMin: 5.6, baseMax: 8.3 },                // 12-18 chars/sec
  code:        { baseMin: 11.1, baseMax: 22.2 },              // 4.5-9 chars/sec
  normal:      { baseMin: 5.6, baseMax: 8.3 },                // similar to Chinese
  punctuation: { baseMin: 6.7, baseMax: 8.3, pauseMin: 6.7, pauseMax: 13.3 },
  newline:     { baseMin: 6.7, baseMax: 8.3, pauseMin: 10.0, pauseMax: 20.0 },
}

function getDelayForType(type) {
  const cfg = TYPE_SPEEDS[type] || TYPE_SPEEDS.normal
  const base = cfg.baseMin + Math.random() * (cfg.baseMax - cfg.baseMin)
  let pause = 0
  if (cfg.pauseMin !== undefined) {
    pause = cfg.pauseMin + Math.random() * (cfg.pauseMax - cfg.pauseMin)
  }
  return { base, pause }
}

function enqueueChar(char, charType) {
  // v4.0: 队列超限时合并相邻字符加速消费，防止内存无限增长
  if (typewriterQueue.length >= MAX_QUEUE_SIZE) {
    // 跳过排队，直接合并到最后一个字符
    const last = typewriterQueue[typewriterQueue.length - 1]
    if (last) {
      last.char += char
      return
    }
  }
  typewriterQueue.push({ char, type: charType || 'normal' })
  if (!typewriterRunning.value) {
    typewriterRunning.value = true
    const assistantMsg = messages.value[messages.value.length - 1]
    if (assistantMsg && assistantMsg.role === 'assistant') {
      processTypewriterQueue(assistantMsg)
    }
  }
}

function processTypewriterQueue(msg) {
  if (!typewriterRunning.value) return

  // 队列空 + 流已结束 → 最终化
  if (typewriterQueue.length === 0) {
    if (!isStreaming.value) {
      typewriterRunning.value = false
      if (msg && !msg.content) {
        msg.content = '(AI 未返回内容)'
      }
      saveMessages()
      scrollToBottom()
      return
    }
    // 流还在进行中，轮询等待新字符
    typewriterTimeoutId = setTimeout(() => processTypewriterQueue(msg), 25)
    return
  }

  // 正常出队一个字符
  const item = typewriterQueue.shift()
  msg.content += item.char

  const { base, pause } = getDelayForType(item.type)
  const totalDelay = pause > 0 ? base + pause : base

  // 每 5 秒自动保存（断网保护）
  const now = Date.now()
  if (now - lastAutoSave > 5000) {
    saveMessages()
    lastAutoSave = now
  }

  scrollToBottom(false)  // v4.1 (#69): 高频出队用 instant 滚动，避免 smooth 互相打架
  typewriterTimeoutId = setTimeout(() => processTypewriterQueue(msg), totalDelay)
}

function cleanupTypewriter() {
  typewriterQueue.length = 0
  typewriterRunning.value = false
  streamingMdCache = ''
  streamingMdRendered.value = ''
  if (typewriterTimeoutId !== null) {
    clearTimeout(typewriterTimeoutId)
    typewriterTimeoutId = null
  }
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
  visibleCount.value = VISIBLE_PAGE_SIZE  // v4.1 (#87): 会话切换重置分页
  historyMdCache.clear()  // v4.1 (#68): 历史消息缓存随会话切换失效
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

  // v4.1 (#87): 新消息发送时收起历史分页，聚焦当前对话
  if (visibleCount.value < VISIBLE_PAGE_SIZE) visibleCount.value = VISIBLE_PAGE_SIZE

  // 创建 assistant 占位
  const assistantId = genId()
  const assistantMsg = { id: assistantId, role: 'assistant', content: '' }
  messages.value.push(assistantMsg)
  // v4.1 (#67): 从 ref 取出响应式代理再交给闭包 — 直接持有原始对象时
  // onAgentEvent/onError 对 reasoningSteps/error 的修改 Vue 感知不到
  const liveMsg = messages.value[messages.value.length - 1]
  isStreaming.value = true

  // 构建请求消息列表
  const chatMessages = []
  for (const m of messages.value) {
    if (m.error) continue
    if (m === liveMsg) continue  // v4.1: 代理比较恒成立，正确排除占位消息
    chatMessages.push({ role: m.role, content: m.content })
  }
  // v4.1 (#83): 后端限制单次请求最多 50 条消息，超出时保留最近的上下文
  if (chatMessages.length > 50) chatMessages.splice(0, chatMessages.length - 50)

  streamController = chatCompletionsStream(
    {
      model: useAgent.value ? 'rag-agent' : 'rag-hybrid',
      messages: chatMessages,
      kb_id: route.params.id || null,
      enable_web: enableWeb.value,
    },
    // onChunk — 逐字符入队，打字机队列自动驱动显示
    (char, charType) => {
      enqueueChar(char, charType)
    },
    // onDone — 流结束，队列处理器自动在耗尽后最终化
    () => {
      isStreaming.value = false
      streamController = null
      streamingMdCache = ''
      streamingMdRendered.value = ''
      // 如果队列已空且打字机未运行，手动最终化
      if (typewriterQueue.length === 0 && !typewriterRunning.value) {
        if (!liveMsg.content) {
          liveMsg.content = '(AI 未返回内容)'
        }
        saveMessages()
        scrollToBottom()
      }
    },
    // onError — 清空队列，保留已显示内容
    (err) => {
      cleanupTypewriter()
      liveMsg.error = err.message || '请求失败'
      isStreaming.value = false
      streamController = null
      saveMessages()
      ElMessage.error(`请求失败: ${err.message}`)
    },
    // v4.0: onAgentEvent — 处理 Agent 推理事件
    (event) => {
      // 将推理事件插入消息列表中（作为特殊卡片显示）
      const type = event.type || ''
      if (type === 'agent/thought' || type === 'agent/action' || type === 'agent/observation') {
        // v4.1 (#67): 经响应式代理写入，推理卡片即时渲染（首字符前到达的事件同样生效）
        if (!liveMsg.reasoningSteps) liveMsg.reasoningSteps = []
        liveMsg.reasoningSteps.push(event)
      }
      if (type === 'agent/error') {
        liveMsg.error = event.content || '推理过程出错'
      }
    }
  )
}

function stopStreaming() {
  if (streamController) {
    streamController.abort()
    streamController = null
  }
  isStreaming.value = false

  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    // 立即 flush 队列中剩余字符
    if (typewriterQueue.length > 0) {
      while (typewriterQueue.length > 0) {
        last.content += typewriterQueue.shift().char
      }
    }
    if (!last.content && typewriterQueue.length === 0 && !typewriterRunning.value) {
      last.content = '(已中断)'
    }
  }
  typewriterRunning.value = false
  if (typewriterTimeoutId !== null) {
    clearTimeout(typewriterTimeoutId)
    typewriterTimeoutId = null
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
  cleanupTypewriter()
  messages.value = []
  historyMdCache.clear()  // v4.1 (#68): 清空对话同步清理渲染缓存
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
    cleanupTypewriter()
    messages.value = []
    loadMessages()
  }
})

onBeforeUnmount(() => {
  if (isStreaming.value) stopStreaming()
  cleanupTypewriter()
})
</script>

<style scoped lang="scss">
.chat-studio {
  height: 100vh;
  display: flex;
  gap: 0;
  overflow: hidden;
  background: var(--bg-page);
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
  animation: fadeIn 0.5s ease;

  .welcome-icon {
    display: inline-block;
    margin-bottom: var(--spacing-lg);
    color: var(--color-primary);
    animation: float 3.5s ease-in-out infinite;
  }

  h2 {
    font-size: 24px;
    font-weight: 600;
    margin-bottom: var(--spacing-sm);
    color: var(--text-primary);
    letter-spacing: var(--tracking-tight);
  }
  p {
    color: var(--text-secondary);
    font-size: 14px;
    letter-spacing: 0.02em;
  }
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
  transition: box-shadow var(--transition-fast);

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

// v4.0: Agent 推理步骤
.msg-reasoning {
  margin-bottom: 8px;

  details {
    background: var(--bg-page);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-sm);
    padding: 6px 10px;
    margin-bottom: 4px;

    &[open] {
      border-color: var(--color-primary-light);
    }
  }

  .reasoning-summary {
    font-size: 12px;
    cursor: pointer;
    color: var(--text-secondary);
    user-select: none;

    .reasoning-badge {
      font-weight: 500;
    }
  }

  .reasoning-content {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
    padding: 4px 8px;
    background: var(--bg-card);
    border-radius: 4px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 120px;
    overflow-y: auto;

    .reasoning-label {
      font-weight: 600;
      color: var(--text-primary);
    }
  }
}

// 打字机光标闪烁
:deep(.typewriter-cursor) {
  display: inline-block;
  vertical-align: text-bottom;
  font-weight: 300;
  color: var(--color-primary);
  animation: cursor-blink 0.8s step-end infinite;
  margin-left: 1px;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

// 流式指示器
.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  animation: fadeInUp 0.3s ease both;

  .streaming-dots {
    display: inline-flex;
    gap: 4px;
  }

  .streaming-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--color-primary);
    animation: dotBounce 1.2s ease-in-out infinite;

    &:nth-child(2) { animation-delay: 0.15s; }
    &:nth-child(3) { animation-delay: 0.3s; }
  }

  .streaming-text {
    font-size: 13px;
    color: var(--text-tertiary);
    letter-spacing: 0.02em;
  }
}

@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-6px); opacity: 1; }
}

// ── 底部 ────────────────────────────────────────────
// ── 顶部模式切换栏 ────────────────────────────────────
.chat-header {
  padding: 10px var(--spacing-lg);
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.mode-switcher {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-page);
  padding: 3px;
  border-radius: var(--radius-md);
  width: fit-content;
}

.mode-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-tertiary);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--text-primary);
  }

  &.active {
    background: var(--bg-card);
    color: var(--color-primary);
    box-shadow: var(--shadow-xs);
  }
}

.web-toggle {
  margin-left: 8px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-tertiary);
  background: var(--bg-page);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);

  &.active {
    color: var(--color-primary);
    background: rgba(58, 157, 91, 0.1);
    border-color: rgba(58, 157, 91, 0.3);
  }

  &:hover {
    color: var(--text-primary);
  }
}

.chat-footer {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-top: 1px solid var(--border-light);
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
    box-shadow: 0 0 0 4px rgba(45, 140, 78, 0.12), 0 2px 8px rgba(45, 140, 78, 0.08);
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

/* v4.1 (#87): 加载更早消息 — 低调胶囊按钮 */
.load-earlier-btn {
  grid-column: 1 / -1;
  justify-self: center;
  margin: 4px auto 12px;
  padding: 6px 16px;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  background: rgba(46, 125, 80, 0.08);
  border: 1px solid rgba(46, 125, 80, 0.25);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.load-earlier-btn:hover {
  color: #2e7d50;
  background: rgba(46, 125, 80, 0.15);
  border-color: rgba(46, 125, 80, 0.45);
}

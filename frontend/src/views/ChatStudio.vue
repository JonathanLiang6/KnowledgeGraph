<template>
  <div class="chat-studio">
    <!-- 聊天区域 -->
    <div class="chat-container">
      <div class="chat-messages" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">
            <el-icon :size="48" color="var(--color-primary)"><ChatDotRound /></el-icon>
          </div>
          <h2>智能问答</h2>
          <p>选择搜索模式，基于知识库内容进行智能问答</p>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'assistant'" :size="18"><Cpu /></el-icon>
            <el-icon v-else :size="18"><User /></el-icon>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(msg.content)" />
            <div v-if="msg.error" class="message-error">{{ msg.error }}</div>
            <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>

        <!-- 流式输出光标 -->
        <span v-if="isStreaming" class="cursor-blink" />
      </div>

      <!-- 输入区域 -->
      <div class="chat-input-area">
        <div class="mode-selector">
          <el-radio-group v-model="searchMode" size="small">
            <el-radio-button value="rag-hybrid">混合检索</el-radio-button>
            <el-radio-button value="rag-local">向量检索</el-radio-button>
            <el-radio-button value="deepseek-chat">直接问答</el-radio-button>
          </el-radio-group>
        </div>
        <div class="input-row">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            placeholder="输入你的问题，按 Enter 发送..."
            @keydown.enter.exact.prevent="sendMessage"
            :disabled="isStreaming"
          />
          <button class="btn-primary send-btn" @click="sendMessage" :disabled="isStreaming || !inputText.trim()">
            <el-icon :size="16"><Promotion /></el-icon>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { chatCompletionsStream } from '../api/chat'
import { ChatDotRound, Cpu, User, Promotion } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'

const route = useRoute()
const messages = ref([])
const inputText = ref('')
const isStreaming = ref(false)
const searchMode = ref('rag-hybrid')
const messagesContainer = ref(null)

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return

  messages.value.push({ role: 'user', content: text, timestamp: new Date().toISOString() })
  inputText.value = ''
  scrollToBottom()

  const assistantMsg = { role: 'assistant', content: '', timestamp: new Date().toISOString() }
  messages.value.push(assistantMsg)
  isStreaming.value = true

  // 只发送已完成的消息（排除当前空的 assistant 占位）
  const chatMessages = messages.value
    .filter(m => m.role !== 'system' && m !== assistantMsg)
    .map(m => ({ role: m.role, content: m.content }))

  chatCompletionsStream(
    {
      model: searchMode.value,
      messages: chatMessages,
      kb_id: route.params.id || null,
    },
    (chunk) => {
      assistantMsg.content += chunk
      scrollToBottom()
    },
    () => {
      isStreaming.value = false
      assistantMsg.timestamp = new Date().toISOString()
      scrollToBottom()
    },
    (err) => {
      assistantMsg.error = `请求失败: ${err.message}`
      isStreaming.value = false
      ElMessage.error(`问答请求失败: ${err.message}`)
    }
  )
}

onMounted(() => {
  try {
    const saved = localStorage.getItem('chatMessages_v2')
    if (saved) messages.value = JSON.parse(saved)
  } catch (e) {
    console.warn('无法恢复聊天记录:', e)
  }
})
</script>

<style scoped lang="scss">
.chat-studio {
  height: calc(100vh - 56px - 44px - var(--spacing-lg) * 2);
  display: flex;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
}

.welcome {
  text-align: center;
  padding: 60px 20px;

  .welcome-icon { margin-bottom: var(--spacing-md); }
  h2 { font-size: 24px; margin-bottom: var(--spacing-sm); }
  p { color: var(--text-secondary); }
}

.message {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);

  &.assistant .message-avatar {
    background: var(--color-primary-gradient);
    color: #fff;
  }

  &.user {
    flex-direction: row-reverse;

    .message-avatar {
      background: var(--bg-page);
      color: var(--color-primary);
    }

    .message-content {
      background: var(--color-primary-gradient);
      color: #fff;
    }
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-content {
  max-width: 75%;
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);

  .message-text {
    font-size: 14px;
    line-height: 1.7;

    :deep(p) { margin-bottom: 8px; }
    :deep(pre) {
      background: #f8f9fc;
      padding: 12px;
      border-radius: var(--radius-sm);
      overflow-x: auto;
    }
    :deep(code) {
      font-family: 'Fira Code', monospace;
      font-size: 13px;
    }
  }

  .message-error {
    color: var(--color-danger);
    font-size: 12px;
    margin-top: 4px;
  }

  .message-time {
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: var(--spacing-xs);
    text-align: right;
  }
}

.chat-input-area {
  padding: var(--spacing-md);
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  border-top: 1px solid var(--border-light);

  .mode-selector {
    margin-bottom: var(--spacing-sm);
    text-align: center;
  }

  .input-row {
    display: flex;
    gap: var(--spacing-sm);

    :deep(.el-textarea__inner) {
      border-radius: var(--radius-md);
      resize: none;
    }

    .send-btn {
      width: 44px;
      height: 44px;
      border-radius: var(--radius-md);
      flex-shrink: 0;
    }
  }
}
</style>

<template>
  <div class="chat">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        智能问答
      </h1>
      <div class="chat-actions">
        <button class="btn-secondary" @click="exportChat">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          导出对话
        </button>
      </div>
    </div>

    <div class="chat-container">
      <!-- 聊天界面 -->
      <div class="chat-main">
        <!-- 聊天记录 -->
        <div class="chat-messages" ref="chatMessages">
          <div v-for="message in messages" :key="message.id" class="message" :class="message.role">
            <div class="message-avatar">
              <div v-if="message.role === 'user'" class="avatar user-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </div>
              <div v-else class="avatar assistant-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-author">{{ message.role === 'user' ? '我' : '知识图谱助手' }}</span>
                <span class="message-time">{{ message.time }}</span>
              </div>
              <div class="message-body" v-html="message.content"></div>
              <div class="message-actions" v-if="message.role === 'assistant'">
                <button class="action-btn" @click="copyMessage(message.content)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  复制
                </button>
                <button class="action-btn" @click="feedback(message.id, 'positive')">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                  有用
                </button>
                <button class="action-btn" @click="feedback(message.id, 'negative')">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 19 12 9.01 9 12.01"></polyline>
                  </svg>
                  无用
                </button>
              </div>
            </div>
          </div>
          <div v-if="loading" class="message assistant loading">
            <div class="message-avatar">
              <div class="avatar assistant-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
            </div>
            <div class="message-content">
              <div class="loading-spinner"></div>
              <div class="loading-text">正在思考...</div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="chat-input-area">
          <div class="input-wrapper">
            <textarea 
              v-model="inputMessage" 
              class="input" 
              placeholder="请输入您的问题..."
              rows="1"
              @keydown.enter.exact="sendMessage"
              @keydown.enter.shift="$event.target.value += '\n'"
              @input="autoResize"
              ref="textarea"
            ></textarea>
            <div class="input-actions">
              <button class="btn-secondary" @click="clearChat">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="10" y2="17"></line>
                  <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
                清空
              </button>
              <button class="btn-primary" @click="sendMessage" :disabled="!inputMessage.trim() || loading">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
                发送
              </button>
            </div>
          </div>
          <div class="chat-tips">
            <span class="tip">💡 提示：</span>
            <span class="tip-text">按 Enter 发送消息，Shift+Enter 换行</span>
          </div>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="chat-sidebar">
        <!-- 搜索模式 -->
        <div class="card">
          <h3>搜索模式</h3>
          <div class="mode-selector">
            <el-radio-group v-model="searchMode">
              <el-radio-button label="local">本地搜索</el-radio-button>
              <el-radio-button label="global">全局搜索</el-radio-button>
              <el-radio-button label="full">综合搜索</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <!-- 历史记录 -->
        <div class="card">
          <div class="card-header">
            <h3>历史记录</h3>
            <button class="btn-sm" @click="clearHistory">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <line x1="10" y1="11" x2="10" y2="17"></line>
                <line x1="14" y1="11" x2="14" y2="17"></line>
              </svg>
            </button>
          </div>
          <div class="history-list">
            <div 
              v-for="(history, index) in historyList" 
              :key="index" 
              class="history-item"
              @click="loadHistory(history)"
            >
              <div class="history-question">{{ history.question }}</div>
              <div class="history-time">{{ history.time }}</div>
            </div>
            <div v-if="historyList.length === 0" class="empty-history">
              暂无历史记录
            </div>
          </div>
        </div>

        <!-- 推荐问题 -->
        <div class="card">
          <h3>推荐问题</h3>
          <div class="recommended-questions">
            <div 
              v-for="(question, index) in recommendedQuestions" 
              :key="index" 
              class="recommended-question"
              @click="selectRecommendedQuestion(question)"
            >
              {{ question }}
            </div>
          </div>
        </div>

        <!-- 对话统计 -->
        <div class="card">
          <h3>对话统计</h3>
          <div class="chat-stats">
            <div class="stat-item">
              <div class="stat-value">{{ messages.length }}</div>
              <div class="stat-label">消息数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ historyList.length }}</div>
              <div class="stat-label">历史对话</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ getTodayMessages() }}</div>
              <div class="stat-label">今日消息</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 聊天消息
const messages = ref([
  {
    id: 1,
    role: 'assistant',
    content: '<p>你好！我是知识图谱助手，有什么我可以帮助你的吗？</p>',
    time: '2026-03-30 10:00'
  }
])

// 输入消息
const inputMessage = ref('')

// 加载状态
const loading = ref(false)

// 搜索模式
const searchMode = ref('local')

// 历史记录
const historyList = ref([
  {
    question: '什么是知识图谱？',
    time: '2026-03-29 14:20'
  },
  {
    question: '知识图谱有哪些应用？',
    time: '2026-03-29 10:15'
  }
])

// 推荐问题
const recommendedQuestions = ref([
  '知识图谱的基本概念',
  '知识图谱的构建方法',
  '知识图谱在教育中的应用',
  '如何优化知识图谱',
  '知识图谱与人工智能的关系'
])

// 引用
const chatMessages = ref(null)
const textarea = ref(null)

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const question = inputMessage.value.trim()
  
  // 添加用户消息
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: `<p>${question}</p>`,
    time: new Date().toLocaleString('zh-CN')
  })
  
  inputMessage.value = ''
  loading.value = true

  // 滚动到底部
  await nextTick()
  scrollToBottom()

  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 生成回答
    const answer = getMockAnswer(question)
    
    // 添加助手消息
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: marked(answer),
      time: new Date().toLocaleString('zh-CN')
    })
    
    // 更新历史记录
    historyList.value.unshift({
      question: question,
      time: new Date().toLocaleString('zh-CN')
    })
    
    if (historyList.value.length > 10) {
      historyList.value = historyList.value.slice(0, 10)
    }
    
  } catch (error) {
    console.error('发送消息失败:', error)
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: '<p>抱歉，我暂时无法回答这个问题，请稍后再试。</p>',
      time: new Date().toLocaleString('zh-CN')
    })
  } finally {
    loading.value = false
    // 滚动到底部
    await nextTick()
    scrollToBottom()
  }
}

// 清空聊天
const clearChat = () => {
  messages.value = [
    {
      id: 1,
      role: 'assistant',
      content: '<p>你好！我是知识图谱助手，有什么我可以帮助你的吗？</p>',
      time: '2026-03-30 10:00'
    }
  ]
}

// 加载历史记录
const loadHistory = (history) => {
  inputMessage.value = history.question
}

// 选择推荐问题
const selectRecommendedQuestion = (question) => {
  inputMessage.value = question
  sendMessage()
}

// 模拟回答
const getMockAnswer = (question) => {
  const answers = {
    '什么是知识图谱？': `
# 知识图谱的概念

知识图谱是一种结构化的知识表示方法，通过图结构来表示实体之间的关系。它由节点（实体）和边（关系）组成，能够有效地组织和管理复杂的知识网络。

## 核心特点

- **结构化**：使用图结构存储知识
- **语义丰富**：包含实体之间的语义关系
- **可扩展**：易于添加新的实体和关系
- **多源融合**：整合来自不同来源的知识

## 应用场景

- 智能问答系统
- 推荐系统
- 数据分析和可视化
- 知识管理
    `,
    '知识图谱有哪些应用？': `
# 知识图谱的应用

知识图谱在各个领域都有广泛的应用，以下是一些主要应用场景：

## 智能问答
- 基于知识图谱的问答系统能够提供准确、结构化的回答
- 支持复杂的多跳推理
- 适用于客服、教育等场景

## 推荐系统
- 利用知识图谱的语义关系提升推荐质量
- 实现基于知识的个性化推荐
- 提高推荐的可解释性

## 金融领域
- 风险评估和欺诈检测
- 反洗钱分析
- 智能投顾

## 医疗健康
- 医学知识管理
- 辅助诊断
- 药物研发

## 教育领域
- 智能教学系统
- 知识结构可视化
- 个性化学习路径
    `
  }
  
  return answers[question] || `
# 关于"${question}"的回答

这是一个基于知识图谱的回答。知识图谱系统正在分析您的问题，并从结构化的知识库中检索相关信息。

## 核心信息

- 问题类型：${question.includes('什么是') ? '定义类问题' : question.includes('如何') ? '方法类问题' : '其他类型问题'}
- 相关实体：根据知识图谱分析
- 相关关系：基于知识图谱的语义分析

## 建议

如果您需要更详细的信息，可以尝试以下方式：

- 提供更具体的问题描述
- 指明您感兴趣的具体方面
- 参考推荐的相关问题
    `
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }
}

// 自动调整文本框高度
const autoResize = () => {
  if (textarea.value) {
    textarea.value.style.height = 'auto'
    textarea.value.style.height = Math.min(textarea.value.scrollHeight, 200) + 'px'
  }
}

// 复制消息
const copyMessage = (content) => {
  // 移除HTML标签，只复制纯文本
  const plainText = content.replace(/<[^>]*>/g, '')
  navigator.clipboard.writeText(plainText).then(() => {
    // 可以添加复制成功的提示
    console.log('复制成功')
  }).catch(err => {
    console.error('复制失败:', err)
  })
}

// 反馈功能
const feedback = (messageId, type) => {
  console.log('反馈:', messageId, type)
  // 这里可以添加反馈处理逻辑
}

// 导出对话
const exportChat = () => {
  const chatContent = messages.value.map(msg => {
    return `${msg.role === 'user' ? '我' : '知识图谱助手'} (${msg.time}):\n${msg.content.replace(/<[^>]*>/g, '')}\n\n`
  }).join('')
  
  const blob = new Blob([chatContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `知识图谱对话_${new Date().toLocaleString('zh-CN').replace(/[\/:]/g, '-')}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// 清空历史记录
const clearHistory = () => {
  historyList.value = []
}

// 获取今日消息数
const getTodayMessages = () => {
  const today = new Date().toLocaleDateString('zh-CN')
  return messages.value.filter(msg => msg.time.startsWith(today)).length
}

onMounted(() => {
  // 配置marked
  marked.setOptions({
    highlight: function(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext'
      return hljs.highlight(code, { language }).value
    }
  })
  
  // 滚动到底部
  scrollToBottom()
})
</script>

<style scoped>
.chat {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    
    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    .chat-actions {
      display: flex;
      gap: 12px;
    }
  }

  .chat-container {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 24px;
    height: calc(100vh - 220px);

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
      height: auto;
    }
  }

  .chat-main {
    display: flex;
    flex-direction: column;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    overflow: hidden;
  }

  .chat-messages {
    flex: 1;
    padding: 24px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 20px;

    .message {
      display: flex;
      gap: 16px;
      margin-bottom: 12px;

      &.user {
        flex-direction: row-reverse;
        .message-content {
          background: #f0f9ff;
          border-radius: 12px 12px 0 12px;
        }
      }

      &.assistant {
        .message-content {
          background: #f5f7fa;
          border-radius: 12px 12px 12px 0;
        }

        &.loading {
          .message-content {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 20px;
          }
          .loading-spinner {
            width: 24px;
            height: 24px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
          .loading-text {
            color: #909399;
            font-size: 14px;
          }
        }
      }

      .message-avatar {
        flex-shrink: 0;
        
        .avatar {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          transition: all 0.3s ease;
          
          &.user-avatar {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
          }
          &.assistant-avatar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          }
        }
      }

      .message-content {
        flex: 1;
        padding: 20px;
        max-width: 80%;
        transition: all 0.3s ease;
        
        &:hover {
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .message-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          .message-author {
            font-size: 14px;
            font-weight: 600;
            color: #303133;
          }
          .message-time {
            font-size: 12px;
            color: #909399;
          }
        }

        .message-body {
          font-size: 14px;
          line-height: 1.6;
          color: #303133;
          margin-bottom: 12px;

          p {
            margin-bottom: 10px;
            &:last-child {
              margin-bottom: 0;
            }
          }

          h1, h2, h3, h4, h5, h6 {
            margin: 15px 0 10px 0;
            color: #303133;
          }

          code {
            background: #f0f0f0;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 12px;
          }

          pre {
            background: #f0f0f0;
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 10px 0;
            box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
          }

          pre code {
            background: none;
            padding: 0;
          }

          ul, ol {
            margin: 10px 0;
            padding-left: 20px;
          }

          li {
            margin-bottom: 5px;
          }
        }

        .message-actions {
          display: flex;
          gap: 8px;
          margin-top: 8px;
          padding-top: 12px;
          border-top: 1px solid #f0f2f5;
          
          .action-btn {
            background: none;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            color: #606266;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: all 0.3s ease;
            
            &:hover {
              background: #ecf5ff;
              border-color: #c6e2ff;
              color: #409eff;
            }
          }
        }
      }
    }
  }

  .chat-input-area {
    padding: 24px;
    border-top: 1px solid #f0f2f5;
    background: #fafafa;

    .input-wrapper {
      display: flex;
      gap: 12px;
      margin-bottom: 12px;

      textarea {
        flex: 1;
        border: 1px solid #dcdfe6;
        border-radius: 8px;
        padding: 14px;
        font-size: 14px;
        resize: none;
        min-height: 48px;
        max-height: 200px;
        font-family: inherit;
        background: white;
        transition: all 0.3s ease;

        &:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
        }
      }

      .input-actions {
        display: flex;
        gap: 10px;
        align-items: flex-end;
      }
    }

    .chat-tips {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #909399;

      .tip {
        font-weight: 600;
      }
    }
  }

  .chat-sidebar {
    display: flex;
    flex-direction: column;
    gap: 24px;

    @media (max-width: 768px) {
      margin-top: 24px;
    }

    .card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      padding: 20px;
      transition: all 0.3s ease;
      
      &:hover {
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
      }

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        
        h3 {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
          margin: 0;
        }
        
        .btn-sm {
          background: none;
          border: 1px solid #dcdfe6;
          border-radius: 4px;
          padding: 4px 8px;
          font-size: 12px;
          color: #606266;
          cursor: pointer;
          transition: all 0.3s ease;
          
          &:hover {
            background: #ecf5ff;
            border-color: #c6e2ff;
            color: #409eff;
          }
        }
      }

      h3 {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 16px;
        color: #303133;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .mode-selector {
        margin-bottom: 12px;
      }

      .history-list {
        max-height: 220px;
        overflow-y: auto;
        
        &::-webkit-scrollbar {
          width: 6px;
        }
        
        &::-webkit-scrollbar-track {
          background: #f1f1f1;
          border-radius: 3px;
        }
        
        &::-webkit-scrollbar-thumb {
          background: #c1c1c1;
          border-radius: 3px;
        }
        
        &::-webkit-scrollbar-thumb:hover {
          background: #a8a8a8;
        }

        .history-item {
          padding: 12px;
          border-radius: 8px;
          cursor: pointer;
          margin-bottom: 10px;
          transition: all 0.3s ease;
          border: 1px solid #f0f2f5;

          &:hover {
            background: #f0f9ff;
            border-color: #c6e2ff;
            transform: translateY(-1px);
          }

          .history-question {
            font-size: 13px;
            color: #303133;
            margin-bottom: 6px;
            line-height: 1.4;
            font-weight: 500;
          }

          .history-time {
            font-size: 11px;
            color: #909399;
          }
        }

        .empty-history {
          text-align: center;
          color: #909399;
          font-size: 13px;
          padding: 24px 0;
        }
      }

      .recommended-questions {
        .recommended-question {
          padding: 10px 14px;
          border-radius: 8px;
          cursor: pointer;
          margin-bottom: 10px;
          font-size: 13px;
          color: #606266;
          background: #f5f7fa;
          transition: all 0.3s ease;
          border: 1px solid #f0f2f5;

          &:hover {
            background: #ecf5ff;
            color: #409eff;
            border-color: #c6e2ff;
            transform: translateY(-1px);
          }
        }
      }

      .chat-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        
        .stat-item {
          text-align: center;
          background: #f5f7fa;
          padding: 16px;
          border-radius: 8px;
          transition: all 0.3s ease;
          
          &:hover {
            background: #ecf5ff;
            transform: translateY(-2px);
          }
          
          .stat-value {
            font-size: 20px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 4px;
          }
          .stat-label {
            font-size: 12px;
            color: #909399;
          }
        }
      }
    }
  }
}

/* 按钮样式 */
.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
  
  &:active {
    transform: translateY(0);
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    &:hover {
      transform: none;
      box-shadow: none;
    }
  }
}

.btn-secondary {
  background: #f5f7fa;
  color: #606266;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  
  &:hover {
    background: #ecf5ff;
    border-color: #c6e2ff;
    color: #409eff;
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>

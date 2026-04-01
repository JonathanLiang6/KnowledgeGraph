<template>
  <div class="home">
    <!-- 页面标题 -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="page-title">
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          知识图谱系统
        </h1>
        <p class="hero-subtitle">基于 GraphRAG 和 智谱AI 的智能知识管理平台</p>
      </div>
    </div>

    <!-- 系统概览卡片 -->
    <div class="overview-cards">
      <div class="card">
        <div class="card-header">
          <h3>系统概览</h3>
          <span class="badge">实时</span>
        </div>
        <div class="card-body">
          <div class="stats-grid">
            <div class="stat-item" @mouseenter="statHover = true" @mouseleave="statHover = false">
              <div class="stat-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
              </div>
              <div class="stat-value">{{ stats.entities }}</div>
              <div class="stat-label">实体数量</div>
            </div>
            <div class="stat-item" @mouseenter="statHover = true" @mouseleave="statHover = false">
              <div class="stat-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"></path>
                </svg>
              </div>
              <div class="stat-value">{{ stats.relationships }}</div>
              <div class="stat-label">关系数量</div>
            </div>
            <div class="stat-item" @mouseenter="statHover = true" @mouseleave="statHover = false">
              <div class="stat-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>
              <div class="stat-value">{{ stats.documents }}</div>
              <div class="stat-label">文档数量</div>
            </div>
            <div class="stat-item" @mouseenter="statHover = true" @mouseleave="statHover = false">
              <div class="stat-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                  <line x1="8" y1="21" x2="16" y2="21"></line>
                  <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
              </div>
              <div class="stat-value">{{ stats.chunks }}</div>
              <div class="stat-label">文本块数量</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 最近活动 -->
      <div class="card">
        <div class="card-header">
          <h3>最近活动</h3>
          <button class="btn-sm">查看全部</button>
        </div>
        <div class="card-body">
          <div class="activity-list">
            <div v-for="activity in activities" :key="activity.id" class="activity-item" @click="viewActivity(activity)">
              <div class="activity-icon" :class="activity.type">
                <svg v-if="activity.type === 'import'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                <svg v-else-if="activity.type === 'chat'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                </svg>
              </div>
              <div class="activity-content">
                <div class="activity-title">{{ activity.title }}</div>
                <div class="activity-time">{{ activity.time }}</div>
              </div>
              <div class="activity-arrow">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 功能卡片 -->
    <div class="feature-cards">
      <div class="card feature-card" @mouseenter="cardHover = true" @mouseleave="cardHover = false">
        <div class="feature-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <h3>智能问答</h3>
        <p>基于知识图谱的智能问答系统，提供准确的知识检索和回答</p>
        <router-link to="/chat" class="btn-primary">开始问答</router-link>
      </div>

      <div class="card feature-card" @mouseenter="cardHover = true" @mouseleave="cardHover = false">
        <div class="feature-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
        </div>
        <h3>图谱可视化</h3>
        <p>直观展示知识图谱的结构和关系，支持交互式探索</p>
        <router-link to="/graph" class="btn-primary">查看图谱</router-link>
      </div>

      <div class="card feature-card" @mouseenter="cardHover = true" @mouseleave="cardHover = false">
        <div class="feature-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
        </div>
        <h3>文档管理</h3>
        <p>管理知识图谱的源文档，支持文档上传和管理</p>
        <router-link to="/documents" class="btn-primary">管理文档</router-link>
      </div>

      <div class="card feature-card" @mouseenter="cardHover = true" @mouseleave="cardHover = false">
        <div class="feature-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </div>
        <h3>系统设置</h3>
        <p>配置系统参数和模型设置，优化知识图谱构建</p>
        <router-link to="/settings" class="btn-primary">系统设置</router-link>
      </div>
    </div>

    <!-- 技术栈展示 -->
    <div class="tech-stack">
      <h2>技术栈</h2>
      <div class="tech-icons">
        <div class="tech-item">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 18l6-6-6-6"></path>
            <path d="M8 6l-6 6 6 6"></path>
          </svg>
          <span>Vue 3</span>
        </div>
        <div class="tech-item">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
            <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
          </svg>
          <span>Element Plus</span>
        </div>
        <div class="tech-item">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
          <span>D3.js</span>
        </div>
        <div class="tech-item">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
          </svg>
          <span>智谱AI</span>
        </div>
        <div class="tech-item">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
          </svg>
          <span>FastAPI</span>
        </div>
        <div class="tech-item">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
          </svg>
          <span>SQLite</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

// 系统统计数据
const stats = ref({
  entities: 1280,
  relationships: 2560,
  documents: 12,
  chunks: 384
})

// 最近活动
const activities = ref([
  {
    id: 1,
    type: 'import',
    title: '导入了新文档《人工智能导论》',
    time: '2026-03-30 10:30'
  },
  {
    id: 2,
    type: 'chat',
    title: '回答了关于机器学习的问题',
    time: '2026-03-30 09:15'
  },
  {
    id: 3,
    type: 'import',
    title: '更新了知识图谱索引',
    time: '2026-03-29 16:45'
  },
  {
    id: 4,
    type: 'chat',
    title: '回答了关于深度学习的问题',
    time: '2026-03-29 14:20'
  }
])

// 交互状态
const statHover = ref(false)
const cardHover = ref(false)

// 查看活动详情
const viewActivity = (activity) => {
  console.log('查看活动详情:', activity)
  // 这里可以添加跳转到活动详情页面的逻辑
}

onMounted(() => {
  // 模拟加载数据
  console.log('首页数据加载完成')
  
  // 为统计数字添加动画效果
  animateStats()
})

// 统计数字动画
const animateStats = () => {
  const targets = [
    { ref: stats.value, key: 'entities', target: 1280 },
    { ref: stats.value, key: 'relationships', target: 2560 },
    { ref: stats.value, key: 'documents', target: 12 },
    { ref: stats.value, key: 'chunks', target: 384 }
  ]
  
  targets.forEach(item => {
    let current = 0
    const increment = item.target / 50
    const interval = setInterval(() => {
      current += increment
      if (current >= item.target) {
        item.ref[item.key] = item.target
        clearInterval(interval)
      } else {
        item.ref[item.key] = Math.floor(current)
      }
    }, 30)
  })
}
</script>

<style scoped>
.home {
  .hero-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 60px 0;
    margin-bottom: 40px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    
    .hero-content {
      text-align: center;
      color: white;
      
      .page-title {
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        
        svg {
          animation: pulse 2s infinite;
        }
      }
      
      .hero-subtitle {
        font-size: 18px;
        opacity: 0.9;
      }
    }
  }

  .overview-cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 40px;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }

  .card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px 24px;
      border-bottom: 1px solid #f0f2f5;
      
      h3 {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
        margin: 0;
      }
      
      .badge {
        background: #67c23a;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
      }
      
      .btn-sm {
        background: #f5f7fa;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
        padding: 4px 12px;
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
    
    .card-body {
      padding: 24px;
    }
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;

    @media (max-width: 768px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  .stat-item {
    text-align: center;
    padding: 20px;
    background: #f5f7fa;
    border-radius: 8px;
    transition: all 0.3s ease;
    cursor: pointer;
    
    &:hover {
      background: #ecf5ff;
      transform: translateY(-2px);
    }
    
    .stat-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 12px;
      color: white;
    }
    
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #667eea;
      margin-bottom: 6px;
      animation: countUp 1s ease-out;
    }
    
    .stat-label {
      font-size: 14px;
      color: #606266;
    }
  }

  .activity-list {
    .activity-item {
      display: flex;
      align-items: center;
      padding: 16px 0;
      border-bottom: 1px solid #f0f2f5;
      cursor: pointer;
      transition: all 0.3s ease;
      
      &:last-child {
        border-bottom: none;
      }
      
      &:hover {
        background: #f5f7fa;
        padding-left: 12px;
        border-radius: 8px;
      }
      
      .activity-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 16px;
        color: white;
        transition: all 0.3s ease;
        
        &.import {
          background: #67c23a;
        }
        &.chat {
          background: #409eff;
        }
        &.other {
          background: #e6a23c;
        }
      }
      
      .activity-content {
        flex: 1;
        
        .activity-title {
          font-size: 14px;
          color: #303133;
          margin-bottom: 4px;
          font-weight: 500;
        }
        
        .activity-time {
          font-size: 12px;
          color: #909399;
        }
      }
      
      .activity-arrow {
        color: #c0c4cc;
        transition: all 0.3s ease;
        
        &:hover {
          color: #409eff;
        }
      }
    }
  }

  .feature-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 24px;
    margin-bottom: 40px;
  }

  .feature-card {
    text-align: center;
    padding: 40px 24px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transition: all 0.3s ease;
    cursor: pointer;
    
    &:hover {
      transform: translateY(-8px);
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
    }
    
    .feature-icon {
      width: 96px;
      height: 96px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 24px;
      color: white;
      transition: all 0.3s ease;
      
      &:hover {
        transform: scale(1.1);
      }
    }
    
    h3 {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 12px;
      color: #303133;
    }
    
    p {
      font-size: 14px;
      color: #606266;
      margin-bottom: 24px;
      line-height: 1.6;
    }
    
    .btn-primary {
      display: inline-block;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      text-decoration: none;
      transition: all 0.3s ease;
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
      }
    }
  }
  
  .tech-stack {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    padding: 32px;
    margin-bottom: 40px;
    
    h2 {
      text-align: center;
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 32px;
    }
    
    .tech-icons {
      display: flex;
      justify-content: center;
      gap: 40px;
      flex-wrap: wrap;
      
      .tech-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        
        svg {
          width: 64px;
          height: 64px;
          background: #f5f7fa;
          border-radius: 12px;
          padding: 16px;
          color: #667eea;
          transition: all 0.3s ease;
          
          &:hover {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            transform: scale(1.1);
          }
        }
        
        span {
          font-size: 14px;
          color: #606266;
          font-weight: 500;
        }
      }
    }
  }
}

@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes countUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

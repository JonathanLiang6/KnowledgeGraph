<template>
  <div class="app-container">
    <!-- 头部导航 -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo">
          <div class="logo-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
          </div>
          <span>知识图谱系统</span>
        </div>
        
        <!-- 桌面端导航 -->
        <nav class="nav-menu" v-if="!isMobile">
          <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">首页</router-link>
          <router-link to="/chat" class="nav-item" :class="{ active: $route.path === '/chat' }">智能问答</router-link>
          <router-link to="/graph" class="nav-item" :class="{ active: $route.path === '/graph' }">图谱可视化</router-link>
          <router-link to="/documents" class="nav-item" :class="{ active: $route.path === '/documents' }">文档管理</router-link>
          <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">系统设置</router-link>
        </nav>
        
        <!-- 移动端菜单按钮 -->
        <button class="menu-toggle" v-else @click="toggleMenu">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <!-- 移动端导航菜单 -->
      <div class="mobile-menu" v-if="isMobile && menuOpen">
        <router-link to="/" class="mobile-nav-item" :class="{ active: $route.path === '/' }" @click="menuOpen = false">首页</router-link>
        <router-link to="/chat" class="mobile-nav-item" :class="{ active: $route.path === '/chat' }" @click="menuOpen = false">智能问答</router-link>
        <router-link to="/graph" class="mobile-nav-item" :class="{ active: $route.path === '/graph' }" @click="menuOpen = false">图谱可视化</router-link>
        <router-link to="/documents" class="mobile-nav-item" :class="{ active: $route.path === '/documents' }" @click="menuOpen = false">文档管理</router-link>
        <router-link to="/settings" class="mobile-nav-item" :class="{ active: $route.path === '/settings' }" @click="menuOpen = false">系统设置</router-link>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 页脚 -->
    <footer class="app-footer">
      <p>© 2026 知识图谱系统 | 基于 GraphRAG 和 智谱AI</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// 移动端检测和菜单控制
const isMobile = ref(false)
const menuOpen = ref(false)

// 检测屏幕尺寸
const checkScreenSize = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    menuOpen.value = false
  }
}

// 切换菜单
const toggleMenu = () => {
  menuOpen.value = !menuOpen.value
}

// 监听屏幕尺寸变化
onMounted(() => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
})
</script>

<style scoped>
/* 移动端菜单样式 */
.menu-toggle {
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 20px;
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-md);
  transition: var(--transition);
  
  &:hover {
    background: var(--bg-hover);
  }
}

.mobile-menu {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: var(--spacing-sm) 0;
  animation: slideDown 0.2s ease;
  
  .mobile-nav-item {
    display: block;
    color: var(--text-secondary);
    text-decoration: none;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 14px;
    font-weight: 500;
    transition: var(--transition);
    
    &:hover {
      color: var(--text-primary);
      background: var(--bg-hover);
    }
    
    &.active {
      color: var(--primary-light);
      font-weight: 600;
    }
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

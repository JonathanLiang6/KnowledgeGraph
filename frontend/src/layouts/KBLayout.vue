<template>
  <div class="kb-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <!-- 左侧导航栏 -->
    <aside class="kb-sidebar">
      <!-- 知识库头部 -->
      <div class="sidebar-header" v-if="kb">
        <div class="kb-icon-wrap">
          <BrainGraphLogo :size="44" variant="green" />
        </div>
        <div class="kb-info" v-if="!sidebarCollapsed">
          <h1 class="kb-name">{{ kb.name }}</h1>
          <div class="kb-meta">
            <span class="meta-dot" />
            <span>{{ kb.document_count }} 篇文档</span>
          </div>
        </div>
      </div>

      <div class="sidebar-header sidebar-loading" v-else-if="loading">
        <el-skeleton :rows="2" animated />
      </div>

      <!-- 导航项 -->
      <nav class="sidebar-nav" v-if="kb">
        <router-link :to="`/kb/${kbId}/graph`" class="nav-item" active-class="active">
          <el-icon :size="18" class="nav-icon"><Share /></el-icon>
          <span class="nav-label" v-if="!sidebarCollapsed">知识图谱</span>
        </router-link>
        <router-link :to="`/kb/${kbId}/chat`" class="nav-item" active-class="active">
          <el-icon :size="18" class="nav-icon"><ChatDotRound /></el-icon>
          <span class="nav-label" v-if="!sidebarCollapsed">智能问答</span>
        </router-link>
        <router-link :to="`/kb/${kbId}/documents`" class="nav-item" active-class="active">
          <el-icon :size="18" class="nav-icon"><Document /></el-icon>
          <span class="nav-label" v-if="!sidebarCollapsed">文档管理</span>
        </router-link>
        <router-link :to="`/kb/${kbId}/coverage`" class="nav-item" active-class="active">
          <el-icon :size="18" class="nav-icon"><DataAnalysis /></el-icon>
          <span class="nav-label" v-if="!sidebarCollapsed">知识体检</span>
        </router-link>
      </nav>

      <!-- 分隔线 -->
      <div class="sidebar-divider" v-if="kb && !sidebarCollapsed" />

      <!-- 返回首页（最底部） -->
      <div class="sidebar-bottom" v-if="kb">
        <button class="tool-item" @click="$router.push('/')" :title="sidebarCollapsed ? '返回首页' : ''">
          <el-icon :size="18" class="tool-icon"><ArrowLeft /></el-icon>
          <span class="tool-label" v-if="!sidebarCollapsed">返回首页</span>
        </button>
      </div>
    </aside>

    <!-- 折叠切换按钮（侧边栏右侧边缘，垂直居中）
         v4.2: 挂在布局层而非侧栏内 — 侧栏 overflow:hidden 会把 right:-12px
         悬边的按钮裁掉一半，移出后完整可见且随收起动画平移 -->
    <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开导航' : '收起导航'">
      <el-icon :size="18" class="collapse-icon" :class="{ flipped: !sidebarCollapsed }"><ArrowRight /></el-icon>
    </button>

    <!-- 内容区 -->
    <main class="kb-main">
      <template v-if="kb">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </template>
      <template v-else-if="error">
        <div class="error-state">
          <el-result icon="error" title="知识库不存在" sub-title="请检查链接或返回首页">
            <template #extra>
              <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
            </template>
          </el-result>
        </div>
      </template>
    </main>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getKnowledgeBase } from '../api/knowledgeBase'
import { ArrowRight, Document, Share, ChatDotRound, DataAnalysis, ArrowLeft } from '@element-plus/icons-vue'
import BrainGraphLogo from '../components/BrainGraphLogo.vue'

const route = useRoute()
const pageTransition = inject('pageTransition', null)
const kbId = computed(() => route.params.id)
const kb = ref(null)
const loading = ref(true)
const error = ref(false)
const sidebarCollapsed = ref(false)

async function fetchKB() {
  loading.value = true
  error.value = false
  try {
    kb.value = await getKnowledgeBase(kbId.value)
    await nextTick()
    setTimeout(() => {
      pageTransition?.hideNodeExpand?.()
    }, 100)
  } catch (e) {
    console.error('加载知识库失败:', e)
    error.value = true
    kb.value = null
    pageTransition?.hideNodeExpand?.()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchKB()
})

watch(() => route.params.id, (newId) => {
  if (newId) fetchKB()
})
</script>

<style scoped lang="scss">
$sidebar-width: 260px;
$sidebar-collapsed-width: 64px;

.kb-layout {
  min-height: 100vh;
  display: flex;
  background: var(--bg-page);
  transition: padding-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;  // v4.2: 折叠按钮以布局为定位基准
}

// ── 左侧导航栏 ──────────────────────────────────────────
.kb-sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: $sidebar-width;
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.sidebar-collapsed .kb-sidebar {
  width: $sidebar-collapsed-width;
}

// 折叠按钮（侧边栏右侧边缘，垂直居中）
// v4.2: 绝对定位于布局层（left 跟随侧栏宽度过渡），不再被侧栏 overflow:hidden 裁切
.collapse-btn {
  position: absolute;
  top: 50%;
  left: calc(#{$sidebar-width} - 12px);
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 101;  // 高于侧栏(z:100)
  box-shadow: 0 2px 8px rgba(27, 79, 52, 0.12);
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              background var(--transition-fast),
              color var(--transition-fast),
              border-color var(--transition-fast);

  .sidebar-collapsed & {
    left: calc(#{$sidebar-collapsed-width} - 12px);
  }

  &:hover {
    background: var(--color-primary);
    color: #fff;
    border-color: var(--color-primary);
  }

  .collapse-icon {
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &.flipped {
      transform: rotate(180deg);
    }
  }
}

// 知识库头部
.sidebar-header {
  padding: 20px 20px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.sidebar-collapsed .sidebar-header {
  padding: 20px 10px 16px;
  justify-content: center;
}

.kb-icon-wrap {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kb-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kb-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kb-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-tertiary);

  .meta-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-primary);
  }
}

.sidebar-loading {
  padding: 20px;
}

// 导航项（垂直居中区域）
.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition-fast);
  position: relative;
  background: transparent;
  border: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
  font-family: inherit;

  .nav-icon {
    flex-shrink: 0;
    color: var(--text-tertiary);
    transition: color var(--transition-fast);
  }

  .nav-label {
    flex: 1;
    white-space: nowrap;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);

    .nav-icon {
      color: var(--color-primary);
    }
  }

  &.active {
    background: var(--color-primary);
    color: #fff;

    .nav-icon {
      color: #fff;
    }

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 16px;
      background: var(--color-primary-light);
      border-radius: 0 2px 2px 0;
    }
  }
}

.sidebar-collapsed .nav-item {
  justify-content: center;
  padding: 10px;
}

// 分隔线
.sidebar-divider {
  height: 1px;
  background: var(--border-light);
  margin: 8px 14px;
}

// 底部区域
.sidebar-bottom {
  padding: 8px 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition-fast);
  width: 100%;
  text-align: left;
  font-family: inherit;

  .tool-icon {
    flex-shrink: 0;
    color: var(--text-tertiary);
    transition: color var(--transition-fast);
  }

  .tool-label {
    flex: 1;
    white-space: nowrap;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);

    .tool-icon {
      color: var(--color-primary);
    }
  }
}

.sidebar-collapsed .tool-item {
  justify-content: center;
  padding: 10px;
}

// ── 主内容区 ──────────────────────────────────────────
.kb-main {
  flex: 1;
  margin-left: $sidebar-width;
  padding: 0;
  min-height: 100vh;
  transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-collapsed .kb-main {
  margin-left: $sidebar-collapsed-width;
}

.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

// ── 知识体检弹窗 ──────────────────────────────────────────
.loading-state,
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.loading-state p {
  margin-top: 12px;
}

</style>

<template>
  <aside :class="['sidebar', { collapsed: collapsed }]">
    <!-- Logo -->
    <div class="sidebar-logo" @click="$router.push('/')">
      <div class="logo-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>
          <line x1="12" y1="7" x2="5" y2="17"/><line x1="12" y1="7" x2="19" y2="17"/>
          <line x1="5" y1="17" x2="19" y2="17"/>
        </svg>
      </div>
      <span v-show="!collapsed" class="logo-text">KnowledgeGraph</span>
    </div>

    <!-- 导航菜单 -->
    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      :router="true"
      class="sidebar-menu"
      background-color="transparent"
    >
      <el-menu-item index="/">
        <el-icon><Monitor /></el-icon>
        <span>仪表盘</span>
      </el-menu-item>

      <el-menu-item index="/knowledge-bases">
        <el-icon><Collection /></el-icon>
        <span>知识库</span>
      </el-menu-item>

      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>Chat Studio</span>
      </el-menu-item>

      <el-menu-item index="/graph">
        <el-icon><Share /></el-icon>
        <span>图谱工作台</span>
      </el-menu-item>

      <el-menu-item index="/documents">
        <el-icon><Document /></el-icon>
        <span>文档管理</span>
      </el-menu-item>

      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <span>系统设置</span>
      </el-menu-item>
    </el-menu>

    <!-- 底部折叠按钮 -->
    <div class="sidebar-footer">
      <button class="collapse-btn" @click="$emit('toggle')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
          :style="{ transform: collapsed ? 'rotate(180deg)' : 'rotate(0deg)' }">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, Collection, ChatDotRound, Share, Document, Setting } from '@element-plus/icons-vue'

defineProps({
  collapsed: { type: Boolean, default: false },
})
defineEmits(['toggle'])

const route = useRoute()
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/knowledge-bases')) return '/knowledge-bases'
  return path
})
</script>

<style scoped lang="scss">
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal);
  z-index: 100;
  overflow: hidden;

  &.collapsed {
    width: var(--sidebar-collapsed);
  }
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  cursor: pointer;
  color: var(--color-primary);

  .logo-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    background: var(--color-primary-gradient);
    color: #fff;
  }

  .logo-text {
    font-size: 16px;
    font-weight: 700;
    white-space: nowrap;
    background: var(--color-primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 8px;
  overflow-y: auto;

  :deep(.el-menu-item) {
    border-radius: var(--radius-sm);
    margin-bottom: 2px;
    height: 44px;
    line-height: 44px;
    color: var(--text-secondary);
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-page);
      color: var(--color-primary);
    }

    &.is-active {
      background: var(--color-primary-gradient);
      color: var(--text-inverse);
      box-shadow: var(--shadow-sm);
    }
  }

  :deep(.el-icon) {
    font-size: 18px;
  }
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: center;

  .collapse-btn {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-color);
    background: var(--bg-card);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-page);
      color: var(--color-primary);
      border-color: var(--color-primary-light);
    }
  }
}
</style>

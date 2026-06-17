<template>
  <header class="topbar">
    <div class="topbar-left">
      <!-- 面包屑 -->
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item v-if="currentPage">{{ currentPage }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="topbar-right">
      <!-- 知识库选择器 -->
      <el-select
        v-model="selectedKB"
        placeholder="选择知识库"
        size="small"
        style="width: 200px"
        clearable
        @change="onKBChange"
      >
        <el-option
          v-for="kb in kbs"
          :key="kb.id"
          :label="kb.name"
          :value="kb.id"
        />
      </el-select>

      <!-- 系统状态 -->
      <span class="status-dot" :class="{ active: apiConfigured }" />
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import { getKnowledgeBases } from '../api/knowledgeBase'
import { getSettings } from '../api/settings'

const route = useRoute()
const appStore = useAppStore()

const selectedKB = ref(null)
const kbs = ref([])
const apiConfigured = ref(false)

const currentPage = computed(() => {
  const map = {
    '/': '仪表盘',
    '/knowledge-bases': '知识库管理',
    '/chat': 'Chat Studio',
    '/graph': '图谱工作台',
    '/documents': '文档管理',
    '/settings': '系统设置',
  }
  return map[route.path] || ''
})

function onKBChange(val) {
  const kb = kbs.value.find(k => k.id === val)
  appStore.setCurrentKB(kb || null)
}

async function loadData() {
  try {
    const [kbRes, settingsRes] = await Promise.all([
      getKnowledgeBases(),
      getSettings(),
    ])
    kbs.value = kbRes.items || []
    appStore.setKnowledgeBases(kbs.value)
    apiConfigured.value = settingsRes.system_status?.api_configured || false
  } catch {}
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.topbar {
  height: var(--topbar-height);
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  position: sticky;
  top: 0;
  z-index: 50;
}

.topbar-left {
  :deep(.el-breadcrumb__inner) {
    color: var(--text-secondary);
    font-size: 13px;
  }
  :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
    color: var(--text-primary);
    font-weight: 500;
  }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-danger);
  transition: background var(--transition-normal);

  &.active {
    background: var(--color-success);
    box-shadow: 0 0 6px var(--color-success);
  }
}
</style>

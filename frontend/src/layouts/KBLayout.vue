<template>
  <div class="kb-layout">
    <!-- 知识库上下文头部 -->
    <header class="kb-header">
      <div class="kb-header-left">
        <button class="back-btn btn-ghost" @click="$router.push('/')">
          <el-icon :size="16"><ArrowLeft /></el-icon>
          <span>返回</span>
        </button>
        <div class="kb-title" v-if="kb">
          <el-icon :size="20" color="var(--color-primary)"><Collection /></el-icon>
          <h1>{{ kb.name }}</h1>
          <span class="kb-doc-count" v-if="kb.document_count > 0">{{ kb.document_count }} 篇文档</span>
        </div>
        <div class="kb-title skeleton-title" v-else-if="loading">
          <span class="skeleton" style="width:200px;height:28px" />
        </div>
        <div class="kb-title" v-else-if="error">
          <el-result icon="error" title="知识库不存在" sub-title="请检查链接或返回首页">
            <template #extra>
              <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
            </template>
          </el-result>
        </div>
      </div>
    </header>

    <!-- 子导航标签 -->
    <nav class="kb-nav" v-if="kb">
      <router-link :to="`/kb/${kbId}/graph`" class="nav-tab" active-class="active">
        <el-icon :size="16"><Share /></el-icon>
        <span>知识图谱</span>
      </router-link>
      <router-link :to="`/kb/${kbId}/chat`" class="nav-tab" active-class="active">
        <el-icon :size="16"><ChatDotRound /></el-icon>
        <span>智能问答</span>
      </router-link>
      <router-link :to="`/kb/${kbId}/documents`" class="nav-tab" active-class="active">
        <el-icon :size="16"><Document /></el-icon>
        <span>文档管理</span>
      </router-link>
    </nav>

    <!-- 子页面内容 -->
    <main class="kb-main">
      <template v-if="kb">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getKnowledgeBase } from '../api/knowledgeBase'
import { ArrowLeft, Collection, Document, Share, ChatDotRound } from '@element-plus/icons-vue'

const route = useRoute()
const kbId = computed(() => route.params.id)
const kb = ref(null)
const loading = ref(true)
const error = ref(false)

async function fetchKB() {
  loading.value = true
  error.value = false
  try {
    kb.value = await getKnowledgeBase(kbId.value)
  } catch (e) {
    console.error('加载知识库失败:', e)
    error.value = true
    kb.value = null
  } finally {
    loading.value = false
  }
}

onMounted(fetchKB)

// 路由参数变化时重新加载（切换知识库）
watch(() => route.params.id, (newId) => {
  if (newId) fetchKB()
})
</script>

<style scoped lang="scss">
.kb-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
}

.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 50;
  min-height: 56px;
}

.kb-header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.back-btn {
  padding: 6px 12px;
  font-size: 13px;
  flex-shrink: 0;
}

.kb-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);

  h1 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .kb-doc-count {
    font-size: 12px;
    color: var(--text-tertiary);
    padding: 2px 8px;
    background: var(--bg-page);
    border-radius: var(--radius-full);
  }
}

.skeleton-title {
  flex: 1;
}

.kb-nav {
  display: flex;
  gap: 0;
  padding: 0 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 56px;
  z-index: 40;
}

.nav-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: all var(--transition-fast);
  margin-bottom: -1px;

  &:hover {
    color: var(--color-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: var(--color-primary);
    border-bottom-color: var(--color-primary);
  }
}

.kb-main {
  flex: 1;
  padding: var(--spacing-lg) 24px;
}
</style>

<template>
  <div class="kb-layout">
    <!-- 知识库上下文头部 -->
    <header class="kb-header">
      <div class="kb-header-left">
        <button class="back-btn btn-ghost" @click="$router.push('/')">
          <el-icon :size="16" class="back-arrow"><ArrowLeft /></el-icon>
          <span>返回</span>
        </button>
        <div class="kb-title" v-if="kb">
          <el-icon :size="20" color="var(--color-primary)"><Collection /></el-icon>
          <h1>{{ kb.name }}</h1>
          <span class="kb-doc-count" v-if="kb.document_count > 0">
            <span class="count-dot" />
            {{ kb.document_count }} 篇文档
          </span>
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
      <div class="nav-inner">
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
        <!-- 滑动指示器 -->
        <div class="nav-indicator" ref="navIndicator" />
        <!-- v3.2: 知识体检按钮 -->
        <div class="nav-extra">
          <el-button size="small" text @click="openCoverageDialog">
            📊 知识体检
          </el-button>
        </div>
      </div>
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

    <!-- v3.2: 知识体检弹窗 -->
    <el-dialog
      v-model="showCoverage"
      title="📊 知识覆盖体检"
      width="700px"
      destroy-on-close
    >
      <div v-if="coverageLoading" style="text-align:center;padding:40px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="margin-top:12px;color:var(--text-secondary)">分析中...</p>
      </div>
      <div v-else-if="coverageError" style="text-align:center;padding:40px;color:var(--color-danger)">
        {{ coverageError }}
      </div>
      <div v-else-if="coverageData">
        <div class="coverage-summary">
          <span>{{ coverageData.total_entities }} 个实体</span>
          <span>·</span>
          <span>{{ coverageData.category_count }} 个分类</span>
        </div>
        <div ref="chartRef" style="width:100%;height:380px;margin-top:16px" />
      </div>
      <div v-else style="text-align:center;padding:40px;color:var(--text-tertiary)">
        暂无数据
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getKnowledgeBase } from '../api/knowledgeBase'
import { ArrowLeft, Collection, Document, Share, ChatDotRound, Loading } from '@element-plus/icons-vue'
import api from '../api'
import * as echarts from 'echarts'

const route = useRoute()
const kbId = computed(() => route.params.id)
const kb = ref(null)
const loading = ref(true)
const error = ref(false)
const navIndicator = ref(null)

// v3.2: 知识体检
const showCoverage = ref(false)
const coverageLoading = ref(false)
const coverageError = ref('')
const coverageData = ref(null)
const chartRef = ref(null)

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

async function openCoverageDialog() {
  showCoverage.value = true
  coverageLoading.value = true
  coverageError.value = ''
  coverageData.value = null
  try {
    const data = await api.get(`/analytics/kb/${kbId.value}/coverage`)
    coverageData.value = data
    await nextTick()
    renderTreemap()
  } catch (e) {
    coverageError.value = e.message || '获取覆盖数据失败'
  } finally {
    coverageLoading.value = false
  }
}

function renderTreemap() {
  if (!chartRef.value || !coverageData.value) return
  const chart = echarts.init(chartRef.value)

  const categories = coverageData.value.categories || []
  // 按实体数降序
  categories.sort((a, b) => b.count - a.count)

  const maxDays = Math.max(...categories.map(c => c.last_updated_days), 1)

  chart.setOption({
    tooltip: {
      formatter: (params) => {
        const d = params.data
        return `<b>${d.name}</b><br/>实体数: ${d.value}<br/>最后更新: ${d.last_updated_days} 天前`
      },
    },
    series: [{
      type: 'treemap',
      data: categories.map(c => ({
        name: c.name,
        value: c.count,
        last_updated_days: c.last_updated_days,
        itemStyle: {
          // 颜色深浅：红色=老旧(>30天)，绿色=新鲜(<7天)，黄色=普通
          color: c.last_updated_days > 30
            ? `rgba(220,80,80,${0.5 + (1 - c.last_updated_days / maxDays) * 0.5})`
            : c.last_updated_days > 7
              ? `rgba(230,162,60,${0.5 + (1 - c.last_updated_days / maxDays) * 0.5})`
              : `rgba(45,140,78,${0.4 + (1 - c.last_updated_days / maxDays) * 0.6})`,
        },
      })),
      label: {
        show: true,
        formatter: (params) => `${params.name}\n${params.value}`,
        fontSize: 12,
      },
      upperLabel: {
        show: true,
        height: 20,
      },
      roam: false,
      width: '100%',
      height: '100%',
    }],
  })

  // 响应式调整
  const observer = new ResizeObserver(() => chart.resize())
  observer.observe(chartRef.value)
}

// 滑动指示器位置更新
function updateNavIndicator() {
  nextTick(() => {
    if (!navIndicator.value) return
    const active = document.querySelector('.nav-tab.active')
    if (active) {
      navIndicator.value.style.width = `${active.offsetWidth}px`
      navIndicator.value.style.transform = `translateX(${active.offsetLeft}px)`
    }
  })
}

onMounted(() => {
  fetchKB()
  updateNavIndicator()
  window.addEventListener('resize', updateNavIndicator)
})

watch(() => route.params.id, (newId) => {
  if (newId) fetchKB()
})

watch(() => route.path, () => {
  updateNavIndicator()
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
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 50;
  min-height: 56px;

  // 渐变底边
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      var(--color-primary-light) 30%,
      var(--color-primary) 50%,
      var(--color-primary-light) 70%,
      transparent 100%
    );
    opacity: 0.5;
  }
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

  .back-arrow {
    transition: transform var(--transition-fast);
  }

  &:hover .back-arrow {
    transform: translateX(-3px);
  }
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
    padding: 2px 10px;
    background: var(--bg-page);
    border-radius: var(--radius-full);
    display: flex;
    align-items: center;
    gap: 5px;

    .count-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--color-primary);
      animation: dot-pulse 2s ease-in-out infinite;
    }
  }
}

.skeleton-title {
  flex: 1;
}

// ── 导航标签 ──────────────────────────────────────────
.kb-nav {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 56px;
  z-index: 40;
}

.nav-inner {
  display: flex;
  position: relative;
  padding: 0 24px;
}

.nav-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 13px 22px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--transition-fast);
  position: relative;
  z-index: 1;

  &:hover {
    color: var(--color-primary);
  }

  &.active {
    color: var(--color-primary);
    font-weight: 600;
  }
}

// 滑动指示器
.nav-indicator {
  position: absolute;
  bottom: 0;
  left: 24px;
  height: 2.5px;
  border-radius: 2px;
  background: var(--color-primary-gradient);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1),
              width 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 0;
}

// v3.2: 右侧操作区
.nav-extra {
  margin-left: auto;
  display: flex;
  align-items: center;
  padding-right: 8px;
}

.kb-main {
  flex: 1;
  padding: var(--spacing-lg) 24px;
}

// v3.2: 知识体检
.coverage-summary {
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 8px 0;
  background: var(--bg-page);
  border-radius: var(--radius-sm);
}
</style>

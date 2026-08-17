<template>
  <div class="coverage-page">
    <div class="page-header">
      <h1>知识体检</h1>
      <el-button type="primary" @click="analyze" :loading="loading">
        重新分析
      </el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>分析中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <el-icon color="#F56C6C" :size="24"><WarningFilled /></el-icon>
      <p>{{ error }}</p>
      <el-button type="primary" plain @click="analyze">重试</el-button>
    </div>

    <div v-else-if="categories.length" class="coverage-content">
      <!-- 概览卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-num">{{ totalEntities }}</div>
          <div class="stat-label">总实体数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ categories.length }}</div>
          <div class="stat-label">分类数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ avgPerCategory }}</div>
          <div class="stat-label">平均每类实体</div>
        </div>
        <div class="stat-card" :title="topCategory?.name">
          <div class="stat-num">{{ topCategory?.count ?? 0 }}</div>
          <div class="stat-label">最大分类：{{ topCategory?.name || '-' }}</div>
        </div>
      </div>

      <!-- 分类分布图 -->
      <div class="chart-section">
        <h3>分类分布</h3>
        <div ref="chartRef" class="chart-container" />
      </div>

      <!-- 覆盖度分析 -->
      <div class="analysis-section">
        <h3>覆盖度分析</h3>
        <div class="coverage-list">
          <div v-for="cat in categories" :key="cat.name" class="coverage-item">
            <div class="coverage-header">
              <span class="coverage-category">{{ cat.name }}</span>
              <span class="coverage-count">{{ cat.count }} 个实体 · {{ formatUpdated(cat.last_updated_days) }}</span>
            </div>
            <div class="coverage-bar">
              <div class="coverage-fill" :style="{ width: barWidth(cat.count) + '%', background: barColor(cat.name) }" />
            </div>
            <div class="coverage-meta">
              <span>占比 {{ percentOf(cat.count) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="data" class="empty-state">
      <BrainGraphLogo :size="80" variant="green" />
      <p>该知识库暂无实体数据，请先上传文档并构建图谱</p>
    </div>

    <div v-else class="empty-state">
      <BrainGraphLogo :size="80" variant="green" />
      <p>点击上方按钮开始分析知识库</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Loading, WarningFilled } from '@element-plus/icons-vue'
import BrainGraphLogo from '../components/BrainGraphLogo.vue'
import api from '../api'
import * as echarts from 'echarts'

const route = useRoute()
const kbId = route.params.id

const loading = ref(false)
const error = ref('')
const data = ref(null)
const chartRef = ref(null)
let chartInstance = null

// 按实体数降序，与后端契约一致：categories: [{name, count, last_updated_days}]
const categories = computed(() => data.value?.categories ?? [])
const totalEntities = computed(() => data.value?.total_entities ?? 0)
const topCategory = computed(() => categories.value[0] ?? null)
const avgPerCategory = computed(() => {
  if (!categories.value.length) return '0'
  return (totalEntities.value / categories.value.length).toFixed(1)
})

const BAR_COLORS = ['#3a9d5b', '#5fb877', '#8fcc9f', '#a9d8b6', '#c4e5cd']

function barColor(name) {
  const idx = categories.value.findIndex(c => c.name === name)
  return BAR_COLORS[idx % BAR_COLORS.length]
}

function barWidth(count) {
  const max = topCategory.value?.count || 1
  return Math.max(2, Math.round((count / max) * 100))
}

function percentOf(count) {
  if (!totalEntities.value) return '0.0'
  return ((count / totalEntities.value) * 100).toFixed(1)
}

function formatUpdated(days) {
  if (days === null || days === undefined) return '暂无更新记录'
  if (days === 0) return '今天更新'
  if (days === 1) return '1 天前更新'
  return `约 ${days} 天前更新`
}

async function analyze() {
  loading.value = true
  error.value = ''
  try {
    // 拦截器已解包 response.data，这里直接拿到后端返回体
    const payload = await api.get(`/analytics/kb/${kbId}/coverage`)
    data.value = payload
  } catch (e) {
    // 拦截器 reject 的是 plain Error，从 e.message 取信息
    error.value = e.message || '分析失败，请稍后重试'
  } finally {
    loading.value = false
    // v4.1 修复：图表容器在 v-else-if 分支内，必须等 loading 结束、容器挂载后
    // 再初始化 ECharts（此前在 loading 期间调用，chartRef 为 null 直接跳过，
    // 导致"分类分布"永远空白）
    await nextTick()
    if (!error.value && categories.value.length) renderChart()
  }
}

// 具名 resize 处理器，便于卸载时移除（重复 addEventListener 同引用会去重）
function handleResize() {
  chartInstance?.resize()
}

function renderChart() {
  if (!chartRef.value || !categories.value.length) return
  // 重渲染前释放旧实例，避免泄漏
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  chartInstance = echarts.init(chartRef.value)
  window.addEventListener('resize', handleResize)

  // v4.2: 柱状图 → 环形饼图（占比关系一目了然），森林绿系渐变色板
  const GREEN_PALETTE = [
    '#3a9d5b', '#6bc285', '#93d5a8', '#2e7d50', '#4fb374',
    '#7ed09b', '#a5ddb8', '#57c084', '#c3e9d2', '#8ccfa2',
  ]
  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.name}：${p.value} 个实体（${p.percent}%）`
    },
    legend: {
      orient: 'horizontal',
      bottom: 0,
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#606266', fontSize: 12 }
    },
    color: GREEN_PALETTE,
    series: [{
      type: 'pie',
      radius: ['44%', '70%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        formatter: '{b} {d}%',
        color: '#606266',
        fontSize: 12,
        lineHeight: 16,
      },
      labelLine: { length: 12, length2: 8 },
      emphasis: {
        scale: true,
        scaleSize: 6,
        itemStyle: { shadowBlur: 16, shadowColor: 'rgba(58, 157, 91, 0.35)' },
      },
      data: categories.value.map(c => ({ name: c.name, value: c.count })),
    }]
  })
}

onMounted(() => {
  analyze()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped lang="scss">
.coverage-page {
  min-height: 100vh;
  padding: var(--spacing-lg);
  background: var(--bg-page);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);

  h1 {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 80px var(--spacing-lg);
  color: var(--text-secondary);

  p {
    margin-top: 12px;
  }
}

.error-state {
  color: var(--color-danger);

  .el-button {
    margin-top: 8px;
  }
}

.empty-state {
  :deep(.brain-logo) {
    margin: 0 auto 16px;
    opacity: 0.4;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  text-align: center;

  .stat-num {
    font-size: 28px;
    font-weight: 700;
    color: var(--color-primary);
  }

  .stat-label {
    font-size: 13px;
    color: var(--text-tertiary);
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.chart-section,
.analysis-section {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);

  h3 {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-md);
  }
}

.chart-container {
  width: 100%;
  height: 320px;
}

.coverage-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.coverage-item {
  background: var(--bg-page);
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
}

.coverage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;

  .coverage-category {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .coverage-count {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

.coverage-bar {
  height: 8px;
  background: var(--border-light);
  border-radius: 4px;
  overflow: hidden;
}

.coverage-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.8s ease;
}

.coverage-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>

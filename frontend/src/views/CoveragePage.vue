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
    </div>

    <div v-else-if="data" class="coverage-content">
      <!-- 概览卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-num">{{ data.total_entities }}</div>
          <div class="stat-label">总实体数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ data.category_count }}</div>
          <div class="stat-label">分类数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ data.total_relations }}</div>
          <div class="stat-label">关系数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ data.avg_relations_per_entity }}</div>
          <div class="stat-label">平均关系度</div>
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
          <div v-for="(item, category) in data.category_coverage" :key="category" class="coverage-item">
            <div class="coverage-header">
              <span class="coverage-category">{{ category }}</span>
              <span class="coverage-count">{{ item.count }} 个实体</span>
            </div>
            <div class="coverage-bar">
              <div class="coverage-fill" :style="{ width: item.coverage + '%', background: item.color }" />
            </div>
            <div class="coverage-meta">
              <span>覆盖度 {{ item.coverage }}%</span>
              <span>关键实体 {{ item.key_entities }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 建议 -->
      <div class="suggestions-section">
        <h3>优化建议</h3>
        <ul class="suggestions-list">
          <li v-for="(suggestion, i) in data.suggestions" :key="i">
            <el-icon :size="16"><InfoFilled /></el-icon>
            <span>{{ suggestion }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div v-else class="empty-state">
      <BrainGraphLogo :size="80" variant="green" />
      <p>点击上方按钮开始分析知识库</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Loading, WarningFilled, InfoFilled } from '@element-plus/icons-vue'
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

async function analyze() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/api/v1/knowledge_base/${kbId}/coverage`)
    data.value = res.data
    await nextTick()
    renderChart()
  } catch (e) {
    error.value = e.response?.data?.detail || '分析失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value || !data.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const categories = Object.keys(data.value.category_coverage)
  const values = categories.map(c => data.value.category_coverage[c].count)
  const colors = categories.map(c => data.value.category_coverage[c].color)

  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      bottom: 0,
      left: 'center'
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        formatter: '{b}\n{d}%'
      },
      labelLine: {
        show: true
      },
      data: categories.map((c, i) => ({
        value: values[i],
        name: c,
        itemStyle: { color: colors[i] }
      }))
    }]
  })

  window.addEventListener('resize', () => chartInstance?.resize())
}

onMounted(() => {
  analyze()
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
  }
}

.chart-section,
.analysis-section,
.suggestions-section {
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

.suggestions-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);

  li {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(58, 157, 91, 0.05);
    border-radius: var(--radius-sm);
    font-size: 14px;
    color: var(--text-secondary);

    :deep(.el-icon) {
      color: var(--color-primary);
      flex-shrink: 0;
      margin-top: 2px;
    }
  }
}
</style>

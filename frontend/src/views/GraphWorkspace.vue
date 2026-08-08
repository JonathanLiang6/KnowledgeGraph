<template>
  <div class="graph-workspace">
    <div class="graph-main">
      <canvas ref="canvasRef" class="graph-canvas" />

      <!-- 右侧面板容器（上中下排布） -->
      <div class="right-panels">
        <!-- 上：图谱统计 -->
        <div class="stats-panel glass-card">
          <h4>图谱统计</h4>
          <div class="stat-row"><span>节点数</span><strong>{{ nodeCount }}</strong></div>
          <div class="stat-row"><span>边数</span><strong>{{ linkCount }}</strong></div>
          <div class="stat-row" v-if="bridgeCount > 0">
            <span>虚线桥接</span><strong>{{ bridgeCount }}</strong>
          </div>
        </div>

        <!-- 中：图例 + 类型筛选 -->
        <div class="legend-panel glass-card" v-if="legend && Object.keys(legend).length > 0">
          <div class="legend-header">
            <h4>图例</h4>
            <div class="legend-toggle">
              <button class="legend-btn" @click="toggleAllTypes(true)">全选</button>
              <button class="legend-btn" @click="toggleAllTypes(false)">全不选</button>
            </div>
          </div>
          <div v-for="(color, type) in legend" :key="type" class="legend-item">
            <label class="legend-label" :style="{ opacity: hiddenTypes.has(type) ? 0.4 : 1 }">
              <input
                type="checkbox"
                :checked="!hiddenTypes.has(type)"
                @change="toggleType(type)"
              />
              <span class="legend-dot" :style="{ background: color }" />
              <span>{{ type }}</span>
            </label>
          </div>
        </div>

        <!-- 下：工具栏（调整/重置/更新） -->
        <div class="toolbar-panel glass-card">
          <div class="size-control">
            <span class="size-label">大小</span>
            <el-slider v-model="nodeSizeScale" :min="0.5" :max="1.5" :step="0.1" :show-input="false" width="100" @input="onSizeChange" />
          </div>
          <div class="weight-control">
            <span class="size-label">权重</span>
            <el-slider v-model="minWeight" :min="0" :max="1" :step="0.05" :show-input="false" width="100" @input="onWeightChange" />
          </div>
          <div class="toolbar-buttons">
            <button class="btn-secondary btn-sm" @click="resetView">重置视图</button>
            <button class="btn-primary btn-sm" @click="refreshData">刷新数据</button>
          </div>
        </div>
      </div>

      <!-- 底部操作提示（居中） -->
      <div class="hint-bar">
        <span>滚轮缩放</span>
        <span class="hint-divider">|</span>
        <span>拖拽平移</span>
        <span class="hint-divider">|</span>
        <span>点击节点查看详情</span>
        <span class="hint-divider">|</span>
        <span>图例筛选类型</span>
      </div>
    </div>

    <!-- 实体详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="实体详情" size="380px">
      <template v-if="selectedEntity">
        <div class="entity-detail">
          <div class="entity-header">
            <span class="entity-dot" :style="{ background: selectedEntity.color }" />
            <h3>{{ selectedEntity.name }}</h3>
          </div>
          <el-tag :style="{ background: selectedEntity.color + '20', color: selectedEntity.color, borderColor: selectedEntity.color + '40' }" size="small">
            {{ selectedEntity.type }}
          </el-tag>
          <div class="entity-meta">
            <div class="meta-item">
              <span class="meta-label">权重</span>
              <span class="meta-value">{{ (selectedEntity.weight || 0).toFixed(3) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">关联</span>
              <span class="meta-value">{{ relatedLinkCount }}</span>
            </div>
          </div>
          <div class="entity-related" v-if="relatedNodes.length > 0">
            <h4>关联实体 <span class="related-hint">(点击跳转)</span></h4>
            <div
              v-for="rn in relatedNodes"
              :key="rn.id"
              class="related-item clickable"
              @click="navigateToEntity(rn)"
            >
              <span class="related-dot" :style="{ background: rn.color }" />
              <span class="related-name">{{ rn.name }}</span>
              <span class="related-type">{{ rn.type }}</span>
              <span class="related-rel">{{ rn.relation }}</span>
              <el-icon class="related-arrow" :size="12"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </template>
      <el-empty v-else description="点击图谱中的节点查看详情" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, markRaw, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useGraphRenderer } from '../composables/useGraphRenderer'
import { getGraphData, getEntityDetail } from '../api/graph'
import { ElMessage } from 'element-plus'
import { Minus, Plus, ArrowRight } from '@element-plus/icons-vue'

const route = useRoute()
const canvasRef = ref(null)
const legend = ref({})
const nodeCount = ref(0)
const linkCount = ref(0)
const bridgeCount = ref(0)
const nodeSizeScale = ref(0.8)
const minWeight = ref(0.0)
const selectedEntity = ref(null)
const drawerVisible = ref(false)
const graphWidth = ref(1000)
const graphHeight = ref(600)
const hiddenTypes = reactive(new Set())

let renderer = null
const currentNodeData = ref([])
const currentLinkData = ref([])

const relatedLinkCount = computed(() => {
  if (!selectedEntity.value) return 0
  return currentLinkData.value.filter(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source
    const tid = typeof l.target === 'object' ? l.target.id : l.target
    return sid === selectedEntity.value.id || tid === selectedEntity.value.id
  }).length
})

const relatedNodes = computed(() => {
  if (!selectedEntity.value) return []
  const result = []
  for (const l of currentLinkData.value) {
    const sid = typeof l.source === 'object' ? l.source.id : l.source
    const tid = typeof l.target === 'object' ? l.target.id : l.target
    let otherId = null
    if (sid === selectedEntity.value.id) otherId = tid
    else if (tid === selectedEntity.value.id) otherId = sid
    if (otherId) {
      const other = currentNodeData.value.find(n => n.id === otherId)
      if (other && !result.find(r => r.id === otherId)) {
        result.push({
          ...other,
          relation: l.relation || '关联',
          dashed: l.dashed || false,
        })
      }
    }
  }
  return result
})

function handleNodeClick(node) {
  if (node) {
    selectedEntity.value = node
    drawerVisible.value = true
  }
}

function navigateToEntity(entity) {
  if (!renderer || !entity) return
  // 确保该类型可见
  if (hiddenTypes.has(entity.type)) {
    hiddenTypes.delete(entity.type)
    renderer.setHiddenTypes([...hiddenTypes])
  }
  // 居中到目标节点
  renderer.centerOn(entity)
  // 更新抽屉内容
  selectedEntity.value = entity
  drawerVisible.value = true
}

function toggleType(type) {
  if (hiddenTypes.has(type)) {
    hiddenTypes.delete(type)
  } else {
    hiddenTypes.add(type)
  }
  if (renderer) renderer.setHiddenTypes([...hiddenTypes])
}

function toggleAllTypes(show) {
  if (show) {
    hiddenTypes.clear()
  } else {
    Object.keys(legend.value).forEach(t => hiddenTypes.add(t))
  }
  if (renderer) renderer.setHiddenTypes([...hiddenTypes])
}

function onSizeChange(val) {
  if (renderer) renderer.setNodeSizeScale(val)
}

function onWeightChange(val) {
  if (renderer) renderer.setMinWeight(val)
}

async function refreshData() {
  try {
    const res = await getGraphData({ kb_id: route.params.id, limit: 200 })
    const data = markRaw({
      nodes: res.nodes || [],
      links: res.links || [],
    })
    currentNodeData.value = data.nodes
    currentLinkData.value = data.links
    nodeCount.value = data.nodes.length
    linkCount.value = data.links.length
    bridgeCount.value = data.links.filter(l => l.dashed).length
    legend.value = res.legend || {}

    // 重置类型筛选
    hiddenTypes.clear()

    if (renderer) renderer.stop()
    if (canvasRef.value) {
      renderer = useGraphRenderer(canvasRef, graphWidth, graphHeight, handleNodeClick)
      renderer.init(data, nodeSizeScale.value)
    }
  } catch (e) {
    console.error('加载图谱数据失败:', e)
    ElMessage.error('加载图谱数据失败')
  }
}

function resetView() { refreshData() }

function updateSize() {
    const container = canvasRef.value?.parentElement
    if (container) {
      graphWidth.value = container.clientWidth
      graphHeight.value = container.clientHeight
    } else {
      graphWidth.value = window.innerWidth - 280
      graphHeight.value = window.innerHeight - 60
    }
    if (renderer) renderer.resize(graphWidth.value, graphHeight.value)
  }

watch(() => route.params.id, () => refreshData())

onMounted(() => {
  updateSize()
  window.addEventListener('resize', updateSize)
  refreshData()
})

onUnmounted(() => {
  window.removeEventListener('resize', updateSize)
  if (renderer) renderer.stop()
})
</script>

<style scoped lang="scss">
.graph-workspace {
  height: 100vh;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
}

.graph-main {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0;
}

.weight-label {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.graph-main {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0;
  background: var(--bg-card);
}

.graph-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

// ── 右侧面板容器（上中下排布） ──────────────────────
.right-panels {
  position: absolute;
  top: var(--spacing-md);
  right: var(--spacing-md);
  bottom: var(--spacing-md);
  width: 180px;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  z-index: 10;
  pointer-events: none;

  > * {
    pointer-events: auto;
  }
}

// ── 图例面板 ──────────────────────────────────────────
.legend-panel {
  padding: var(--spacing-md);
  min-width: 0;
  max-height: 100%;
  overflow-y: auto;
  animation: fadeInUp 0.4s cubic-bezier(0.22, 1, 0.36, 1) 0.1s both;

  h4 { font-size: 13px; margin: 0; color: var(--text-secondary); }

  .legend-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-sm);
    gap: var(--spacing-sm);
  }

  .legend-toggle {
    display: flex;
    gap: 3px;
  }

  .legend-btn {
    font-size: 10px;
    padding: 2px 8px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-xs);
    background: var(--bg-page);
    color: var(--text-tertiary);
    cursor: pointer;
    transition: all var(--transition-fast);
    &:hover {
      color: var(--color-primary);
      border-color: var(--color-primary);
      background: var(--bg-hover);
    }
  }
}

.stats-panel {
  padding: var(--spacing-md);
  min-width: 0;
  animation: fadeInUp 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;

  h4 { font-size: 13px; margin-bottom: var(--spacing-sm); color: var(--text-secondary); }
}

// 工具栏面板
.toolbar-panel {
  padding: var(--spacing-md);
  min-width: 0;
  animation: fadeInUp 0.4s cubic-bezier(0.22, 1, 0.36, 1) 0.2s both;

  .size-control,
  .weight-control {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);

    .size-label {
      font-size: 12px;
      color: var(--text-tertiary);
      white-space: nowrap;
      min-width: 28px;
    }

    :deep(.el-slider__bar) {
      background: var(--color-primary-gradient);
    }
  }

  .toolbar-buttons {
    display: flex;
    gap: 6px;
    margin-top: var(--spacing-sm);

    .btn-sm {
      flex: 1;
      padding: 6px 8px;
      font-size: 12px;
    }
  }
}

// 底部操作提示（居中）
.hint-bar {
  position: absolute;
  bottom: var(--spacing-md);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-glass);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 6px 16px;
  border-radius: var(--radius-full);
  pointer-events: none;
  box-shadow: var(--shadow-sm);
  z-index: 10;

  .hint-divider {
    color: var(--border-light);
    margin: 0 2px;
  }
}

.legend-item {
  margin-bottom: 3px;

  .legend-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
    padding: 3px 4px;
    border-radius: var(--radius-xs);
    transition: background var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
    }

    input[type="checkbox"] {
      width: 13px;
      height: 13px;
      cursor: pointer;
      accent-color: var(--color-primary);
    }
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 6px currentColor;
    transition: box-shadow var(--transition-fast);

    .legend-label:hover & {
      box-shadow: 0 0 10px currentColor;
    }
  }
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 6px;
  gap: var(--spacing-md);

  strong {
    font-size: 15px;
    font-weight: 600;
    color: var(--color-primary);
    font-family: var(--font-mono);
    transition: transform var(--transition-fast);
  }

  &:hover strong {
    transform: translateX(2px);
  }
}

.entity-detail {
  .entity-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);

    .entity-dot {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      flex-shrink: 0;
      box-shadow: 0 0 8px currentColor;
    }

    h3 { font-size: 18px; font-weight: 600; }
  }

  .entity-meta {
    margin-top: var(--spacing-lg);
    display: flex;
    gap: var(--spacing-xl);

    .meta-item {
      display: flex;
      flex-direction: column;
      .meta-label { font-size: 12px; color: var(--text-tertiary); margin-bottom: 2px; }
      .meta-value {
        font-size: 22px;
        font-weight: 600;
        color: var(--color-primary);
        font-family: var(--font-mono);
        transition: transform var(--transition-fast);
      }
    }
  }

  .entity-related {
    margin-top: var(--spacing-xl);
    h4 {
      font-size: 14px;
      margin-bottom: var(--spacing-md);
      color: var(--text-secondary);
      .related-hint { font-size: 11px; color: var(--text-tertiary); font-weight: 400; }
    }

    .related-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 1px solid var(--border-light);
      border-radius: var(--radius-sm);
      transition: all var(--transition-fast);

      &.clickable {
        cursor: pointer;
        &:hover {
          background: var(--bg-hover);
          transform: translateX(4px);

          .related-name { color: var(--color-primary); }
          .related-arrow { opacity: 1; transform: translateX(0); }
        }
      }

      .related-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
      .related-name { font-weight: 500; flex: 1; transition: color var(--transition-fast); }
      .related-type { font-size: 11px; color: var(--text-tertiary); }
      .related-rel {
        font-size: 11px;
        color: var(--color-primary);
        background: var(--bg-active);
        padding: 1px 10px;
        border-radius: var(--radius-full);
      }
      .related-arrow {
        color: var(--text-tertiary);
        flex-shrink: 0;
        opacity: 0.4;
        transform: translateX(-4px);
        transition: all var(--transition-fast);
      }
    }
  }
}
</style>

<template>
  <div class="graph-workspace">
    <div class="graph-toolbar">
      <h1 class="page-title">知识图谱</h1>
      <div class="toolbar-actions">
        <div class="size-control">
          <el-icon :size="14"><Minus /></el-icon>
          <el-slider
            v-model="nodeSizeScale"
            :min="0.5"
            :max="1.5"
            :step="0.1"
            style="width:100px"
            @input="onSizeChange"
          />
          <el-icon :size="14"><Plus /></el-icon>
          <span class="size-label">节点 {{ Math.round(nodeSizeScale * 100) }}%</span>
        </div>
        <div class="weight-control">
          <span class="weight-label">权重 ≥</span>
          <el-slider
            v-model="minWeight"
            :min="0"
            :max="1"
            :step="0.05"
            style="width:80px"
            @input="onWeightChange"
          />
          <span class="size-label">{{ minWeight.toFixed(2) }}</span>
        </div>
        <button class="btn-secondary btn-sm" @click="resetView">重置视图</button>
        <button class="btn-primary btn-sm" @click="refreshData">刷新数据</button>
      </div>
    </div>

    <div class="graph-main">
      <canvas ref="canvasRef" class="graph-canvas" />

      <!-- 图例 + 类型筛选 -->
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

      <!-- 统计 -->
      <div class="stats-panel glass-card">
        <h4>图谱统计</h4>
        <div class="stat-row"><span>节点数</span><strong>{{ nodeCount }}</strong></div>
        <div class="stat-row"><span>边数</span><strong>{{ linkCount }}</strong></div>
        <div class="stat-row" v-if="bridgeCount > 0">
          <span>虚线桥接</span><strong>{{ bridgeCount }}</strong>
        </div>
      </div>

      <!-- 操作提示 -->
      <div class="hint-bar">
        <span>🖱 滚轮缩放 &nbsp;|&nbsp; 拖拽平移 &nbsp;|&nbsp; 点击节点查看详情 &nbsp;|&nbsp; 图例筛选类型</span>
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
  graphWidth.value = window.innerWidth - 340
  graphHeight.value = window.innerHeight - 240
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
  height: calc(100vh - 56px - 44px - var(--spacing-lg) * 2);
  display: flex;
  flex-direction: column;
}

.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  flex-shrink: 0;

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }
}

.size-control,
.weight-control {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--text-secondary);
  font-size: 13px;

  .size-label {
    font-size: 12px;
    color: var(--text-tertiary);
    white-space: nowrap;
    min-width: 36px;
  }
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
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-light);
  min-height: 0;
}

.graph-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.legend-panel {
  position: absolute;
  top: var(--spacing-md);
  right: var(--spacing-md);
  padding: var(--spacing-md);
  min-width: 140px;
  max-height: 55%;
  overflow-y: auto;
  z-index: 10;

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
    gap: 2px;
  }

  .legend-btn {
    font-size: 10px;
    padding: 1px 6px;
    border: 1px solid var(--border-light);
    border-radius: 3px;
    background: var(--bg-page);
    color: var(--text-tertiary);
    cursor: pointer;
    &:hover { color: var(--color-primary); border-color: var(--color-primary); }
  }
}

.stats-panel {
  position: absolute;
  top: var(--spacing-md);
  left: var(--spacing-md);
  padding: var(--spacing-md);
  min-width: 110px;

  h4 { font-size: 13px; margin-bottom: var(--spacing-sm); color: var(--text-secondary); }
}

.legend-item {
  margin-bottom: 2px;

  .legend-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;

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
    box-shadow: 0 0 4px currentColor;
  }
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 4px;
  gap: var(--spacing-md);

  strong { color: var(--color-primary); }
}

.hint-bar {
  position: absolute;
  bottom: var(--spacing-sm);
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-glass);
  backdrop-filter: blur(8px);
  padding: 4px 12px;
  border-radius: var(--radius-full);
  pointer-events: none;
}

.entity-detail {
  .entity-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);

    .entity-dot {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    h3 { font-size: 18px; font-weight: 600; }
  }

  .entity-meta {
    margin-top: var(--spacing-lg);
    display: flex;
    gap: var(--spacing-lg);

    .meta-item {
      display: flex;
      flex-direction: column;
      .meta-label { font-size: 12px; color: var(--text-tertiary); }
      .meta-value { font-size: 20px; font-weight: 600; color: var(--text-primary); }
    }
  }

  .entity-related {
    margin-top: var(--spacing-lg);
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
      padding: var(--spacing-sm);
      border-bottom: 1px solid var(--border-light);
      border-radius: var(--radius-sm);
      transition: background 0.15s;

      &.clickable {
        cursor: pointer;
        &:hover {
          background: var(--bg-page);
          .related-name { color: var(--color-primary); }
        }
      }

      .related-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
      .related-name { font-weight: 500; flex: 1; transition: color 0.15s; }
      .related-type { font-size: 11px; color: var(--text-tertiary); }
      .related-rel {
        font-size: 11px;
        color: var(--color-primary);
        background: var(--bg-page);
        padding: 1px 8px;
        border-radius: var(--radius-full);
      }
      .related-arrow {
        color: var(--text-tertiary);
        flex-shrink: 0;
      }
    }
  }
}
</style>

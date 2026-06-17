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
        <button class="btn-secondary btn-sm" @click="resetView">重置视图</button>
        <button class="btn-primary btn-sm" @click="refreshData">刷新数据</button>
      </div>
    </div>

    <div class="graph-main">
      <canvas ref="canvasRef" class="graph-canvas" />

      <!-- 图例 -->
      <div class="legend-panel glass-card" v-if="legend && Object.keys(legend).length > 0">
        <h4>图例</h4>
        <div v-for="(color, type) in legend" :key="type" class="legend-item">
          <span class="legend-dot" :style="{ background: color }" />
          <span>{{ type }}</span>
        </div>
      </div>

      <!-- 统计 -->
      <div class="stats-panel glass-card">
        <h4>图谱统计</h4>
        <div class="stat-row"><span>节点数</span><strong>{{ nodeCount }}</strong></div>
        <div class="stat-row"><span>边数</span><strong>{{ linkCount }}</strong></div>
      </div>

      <!-- 操作提示 -->
      <div class="hint-bar">
        <span>🖱 滚轮缩放 &nbsp;|&nbsp; 拖拽平移 &nbsp;|&nbsp; 点击节点查看详情</span>
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
            <h4>关联实体</h4>
            <div v-for="rn in relatedNodes" :key="rn.id" class="related-item">
              <span class="related-dot" :style="{ background: rn.color }" />
              <span class="related-name">{{ rn.name }}</span>
              <span class="related-type">{{ rn.type }}</span>
              <span class="related-rel">{{ rn.relation }}</span>
            </div>
          </div>
        </div>
      </template>
      <el-empty v-else description="点击图谱中的节点查看详情" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, markRaw } from 'vue'
import { useRoute } from 'vue-router'
import { useGraphRenderer } from '../composables/useGraphRenderer'
import { getGraphData } from '../api/graph'
import { ElMessage } from 'element-plus'
import { Minus, Plus } from '@element-plus/icons-vue'

const route = useRoute()
const canvasRef = ref(null)
const legend = ref({})
const nodeCount = ref(0)
const linkCount = ref(0)
const nodeSizeScale = ref(0.8)
const selectedEntity = ref(null)
const drawerVisible = ref(false)
const graphWidth = ref(1000)
const graphHeight = ref(600)

let renderer = null
let currentNodeData = []
let currentLinkData = []

const relatedLinkCount = computed(() => {
  if (!selectedEntity.value) return 0
  return currentLinkData.filter(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source
    const tid = typeof l.target === 'object' ? l.target.id : l.target
    return sid === selectedEntity.value.id || tid === selectedEntity.value.id
  }).length
})

const relatedNodes = computed(() => {
  if (!selectedEntity.value) return []
  const result = []
  for (const l of currentLinkData) {
    const sid = typeof l.source === 'object' ? l.source.id : l.source
    const tid = typeof l.target === 'object' ? l.target.id : l.target
    let otherId = null
    if (sid === selectedEntity.value.id) otherId = tid
    else if (tid === selectedEntity.value.id) otherId = sid
    if (otherId) {
      const other = currentNodeData.find(n => n.id === otherId)
      if (other && !result.find(r => r.id === otherId)) {
        result.push({ ...other, relation: l.relation || '关联' })
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

function onSizeChange(val) {
  if (renderer) renderer.setNodeSizeScale(val)
}

async function refreshData() {
  try {
    const res = await getGraphData({ kb_id: route.params.id, limit: 200 })
    const data = markRaw({
      nodes: res.nodes || [],
      links: res.links || [],
    })
    currentNodeData = data.nodes
    currentLinkData = data.links
    nodeCount.value = data.nodes.length
    linkCount.value = data.links.length
    legend.value = res.legend || {}
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

.size-control {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--text-secondary);
  font-size: 13px;

  .size-label {
    font-size: 12px;
    color: var(--text-tertiary);
    white-space: nowrap;
    min-width: 60px;
  }
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
  min-width: 130px;
  max-height: 50%;
  overflow-y: auto;

  h4 { font-size: 13px; margin-bottom: var(--spacing-sm); color: var(--text-secondary); }
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
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--text-secondary);

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
    h4 { font-size: 14px; margin-bottom: var(--spacing-md); color: var(--text-secondary); }

    .related-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-sm) 0;
      border-bottom: 1px solid var(--border-light);

      .related-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
      .related-name { font-weight: 500; flex: 1; }
      .related-type { font-size: 11px; color: var(--text-tertiary); }
      .related-rel {
        font-size: 11px;
        color: var(--color-primary);
        background: var(--bg-page);
        padding: 1px 8px;
        border-radius: var(--radius-full);
      }
    }
  }
}
</style>
